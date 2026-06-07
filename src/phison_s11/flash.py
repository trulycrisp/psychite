"""S11 flash data functionality."""

import dataclasses
import enum
import itertools
import struct
from typing import TYPE_CHECKING, ClassVar, Self

if TYPE_CHECKING:
    from collections.abc import Iterator

from phison_s11 import firmware as s11_firmware


@dataclasses.dataclass(frozen=True)
class FlashSectionInfo:
    """Firmware section flash information.

    Attributes:
        page_start: Start page of section.
        page_count: Page count of section.

    """

    page_start: int
    page_count: int


class InitScriptOpcode(enum.IntEnum):
    """Init script operation code.

    Attributes:
        END: End script early.
        WRITE: Write operand1 to target (or *operand1 if indirect flag).
        WRITE_OR: Write (operand1 | operand2) to target (or *operand if indirect flag).
        WRITE_AND: Write (operand1 & operand2) to target (or *operand if indirect flag).
        POLL_OR: Wait while (*operand1 | operand2) == target.
        POLL_OR_NOT: Wait while (*operand1 | operand2) != target.
        POLL_AND: Wait while (*operand1 & operand2) == target.
        POLL_AND_NOT: Wait while (*operand1 & operand2) != target.
        NOP: No operation.

    """

    END = 0
    WRITE = 1
    WRITE_OR = 2
    WRITE_AND = 3
    POLL_OR = 4
    POLL_OR_NOT = 5
    POLL_AND = 6
    POLL_AND_NOT = 7
    NOP = 8


@dataclasses.dataclass(frozen=True)
class InitScriptEntry:
    """Flash header init script entry.

    Performs a single operation in an init script.

    Attributes:
        SIZE: Size of entry.
        opcode: Operation code.
        operand1_indirect: Dereference operand1 as a pointer.
        operand2_indirect: Dereference operand2 as a pointer.
        data_size: Access width in bytes.
        operand1: First operand.
        target: Destination for writes, expected value for polls.
        operand2: Second operand.

    """

    _STRUCT: ClassVar[struct.Struct] = struct.Struct("<B B 2x L L L")
    _OP_OPCODE_MASK: ClassVar[int] = 0xF
    _OP_INDIRECT1_MASK: ClassVar[int] = 1 << 4
    _OP_INDIRECT2_MASK: ClassVar[int] = 1 << 5
    _OP_END_ALT: ClassVar[int] = 0xFF
    _DATA_SIZES: ClassVar[dict[int, int]] = {0: 4, 1: 2, 2: 1}

    SIZE: ClassVar[int] = _STRUCT.size

    opcode: InitScriptOpcode
    operand1_indirect: bool
    operand2_indirect: bool
    data_size: int
    operand1: int
    target: int
    operand2: int

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse from bytes.

        Args:
            data: Bytes to parse.

        Returns:
            Parsed entry.

        """
        operation: int
        data_size_raw: int
        operand1: int
        target: int
        operand2: int
        operation, data_size_raw, operand1, target, operand2 = cls._STRUCT.unpack(
            data,
        )

        # The entire operation byte being 0xFF is also an end marker
        if operation == cls._OP_END_ALT:
            operation = int(InitScriptOpcode.END)

        opcode: InitScriptOpcode
        try:
            opcode = InitScriptOpcode(operation & cls._OP_OPCODE_MASK)
        except ValueError:
            # All other opcodes are handled as nop
            opcode = InitScriptOpcode.NOP

        operand1_indirect: bool = bool(operation & cls._OP_INDIRECT1_MASK)
        operand2_indirect: bool = bool(operation & cls._OP_INDIRECT2_MASK)

        try:
            data_size: int = cls._DATA_SIZES[data_size_raw]
        except KeyError as e:
            raise ValueError("Invalid data size", data_size_raw) from e

        return cls(
            opcode=opcode,
            operand1_indirect=operand1_indirect,
            operand2_indirect=operand2_indirect,
            data_size=data_size,
            operand1=operand1,
            target=target,
            operand2=operand2,
        )


@dataclasses.dataclass(frozen=True)
class FirmwareHeader:
    """Firmware header flash page.

    Attributes:
        SIZE: Size of header page.
        write_sequence: Counter incremented each firmware write.
        copy_block_addresses: Block addresses per channel and copy.
        pages_per_block: Flash pages per block.
        skip_crc: Skip CRC verification of firmware code.
        use_alt_sections: Use alternate section range, also requires some
            hardware checks for use.
        init_script_setup: Init script executed before firmware loading process.
        init_script_normal_section: Init script executed for each section loaded,
            for normal hardware boot mode.
        init_script_alt_section: Init script executed for each section loaded,
            for alternate hardware boot mode (unrelated to use_alt_sections).
        init_script_alt_trigger: Init script executed on specific section trigger
            (if trigger_enabled set), for alternate hardware boot mode.
        normal_sections_load_iram: After sections loaded do a copy to instruction RAM,
            for use_alt_sections disabled.
        normal_sections_load_iram_address: Source address for above.
        normal_sections_load_iram_size: Size for above.
        alt_sections_load_iram: After sections loaded do a copy to instruction RAM,
            for use_alt_sections enabled.
        alt_sections_load_iram_address: Source address for above.
        alt_sections_load_iram_size: Size for above.
        normal_section_start: Start section index for normal boot.
        normal_section_count: Section count for normal boot.
        alt_section_start: Start section index if use_alt_sections set.
        alt_section_count: Section count if use_alt_sections set.
        flash_sections: Flash information for sections.
        sections: Information for sections.
        trigger_enabled: Enable trigger action when specific firmware section loaded.
        trigger_section: Section index for trigger.
        trigger_reconfig_hw: Reconfigures some hardware registers on trigger.
        init_script_normal_trigger: Init script executed on specific section trigger,
            for normal hardware boot mode.

    """

    _CHECKSUM_SEED: ClassVar[int] = 0x3111_3111
    _CHANNEL_COUNT: ClassVar[int] = 2
    _COPY_COUNT: ClassVar[int] = 2

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        "<2s"
        "B"
        "x"
        f"{_CHANNEL_COUNT * _COPY_COUNT}H"
        "H"
        "34x"
        "B"
        "9x"
        "?"
        "13x"
        "2L"
        "2H"
        "84x"
        "2L"
        "40x"
        "2H"
        "4x"
        "?"
        "3x"
        "2L"
        "4x"
        "?"
        "3x"
        "2L"
        "4B"
        f"{2 * s11_firmware.SECTION_COUNT}H"
        f"{2 * s11_firmware.SECTION_COUNT}L"
        "68x"
        "?"
        "B"
        "?"
        "x"
        "L"
        "H"
        "3666x",
    )

    _MAGIC: ClassVar[bytes] = b"ID"
    _SKIP_CRC_MAGIC: ClassVar[dict[int, bool]] = {0x55: True, 0xFF: False}
    _INIT_SCRIPT_LENGTH_MASK: ClassVar[int] = 0xFFF
    _LOAD_ADDRESS: ClassVar[int] = 0x5C0D4000

    SIZE: ClassVar[int] = _STRUCT.size

    write_sequence: int
    copy_block_addresses: tuple[tuple[int, ...], ...]
    pages_per_block: int
    skip_crc: bool
    use_alt_sections: bool
    init_script_setup: tuple[InitScriptEntry, ...]
    init_script_normal_section: tuple[InitScriptEntry, ...]
    init_script_alt_section: tuple[InitScriptEntry, ...]
    init_script_alt_trigger: tuple[InitScriptEntry, ...]
    normal_sections_load_iram: bool
    normal_sections_load_iram_address: int
    normal_sections_load_iram_size: int
    alt_sections_load_iram: bool
    alt_sections_load_iram_address: int
    alt_sections_load_iram_size: int
    normal_section_start: int
    normal_section_count: int
    alt_section_start: int
    alt_section_count: int
    flash_sections: tuple[FlashSectionInfo | None, ...]
    sections: tuple[s11_firmware.SectionInfo | None, ...]
    trigger_enabled: bool
    trigger_section: int
    trigger_reconfig_hw: bool
    init_script_normal_trigger: tuple[InitScriptEntry, ...]

    @classmethod
    def _parse_write_sequence(cls, value: int) -> int:
        """Parse write sequence counter.

        Args:
            value: Value to parse.

        Returns:
            Parsed write sequence counter.

        Raises:
            ValueError: Invalid value.

        """
        magic: int = 0xA0
        magic_mask: int = 0xF0

        if value & magic_mask != magic:
            raise ValueError("Invalid write sequence", value)

        return value & ~magic_mask

    @classmethod
    def _parse_init_script(
        cls,
        data: bytes,
        address: int,
        length: int,
    ) -> tuple[InitScriptEntry, ...]:
        if not length:
            return ()

        offset: int = address - cls._LOAD_ADDRESS

        if not (0 <= offset < len(data)):
            raise ValueError("Invalid init script address", address)

        end_offset: int = offset + length * InitScriptEntry.SIZE
        if end_offset > len(data):
            raise ValueError("Init script overruns data", end_offset, len(data))

        script: list[InitScriptEntry] = []

        for index in range(length):
            entry_offset: int = offset + index * InitScriptEntry.SIZE
            entry_data: bytes = data[entry_offset : entry_offset + InitScriptEntry.SIZE]
            entry: InitScriptEntry = InitScriptEntry.from_bytes(entry_data)

            if entry.opcode == InitScriptOpcode.END:
                break

            script.append(entry)

        return tuple(script)

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse a firmware header flash page from bytes.

        Args:
            data: bytes.

        Returns:
            Parsed header.

        Raises:
            ValueError: Invalid header.

        """
        s11_firmware.checksum_crc32_verify(data, cls._CHECKSUM_SEED)

        values_iter: Iterator[int | bool | bytes] = iter(cls._STRUCT.unpack(data))

        magic: bytes = next(values_iter)
        if magic != cls._MAGIC:
            raise ValueError("Invalid magic", magic)

        write_sequence: int = cls._parse_write_sequence(int(next(values_iter)))

        copy_block_addresses: tuple[tuple[int, ...], ...] = tuple(
            tuple(itertools.islice(values_iter, cls._COPY_COUNT))
            for _ in range(cls._CHANNEL_COUNT)
        )

        pages_per_block: int = int(next(values_iter))

        skip_crc_raw: int = int(next(values_iter))
        try:
            skip_crc: bool = cls._SKIP_CRC_MAGIC[skip_crc_raw]
        except KeyError as e:
            raise ValueError("Invalid skip CRC value", skip_crc_raw) from e

        use_alt_sections: bool = bool(next(values_iter))

        init_script_setup_address: int = int(next(values_iter))
        init_script_normal_section_address: int = int(next(values_iter))
        init_script_setup_length: int = (
            int(next(values_iter)) & cls._INIT_SCRIPT_LENGTH_MASK
        )
        init_script_normal_section_length: int = (
            int(next(values_iter)) & cls._INIT_SCRIPT_LENGTH_MASK
        )
        init_script_setup: tuple[InitScriptEntry, ...] = cls._parse_init_script(
            data,
            init_script_setup_address,
            init_script_setup_length,
        )
        init_script_normal_section: tuple[InitScriptEntry, ...] = (
            cls._parse_init_script(
                data,
                init_script_normal_section_address,
                init_script_normal_section_length,
            )
        )

        init_script_alt_section_address: int = int(next(values_iter))
        init_script_alt_trigger_address: int = int(next(values_iter))
        init_script_alt_section_length: int = (
            int(next(values_iter)) & cls._INIT_SCRIPT_LENGTH_MASK
        )
        init_script_alt_trigger_length: int = (
            int(next(values_iter)) & cls._INIT_SCRIPT_LENGTH_MASK
        )
        init_script_alt_section: tuple[InitScriptEntry, ...] = cls._parse_init_script(
            data,
            init_script_alt_section_address,
            init_script_alt_section_length,
        )
        init_script_alt_trigger: tuple[InitScriptEntry, ...] = cls._parse_init_script(
            data,
            init_script_alt_trigger_address,
            init_script_alt_trigger_length,
        )

        normal_sections_load_iram: bool = bool(next(values_iter))
        normal_sections_load_iram_address: int = int(next(values_iter))
        normal_sections_load_iram_size: int = int(next(values_iter))

        alt_sections_load_iram: bool = bool(next(values_iter))
        alt_sections_load_iram_address: int = int(next(values_iter))
        alt_sections_load_iram_size: int = int(next(values_iter))

        normal_section_start: int = int(next(values_iter))
        normal_section_count: int = int(next(values_iter))
        alt_section_start: int = int(next(values_iter))
        alt_section_count: int = int(next(values_iter))

        section_page_counts: list[int] = list(
            map(
                int,
                itertools.islice(values_iter, s11_firmware.SECTION_COUNT),
            ),
        )

        section_page_starts: list[int] = list(
            map(
                int,
                itertools.islice(values_iter, s11_firmware.SECTION_COUNT),
            ),
        )

        flash_sections: tuple[FlashSectionInfo | None, ...] = tuple(
            FlashSectionInfo(page_start=page_start, page_count=page_count)
            if page_count
            else None
            for page_start, page_count in zip(
                section_page_starts,
                section_page_counts,
                strict=True,
            )
        )

        section_addresses: list[int] = list(
            map(
                int,
                itertools.islice(values_iter, s11_firmware.SECTION_COUNT),
            ),
        )

        section_sizes: list[int] = list(
            map(
                int,
                itertools.islice(values_iter, s11_firmware.SECTION_COUNT),
            ),
        )

        sections: tuple[s11_firmware.SectionInfo | None, ...] = tuple(
            s11_firmware.SectionInfo(0, address, size) if size else None
            for address, size in zip(section_addresses, section_sizes, strict=True)
        )

        trigger_enabled: bool = bool(next(values_iter))
        trigger_section: int = int(next(values_iter))
        trigger_reconfig_hw: bool = bool(next(values_iter))

        init_script_normal_trigger_address: int = int(next(values_iter))
        init_script_normal_trigger_length: int = (
            int(next(values_iter)) & cls._INIT_SCRIPT_LENGTH_MASK
        )
        init_script_normal_trigger: tuple[InitScriptEntry, ...] = (
            cls._parse_init_script(
                data,
                init_script_normal_trigger_address,
                init_script_normal_trigger_length,
            )
        )

        return cls(
            write_sequence=write_sequence,
            copy_block_addresses=copy_block_addresses,
            pages_per_block=pages_per_block,
            skip_crc=skip_crc,
            use_alt_sections=use_alt_sections,
            init_script_setup=init_script_setup,
            init_script_normal_section=init_script_normal_section,
            init_script_alt_section=init_script_alt_section,
            init_script_alt_trigger=init_script_alt_trigger,
            normal_sections_load_iram=normal_sections_load_iram,
            normal_sections_load_iram_address=normal_sections_load_iram_address,
            normal_sections_load_iram_size=normal_sections_load_iram_size,
            alt_sections_load_iram=alt_sections_load_iram,
            alt_sections_load_iram_address=alt_sections_load_iram_address,
            alt_sections_load_iram_size=alt_sections_load_iram_size,
            normal_section_start=normal_section_start,
            normal_section_count=normal_section_count,
            alt_section_start=alt_section_start,
            alt_section_count=alt_section_count,
            flash_sections=flash_sections,
            sections=sections,
            trigger_enabled=trigger_enabled,
            trigger_section=trigger_section,
            trigger_reconfig_hw=trigger_reconfig_hw,
            init_script_normal_trigger=init_script_normal_trigger,
        )

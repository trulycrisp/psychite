"""S11 firmware functionality.

Attributes:
    CHECKSUM_SIZE: Size of checksum at end of sections.
    SECTION_COUNT: Number of sections in firmware code.

"""

import abc
import dataclasses
import datetime
import enum
import hashlib
import itertools
import struct
from typing import TYPE_CHECKING, ClassVar, Self, override

if TYPE_CHECKING:
    from collections.abc import Iterator

from phison_s11 import algorithm as s11_algorithm
from phison_s11 import data as s11_data

_CHECKSUM_PAD_SIZE: int = 8
CHECKSUM_SIZE: int = 4
SECTION_COUNT: int = 8


def _checksum_byte_sum_u16(data: bytes) -> int:
    checksum: int = 0

    for x in data:
        checksum = (checksum + x) & 0xFFFF

    return checksum


def _checksum_byte_sum_u16_verify(data: bytes, checksum: int) -> None:
    real_checksum: int = _checksum_byte_sum_u16(data)

    if real_checksum != checksum:
        raise ValueError("Invalid checksum", real_checksum, checksum)


def checksum_crc32_verify(data: bytes, seed: int) -> None:
    """Verify checksum.

    Args:
        data: Data to verify.
        seed: Checksum seed.

    Raises:
        ValueError: Checksum invalid.

    """
    data_checksum: int = int.from_bytes(data[-CHECKSUM_SIZE:], "little")
    real_checksum: int = s11_algorithm.checksum_crc32(data[:-_CHECKSUM_PAD_SIZE], seed)

    if real_checksum != data_checksum:
        raise ValueError("Invalid checksum", real_checksum, data_checksum)


class VersionType(enum.StrEnum):
    """Firmware version type.

    Attributes:
        ROM: Mask ROM.
        NORMAL: Normal.
        BURNER: Burner.
        RDT: Reliability Demonstration Test (RDT).

    """

    ROM = "R"
    NORMAL = "F"
    BURNER = "B"
    RDT = "S"


@dataclasses.dataclass(frozen=True)
class Version:
    """Firmware version.

    Attributes:
        firmware_type: Type.
        brand: Brand.
        flash: Flash type.
        revision: Revision.

    """

    _INTERFACE: ClassVar[str] = "S"
    _CONTROLLER: ClassVar[str] = "B"

    firmware_type: VersionType
    brand: str
    flash: str
    revision: str

    def __str__(self) -> str:
        """Return version as string."""
        return (
            f"{self._INTERFACE}"
            f"{self._CONTROLLER}"
            f"{self.firmware_type}"
            f"{self.brand}"
            f"{self.flash}"
            f"{self.revision}"
        )

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Parse version from string.

        Args:
            value: String.

        Returns:
            Version.

        """
        interface: str
        controller: str
        firmware_type_raw: str
        brand: str
        flash: str
        interface, controller, firmware_type_raw, brand, flash = value[:5]

        if interface != cls._INTERFACE:
            raise ValueError("Invalid interface", interface)

        if controller != cls._CONTROLLER:
            raise ValueError("Invalid controller", controller)

        firmware_type: VersionType = VersionType(firmware_type_raw)
        revision: str = value[5:]

        return cls(
            firmware_type=firmware_type,
            brand=brand,
            flash=flash,
            revision=revision,
        )


@dataclasses.dataclass
class SectionInfo:
    """Firmware section information.

    Attributes:
        burner_address: Load address for burner code.
        normal_address: Load address for normal code.
        size: Section code size.

    """

    burner_address: int
    normal_address: int
    size: int


class Seed:
    """Firmware code seed.

    Attributes:
        KEY_SIZE: Size of key.
        SIZE: Size of seed.
        DEFAULT_KEY: Default key, used for code encryption.

    """

    KEY_SIZE: ClassVar[int] = 15_360
    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        f"<{2 * SECTION_COUNT * 2}L 896x {KEY_SIZE}s",
    )
    SIZE: ClassVar[int] = _STRUCT.size
    DEFAULT_KEY: ClassVar[bytes] = b"\0" * KEY_SIZE

    def __init__(
        self,
        sections: tuple[SectionInfo | None, ...] = (None,) * SECTION_COUNT,
        key: bytes = DEFAULT_KEY,
    ) -> None:
        """Initialise seed.

        Args:
            sections: Section information.
            key: Key used for code encryption.

        """
        self.sections: tuple[SectionInfo | None, ...] = sections
        self.key: bytes = key

    def __bytes__(self) -> bytes:
        """Return seed packed to bytes."""
        section_values: list[int] = []

        # Burner values
        for section in self.sections:
            section_values += (
                (section.burner_address, section.size) if section else (0, 0)
            )

        # Normal values
        for section in self.sections:
            section_values += (
                (section.normal_address, section.size) if section else (0, 0)
            )

        return self._STRUCT.pack(*section_values, self.key)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"{self.__class__.__name__}"
            f"(sections={self.sections!r}, "
            f"key=<size: {len(self.key)}>)"
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse seed from bytes.

        Args:
            data: Bytes.

        Returns:
            Seed.

        """
        if len(data) != cls.SIZE:
            raise ValueError("Invalid size")

        # Iterator for all struct values
        values_iter: Iterator[int | bytes] = iter(
            cls._STRUCT.unpack(data),
        )

        # Consume burner and normal code values into new iterator
        burner_iter: Iterator[int]
        normal_iter: Iterator[int]
        burner_iter, normal_iter = (
            iter(list(itertools.islice(values_iter, SECTION_COUNT * 2)))
            for _ in range(2)
        )

        # Key is last remaining non-consumed element
        key: bytes = next(values_iter)

        sections: list[SectionInfo | None] = []
        for burner_address, burner_size, normal_address, normal_size in zip(
            burner_iter,
            burner_iter,
            normal_iter,
            normal_iter,
            strict=True,
        ):
            if burner_size != normal_size:
                raise ValueError("Size mismatch", burner_size, normal_size)

            section: SectionInfo | None = (
                SectionInfo(
                    burner_address=burner_address,
                    normal_address=normal_address,
                    size=normal_size,
                )
                if normal_size
                else None
            )

            sections.append(section)

        return cls(sections=tuple(sections), key=key)

    @property
    def sections(self) -> tuple[SectionInfo | None, ...]:
        """Section information."""
        return self._sections

    @sections.setter
    def sections(self, value: tuple[SectionInfo | None, ...]) -> None:
        if len(value) != SECTION_COUNT:
            raise ValueError("Invalid section count", len(value))

        self._sections: tuple[SectionInfo | None, ...] = value

    @property
    def key(self) -> bytes:
        """Key used for code encryption."""
        return self._key

    @key.setter
    def key(self, value: bytes) -> None:
        if len(value) != self.KEY_SIZE:
            raise ValueError("Invalid key size", len(value))

        self._key: bytes = value

    @property
    def cipher_crc16_seed(self) -> int:
        """Seed for CRC16-based cipher algorithm."""
        word_size: int = 4
        step_size: int = 516

        seed: int = 0

        for offset in range(0, len(self.key) - word_size + 1, step_size):
            seed ^= int.from_bytes(self.key[offset : offset + word_size], "little")

        return seed


class CodeSection:
    """Code section base class.

    Attributes:
        burner_address: Load address for burner code.
        normal_address: Load address for normal code.
        code: Section code.

    """

    _CHECKSUM_SEED: int = 0x55AA_55AA
    _ALIGN_SIZE: int

    def __new__(cls, *_args: object, **_kwargs: object) -> Self:
        """Create code section instance."""
        if cls is CodeSection:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly")

        return super().__new__(cls)

    def __init__(
        self,
        burner_address: int,
        normal_address: int,
        code: bytes | bytearray,
    ) -> None:
        """Initialise code section.

        Args:
            burner_address: Load address for burner code.
            normal_address: Load address for normal code.
            code: Code data of section.

        """
        self.burner_address: int = burner_address
        self.normal_address: int = normal_address
        self.code: bytes = bytes(code)

    def __bytes__(self) -> bytes:
        """Return code section as bytes."""
        if not self.code:
            raise ValueError("No code")

        data: bytearray = bytearray(self.code)

        # Pad to align
        data += b"\0" * (-len(self.code) % self._ALIGN_SIZE)

        # Set checksum
        checksum: int = s11_algorithm.checksum_crc32(
            data[:-_CHECKSUM_PAD_SIZE],
            self._CHECKSUM_SEED,
        )
        data[-CHECKSUM_SIZE:] = checksum.to_bytes(CHECKSUM_SIZE, "little")

        return bytes(data)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"{self.__class__.__name__}("
            f"burner_address=0x{self.burner_address:08x}, "
            f"normal_address=0x{self.normal_address:08x}, "
            f"code=<size: {len(self.code)}>)"
        )

    @classmethod
    def parse(cls, seed_section: SectionInfo, code: bytes) -> Self:
        """Parse code section.

        Args:
            seed_section: Section info from seed.
            code: Section code.

        Returns:
            Parsed section.

        """
        if len(code) % cls._ALIGN_SIZE:
            raise ValueError("Size not aligned", len(code), cls._ALIGN_SIZE)

        checksum_crc32_verify(code, cls._CHECKSUM_SEED)

        return cls(
            burner_address=seed_section.burner_address,
            normal_address=seed_section.normal_address,
            code=code,
        )


class Code(abc.ABC):
    """Firmware code base class."""

    _SECTION_CLASS: type[CodeSection]

    def __init__(
        self,
        sections: tuple[CodeSection | None, ...],
        seed_key: bytes = Seed.DEFAULT_KEY,
    ) -> None:
        """Initialise code.

        Args:
            sections: Code sections.
            seed_key: Key for code encryption.

        """
        self.sections = sections
        self.seed_key = seed_key

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"{self.__class__.__name__}"
            f"(sections={self.sections!r}, "
            f"seed_key=<size: {len(self.seed_key)}>)"
        )

    def __bytes__(self) -> bytes:
        """Return code packed to bytes."""
        seed_sections: list[SectionInfo | None] = []
        code: bytearray | bytes = bytearray()

        for section in self.sections:
            if not section:
                seed_sections.append(None)
                continue

            section_data: bytes = bytes(section)

            seed_section: SectionInfo = SectionInfo(
                burner_address=section.burner_address,
                normal_address=section.normal_address,
                size=len(section_data),
            )

            seed_sections.append(seed_section)
            code += section_data

        seed: Seed = Seed(sections=tuple(seed_sections), key=self.seed_key)
        code = self._encrypt_code(seed, code)

        return bytes(seed) + code

    @abc.abstractmethod
    def _encrypt_code(self, seed: Seed, code: bytes | bytearray) -> bytes: ...

    @classmethod
    def _parse_sections(
        cls,
        seed_sections: tuple[SectionInfo | None, ...],
        data: bytes,
    ) -> tuple[CodeSection | None, ...]:
        offset: int = 0
        sections: list[CodeSection | None] = []

        for seed_section in seed_sections:
            if not seed_section:
                sections.append(None)
                continue

            section_code: bytes = data[offset : offset + seed_section.size]

            if len(section_code) != seed_section.size:
                raise ValueError(
                    "Invalid section size",
                    seed_section.size,
                    len(data) - offset,
                )

            section: CodeSection = cls._SECTION_CLASS.parse(
                seed_section=seed_section,
                code=section_code,
            )

            sections.append(section)
            offset += seed_section.size

        trailing_size: int = len(data) - offset
        if trailing_size:
            raise ValueError("Trailing data", trailing_size)

        return tuple(sections)

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse code from bytes.

        Args:
            data: Bytes.

        Returns:
            Parsed code.

        """
        ...

    @property
    def sections(self) -> tuple[CodeSection | None, ...]:
        """Code sections."""
        return self._sections

    @sections.setter
    def sections(self, value: tuple[CodeSection | None, ...]) -> None:
        if len(value) != SECTION_COUNT:
            raise ValueError("Invalid section count", len(value))

        self._sections: tuple[CodeSection | None, ...] = value

    @property
    def seed_key(self) -> bytes:
        """Key used for code encryption."""
        return self._key

    @seed_key.setter
    def seed_key(self, value: bytes) -> None:
        if len(value) != Seed.KEY_SIZE:
            raise ValueError("Invalid key size", len(value))

        self._key: bytes = value


class BurnerCodeSection(CodeSection):
    """Burner code section."""

    _ALIGN_SIZE: int = 4_096


class BurnerCode(Code):
    """Burner code."""

    _SECTION_CLASS: type[CodeSection] = BurnerCodeSection
    _SRAM_SECTION: int = 6
    _SRAM_XOR_KEY: int = 0xFF

    @classmethod
    def _crypt_sram(cls, data: bytes | bytearray) -> bytes:
        return bytes(x ^ cls._SRAM_XOR_KEY for x in data)

    @classmethod
    def _crypt_code(cls, seed: Seed, data: bytes | bytearray) -> bytes:
        cipher_crc16_seed: int = seed.cipher_crc16_seed

        before_sram_size: int = sum(
            x.size if x else 0 for x in seed.sections[: cls._SRAM_SECTION]
        )
        before_sram: bytes = s11_algorithm.cipher_crc16(
            data[:before_sram_size],
            cipher_crc16_seed,
        )

        sram_section: SectionInfo | None = seed.sections[cls._SRAM_SECTION]
        sram_size: int = sram_section.size if sram_section else 0
        after_sram_offset: int = before_sram_size + sram_size
        sram: bytes = cls._crypt_sram(
            data[before_sram_size:after_sram_offset],
        )

        after_sram_size: int = sum(
            x.size if x else 0 for x in seed.sections[cls._SRAM_SECTION + 1 :]
        )
        after_sram: bytes = s11_algorithm.cipher_crc16(
            data[after_sram_offset : after_sram_offset + after_sram_size],
            cipher_crc16_seed,
            after_sram_offset,
        )

        return before_sram + sram + after_sram

    @override
    def _encrypt_code(self, seed: Seed, code: bytes | bytearray) -> bytes:
        return self._crypt_code(seed, code)

    @classmethod
    @override
    def from_bytes(cls, data: bytes) -> Self:
        """Parse code from bytes.

        Args:
            data: Bytes.

        Returns:
            Parsed code.

        """
        seed: Seed = Seed.from_bytes(data[: Seed.SIZE])
        code: bytes = cls._crypt_code(seed, data[Seed.SIZE :])

        sections: tuple[BurnerCodeSection | None, ...] = cls._parse_sections(
            seed.sections,
            code,
        )

        return cls(sections=sections, seed_key=seed.key)

    @property
    def iram_sections(self) -> tuple[CodeSection, ...]:
        """Instruction RAM sections, for VUC loading."""
        return tuple(
            x for i, x in enumerate(self.sections) if x and i != self._SRAM_SECTION
        )

    @property
    def sram_section_crypt(self) -> bytes | None:
        """Encrypted SRAM 'icode' section, for VUC loading."""
        section: CodeSection | None = self.sections[self._SRAM_SECTION]

        if not section:
            return None

        return self._crypt_sram(bytes(section))


class NormalCodeSection(CodeSection):
    """Normal code section."""

    _ALIGN_SIZE: int = 16_384


class NormalCode(Code):
    """Firmware normal code.

    Attributes:
        xor_0561: Use XOR-0561 encryption.

    """

    _SECTION_CLASS: type[CodeSection] = NormalCodeSection

    def __init__(
        self,
        sections: tuple[CodeSection | None, ...],
        xor_0561: bool,
        seed_key: bytes = Seed.DEFAULT_KEY,
    ) -> None:
        """Initialise code.

        Args:
            sections: Code sections.
            xor_0561: Use XOR-0561 encryption.
            seed_key: Key for code encryption.

        """
        super().__init__(sections, seed_key)
        self.xor_0561 = xor_0561

    @override
    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"{self.__class__.__name__}"
            f"(sections={self.sections!r}, "
            f"xor_0561={self.xor_0561}, "
            f"seed_key=<size: {len(self.seed_key)}>)"
        )

    @override
    def _encrypt_code(self, seed: Seed, code: bytes | bytearray) -> bytes:
        code = s11_algorithm.cipher_crc16(code, seed.cipher_crc16_seed)

        if self.xor_0561:
            code = s11_algorithm.cipher_xor_0561(code)

        return code

    @classmethod
    @override
    def from_bytes(cls, data: bytes) -> Self:
        """Parse code from bytes.

        Args:
            data: Bytes.

        Returns:
            Parsed code.

        """
        seed: Seed = Seed.from_bytes(data[: Seed.SIZE])

        code: bytes = data[Seed.SIZE :]
        code = s11_algorithm.cipher_crc16(code, seed.cipher_crc16_seed)

        # Try parse sections, if it fails retry with XOR-0561
        sections: tuple[NormalCodeSection | None, ...]
        xor_0561: bool
        try:
            sections = cls._parse_sections(seed.sections, code)
        except ValueError:
            code = s11_algorithm.cipher_xor_0561(code)
            sections = cls._parse_sections(seed.sections, code)
            xor_0561 = True
        else:
            xor_0561 = False

        return cls(sections=sections, xor_0561=xor_0561, seed_key=seed.key)


class FirmwareType(enum.IntEnum):
    """Firmware type.

    Attributes:
        UNKNOWN0: Exists but unknown purpose.
        NORMAL: Normal firmware.
        UNKNOWN2: Exists but unknown purpose.

    """

    UNKNOWN0 = 0
    NORMAL = 1
    UNKNOWN2 = 2


class InstallType(enum.IntEnum):
    """Firmware install type.

    Attributes:
        NORMAL: Normal install.
        FTL_CHECKPOINT: Write FTL state before install.
        FORCE: Skip flash compatibility check.

    """

    NORMAL = 0x0
    FTL_CHECKPOINT = 0xDC
    FORCE = 0xDD


@dataclasses.dataclass(frozen=True)
class Header:
    """Firmware header.

    Attributes:
        SIZE: Size of header.
        version: Firmware version.
        burner_code_size: Burner code section size.
        burner_code_checksum: Burner code section checksum.
        install_type: Firmware install type.
        normal_code_size: Normal code section size.
        normal_code_checksum: Normal code section checksum.
        firmware_type: Firmware type.
        has_signature: Has cryptographic signature for normal code.
        normal_code_offset: Offset to normal code section.
        engineering_mode: Used in VUC unlock handshake.
        size: Firmware size.
        date: Firmware date.

    """

    _MAGIC: ClassVar[bytes] = b"PS"
    _CONTROLLER_VERSION: ClassVar[int] = 3111
    _CONTROLLER_DASH_VERSION: ClassVar[bytes] = b"SB"
    _IS_RDT_MAGIC: ClassVar[bytes] = b"RDT"
    _DATE_SIZE: ClassVar[int] = 7
    _END_MAGIC: ClassVar[int] = 0x55AA

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        ">2s H s s s L H B L H s 2s B 4x s 2x B L 17x B 43x 3s 21x L 378x"
        f"{_DATE_SIZE}s"
        "H",
    )

    SIZE: ClassVar[int] = _STRUCT.size

    version: Version | None = None
    burner_code_size: int = 0
    burner_code_checksum: int = 0
    install_type: InstallType = InstallType.NORMAL
    normal_code_size: int = 0
    normal_code_checksum: int = 0
    firmware_type: FirmwareType = FirmwareType.NORMAL
    has_signature: bool = False
    normal_code_offset: int = 0
    engineering_mode: bool = False
    size: int = 0
    date: datetime.datetime | None = None

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse from bytes.

        Args:
            data: Bytes.

        Returns:
            Parsed header.

        Raises:
            ValueError: Invalid data.

        """
        magic: bytes
        controller_version: int
        version_brand_raw: bytes
        version_flash_raw: bytes
        version_revision1: bytes
        burner_code_size: int
        burner_code_checksum: int
        install_type_raw: int
        normal_code_size: int
        normal_code_checksum: int
        version_revision2: bytes
        controller_dash_version: bytes
        firmware_type_raw: int
        version_revision3: bytes
        has_signature_raw: int
        normal_code_offset: int
        engineering_mode_raw: int
        is_rdt_raw: bytes
        size: int
        date_raw: bytes
        end_magic: int
        (
            magic,
            controller_version,
            version_brand_raw,
            version_flash_raw,
            version_revision1,
            burner_code_size,
            burner_code_checksum,
            install_type_raw,
            normal_code_size,
            normal_code_checksum,
            version_revision2,
            controller_dash_version,
            firmware_type_raw,
            version_revision3,
            has_signature_raw,
            normal_code_offset,
            engineering_mode_raw,
            is_rdt_raw,
            size,
            date_raw,
            end_magic,
        ) = cls._STRUCT.unpack(data)

        if magic != cls._MAGIC:
            raise ValueError("Invalid magic", magic)

        if end_magic != cls._END_MAGIC:
            raise ValueError("Invalid end magic", end_magic)

        if controller_version != cls._CONTROLLER_VERSION:
            raise ValueError("Invalid controller version", controller_version)

        install_type: InstallType = InstallType(install_type_raw)

        if controller_dash_version != cls._CONTROLLER_DASH_VERSION:
            raise ValueError("Invalid controller dash version", controller_dash_version)

        firmware_type: FirmwareType = FirmwareType(firmware_type_raw)
        has_signature: bool = s11_data.bool_unpack(has_signature_raw)

        is_rdt: bool
        match is_rdt_raw:
            case cls._IS_RDT_MAGIC:
                is_rdt = True
            case x if not any(x):
                is_rdt = False
            case _:
                raise ValueError("Invalid is RDT value", is_rdt_raw)

        engineering_mode: bool = s11_data.bool_unpack(engineering_mode_raw)

        version_type: VersionType = VersionType.RDT if is_rdt else VersionType.NORMAL
        version_brand: str
        version_flash: str
        version_revision: str
        version_brand, version_flash, version_revision = map(
            bytes.decode,
            (
                version_brand_raw,
                version_flash_raw,
                version_revision1 + version_revision2 + version_revision3,
            ),
        )
        version: Version = Version(
            version_type,
            version_brand,
            version_flash,
            version_revision,
        )

        date: datetime.datetime | None
        if any(date_raw):
            date_values: list[int] = [int(f"{x:x}") for x in date_raw]
            date_year: int = date_values[0] * 100 + date_values[1]
            date = datetime.datetime(
                date_year,
                *date_values[2:],
                tzinfo=datetime.UTC,
            )
        else:
            date = None

        return cls(
            version=version,
            burner_code_size=burner_code_size,
            burner_code_checksum=burner_code_checksum,
            install_type=install_type,
            normal_code_size=normal_code_size,
            normal_code_checksum=normal_code_checksum,
            firmware_type=firmware_type,
            has_signature=has_signature,
            normal_code_offset=normal_code_offset,
            engineering_mode=engineering_mode,
            size=size,
            date=date,
        )

    def __bytes__(self) -> bytes:
        """Return header packed to bytes."""
        version_brand: bytes
        version_flash: bytes
        version_revision1: bytes
        version_revision2: bytes
        version_revision3: bytes

        if self.version:
            (
                version_brand,
                version_flash,
                version_revision1,
                version_revision2,
                version_revision3,
            ) = map(
                str.encode,
                (self.version.brand, self.version.flash, *self.version.revision),
            )
        else:
            version_brand = version_flash = version_revision1 = version_revision2 = (
                version_revision3
            ) = b"\0"

        has_signature_raw: int = s11_data.bool_pack(self.has_signature)
        engineering_mode_raw: int = s11_data.bool_pack(self.engineering_mode)

        is_rdt_raw: bytes = (
            self._IS_RDT_MAGIC
            if self.version and self.version.firmware_type == VersionType.RDT
            else b"\0" * len(self._IS_RDT_MAGIC)
        )

        date_raw: bytes = (
            bytes.fromhex(self.date.strftime("%Y%m%d%H%M%S"))
            if self.date
            else b"\0" * self._DATE_SIZE
        )

        return self._STRUCT.pack(
            self._MAGIC,
            self._CONTROLLER_VERSION,
            version_brand,
            version_flash,
            version_revision1,
            self.burner_code_size,
            self.burner_code_checksum,
            self.install_type,
            self.normal_code_size,
            self.normal_code_checksum,
            version_revision2,
            self._CONTROLLER_DASH_VERSION,
            self.firmware_type,
            version_revision3,
            has_signature_raw,
            self.normal_code_offset,
            engineering_mode_raw,
            is_rdt_raw,
            self.size,
            date_raw,
            self._END_MAGIC,
        )


@dataclasses.dataclass(frozen=True)
class SignatureSHA256Constants:
    """SHA256 constants used in firmware signature section.

    Attributes:
        SIZE: Size of SHA256 constants.

    """

    _ROUND_CONSTANTS: ClassVar[tuple[int, ...]] = (
        0x428A2F98,
        0x71374491,
        0xB5C0FBCF,
        0xE9B5DBA5,
        0x3956C25B,
        0x59F111F1,
        0x923F82A4,
        0xAB1C5ED5,
        0xD807AA98,
        0x12835B01,
        0x243185BE,
        0x550C7DC3,
        0x72BE5D74,
        0x80DEB1FE,
        0x9BDC06A7,
        0xC19BF174,
        0xE49B69C1,
        0xEFBE4786,
        0x0FC19DC6,
        0x240CA1CC,
        0x2DE92C6F,
        0x4A7484AA,
        0x5CB0A9DC,
        0x76F988DA,
        0x983E5152,
        0xA831C66D,
        0xB00327C8,
        0xBF597FC7,
        0xC6E00BF3,
        0xD5A79147,
        0x06CA6351,
        0x14292967,
        0x27B70A85,
        0x2E1B2138,
        0x4D2C6DFC,
        0x53380D13,
        0x650A7354,
        0x766A0ABB,
        0x81C2C92E,
        0x92722C85,
        0xA2BFE8A1,
        0xA81A664B,
        0xC24B8B70,
        0xC76C51A3,
        0xD192E819,
        0xD6990624,
        0xF40E3585,
        0x106AA070,
        0x19A4C116,
        0x1E376C08,
        0x2748774C,
        0x34B0BCB5,
        0x391C0CB3,
        0x4ED8AA4A,
        0x5B9CCA4F,
        0x682E6FF3,
        0x748F82EE,
        0x78A5636F,
        0x84C87814,
        0x8CC70208,
        0x90BEFFFA,
        0xA4506CEB,
        0xBEF9A3F7,
        0xC67178F2,
    )

    _INITIAL_VALUES: ClassVar[tuple[int, ...]] = (
        0x6A09E667,
        0xBB67AE85,
        0x3C6EF372,
        0xA54FF53A,
        0x510E527F,
        0x9B05688C,
        0x1F83D9AB,
        0x5BE0CD19,
    )

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        f"<{len(_ROUND_CONSTANTS)}L {len(_INITIAL_VALUES)}L 736x",
    )

    SIZE: ClassVar[int] = _STRUCT.size

    def __bytes__(self) -> bytes:
        """Return signature SHA256 constants packed to bytes."""
        data: bytes = self._STRUCT.pack(*self._ROUND_CONSTANTS, *self._INITIAL_VALUES)
        return s11_algorithm.cipher_xor_0561(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse from bytes.

        Args:
            data: Bytes to parse.

        Returns:
            Parsed SHA256 constants.

        """
        data = s11_algorithm.cipher_xor_0561(data)
        values: tuple[int, ...] = cls._STRUCT.unpack(data)
        round_constants: tuple[int, ...] = values[: len(cls._ROUND_CONSTANTS)]
        initial_values: tuple[int, ...] = values[len(cls._ROUND_CONSTANTS) :]

        if round_constants != cls._ROUND_CONSTANTS:
            raise ValueError("Invalid round constants")

        if initial_values != cls._INITIAL_VALUES:
            raise ValueError("Invalid initial values")

        return cls()


@dataclasses.dataclass(frozen=True)
class Signature:
    """Firmware signature.

    Cryptographic signature of normal code section.

    Attributes:
        SIZE: Size of signature section.
        SIZE_IN_HEADER: Size of signature for size field of firmware header
            (different than actual size for unknown reason).
        header: Signature header data.
        rsa_signature: RSA-encrypted hash.
        rsa_modulus: RSA modulus used for verifying signature.
        sha256_constants: Constants used for SHA256 when verifying hash.

    """

    _HEADER_SIZE: ClassVar[int] = 512
    _RSA_SIGNATURE_SIZE: ClassVar[int] = 256
    _RSA_MODULUS_SIZE: ClassVar[int] = 256

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        f">{_HEADER_SIZE}s"
        f"{_RSA_SIGNATURE_SIZE}s"
        f"{_RSA_MODULUS_SIZE}s"
        "1024x"
        f"{SignatureSHA256Constants.SIZE}s",
    )

    _RSA_PUBLIC_EXPONENT: ClassVar[int] = 65_537
    _DEFAULT_HEADER: ClassVar[bytes] = b"\0" * _HEADER_SIZE

    # RSA modulus used to create new signatures
    _DEFAULT_RSA_MODULUS: ClassVar[int] = int(
        "0x6893C4301EE650D56ED820E16D6FF6DBB49D8AE81DFB5AEA949B6EF746C504E74ABBF5C3F26"
        "A1E692D7415A8664933A2D9F89FC5A2D9BEB1DB706E841EB688D4FF46F87CC541F76EC352100D"
        "9C47849B049CB92F494A610BDC968217E17AE605298945E8F07E5316A780511AB21548E0A91C8"
        "1E7B83AEA6B3574D5D5A6CF3E9CE5146A6F74E26635ECDF199857F9A3AAF382A54EDC2E27E7A3"
        "5B567C5B839F99B8125E606A43A28E196CC7404E2F5988B6B19A21CDF4EC5DAAA59CF7AF97544"
        "0224C3214D3F4DA0C7F6BCC4E4CA60A12CEF8C57CFD0AF20A7D27E50F074563D996B2C9725D65"
        "E7341F7F51B0F74D8B93CA25183FF74A12B9756F51588BCBC3BF",
        16,
    )

    # RSA private exponent used to create new signatures
    _DEFAULT_RSA_PRIVATE_EXPONENT: ClassVar[int] = int(
        "0x534EE3CB31D268329ECAADE6E7377A802BB21526343C388107418B74917C021BFEFD1D1BABD"
        "1BDC82BDD7E2358D897B9F3CA8BFCF56E60EB6ED47235EE019B9F927D0716DE4D5EBF6DF9C1B0"
        "15FF23341AC87EFD9C75143A4ECFD7730EBCC8E0F3E5D73B69DA3876A39925030F3AC583B3347"
        "28815CB59536E9254868F0C29E3EC890A91748781C9C0499F5C097B7FA7FABCB2A370103D84F4"
        "4FE3C298BFC09FD45478D605C23C296F0391DE23A245B1C24A52AF4CCAA64AFDFD7EA6749B56C"
        "3C7545C0BB2BD840AB4C2577733038D742655906EC41EACC92C089E0C1E9054BBD1636B73FCAB"
        "ED34D0F8BDAE87265B8D4F333AD5DD2B4F589484CA418657119",
        16,
    )

    SIZE: ClassVar[int] = _STRUCT.size
    SIZE_IN_HEADER: ClassVar[int] = 1_536

    header: bytes
    rsa_signature: bytes
    rsa_modulus: bytes
    sha256_constants: SignatureSHA256Constants

    def __bytes__(self) -> bytes:
        """Return signature packed to bytes."""
        return self._STRUCT.pack(
            self.header,
            self.rsa_signature,
            self.rsa_modulus,
            bytes(self.sha256_constants),
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse from bytes.

        Args:
            data: Bytes to parse.

        Returns:
            Parsed signature.

        """
        header: bytes
        rsa_signature: bytes
        rsa_modulus: bytes
        sha256_constants_raw: bytes
        header, rsa_signature, rsa_modulus, sha256_constants_raw = cls._STRUCT.unpack(
            data,
        )

        sha256_constants: SignatureSHA256Constants = (
            SignatureSHA256Constants.from_bytes(sha256_constants_raw)
        )

        return cls(
            header=header,
            rsa_signature=rsa_signature,
            rsa_modulus=rsa_modulus,
            sha256_constants=sha256_constants,
        )

    @classmethod
    def generate(cls, normal_code: bytes) -> Self:
        """Generate new signature.

        Args:
            normal_code: Normal code data to sign.

        Returns:
            New signature.

        """
        header: bytes = cls._DEFAULT_HEADER

        # Get hash of data
        hash_input: bytes = header + normal_code
        data_hash: bytes = hashlib.sha256(hash_input).digest()

        # Init RSA key pair
        rsa_modulus: int = cls._DEFAULT_RSA_MODULUS
        rsa_modulus_bytes: bytes = rsa_modulus.to_bytes(cls._RSA_MODULUS_SIZE, "little")
        rsa_private_exponent: int = cls._DEFAULT_RSA_PRIVATE_EXPONENT

        # Encrypt hash
        padding: bytes = b"\0" * (cls._RSA_SIGNATURE_SIZE - len(data_hash))
        plaintext: bytes = padding + data_hash
        plaintext_raw: int = int.from_bytes(plaintext, "big")
        ciphertext_raw: int = pow(plaintext_raw, rsa_private_exponent, rsa_modulus)
        ciphertext: bytes = ciphertext_raw.to_bytes(cls._RSA_SIGNATURE_SIZE, "little")

        sha256_constants: SignatureSHA256Constants = SignatureSHA256Constants()

        return cls(
            header=header,
            rsa_signature=ciphertext,
            rsa_modulus=rsa_modulus_bytes,
            sha256_constants=sha256_constants,
        )

    def verify(self, normal_code: bytes) -> bool:
        """Verify signature.

        Args:
            normal_code: Normal code data to verify signature for.

        Returns:
            Signature valid.

        """
        # Calculate hash of data
        hash_input: bytes = self.header + normal_code
        data_hash: bytes = hashlib.sha256(hash_input).digest()

        # Decrypt RSA-encrypted hash in signature
        rsa_signature_raw: int = int.from_bytes(self.rsa_signature, "little")
        rsa_modulus_raw: int = int.from_bytes(self.rsa_modulus, "little")
        decrypted_raw: int = pow(
            rsa_signature_raw,
            self._RSA_PUBLIC_EXPONENT,
            rsa_modulus_raw,
        )
        decrypted: bytes = decrypted_raw.to_bytes(len(self.rsa_signature), "big")
        signature_hash: bytes = decrypted[-len(data_hash) :]

        return signature_hash == data_hash


@dataclasses.dataclass
class Firmware:
    """Firmware.

    Attributes:
        version: Version.
        date: Date.
        firmware_type: Type.
        install_type: Install type.
        has_signature: Has cryptographic signature.
        burner_code: Burner code.
        normal_code: Normal code.

    """

    version: Version
    date: datetime.datetime | None = None
    firmware_type: FirmwareType = FirmwareType.NORMAL
    install_type: InstallType = InstallType.NORMAL
    has_signature: bool = False
    burner_code: BurnerCode | None = None
    normal_code: NormalCode | None = None

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Unpack firmware from bytes.

        Args:
            data: Bytes.

        Returns:
            Firmware.

        """
        header: Header = Header.from_bytes(data[: Header.SIZE])

        burner_code_end_offset: int = Header.SIZE + header.burner_code_size
        expected_size: int = burner_code_end_offset + header.normal_code_size
        normal_code_offset: int = burner_code_end_offset

        if header.has_signature:
            expected_size += Signature.SIZE_IN_HEADER
            normal_code_offset += Signature.SIZE

            if header.normal_code_offset != normal_code_offset:
                raise ValueError(
                    "Invalid normal code offset",
                    header.normal_code_offset,
                    normal_code_offset,
                )
        elif header.normal_code_offset:
            raise ValueError("Unexpected normal code offset", header.normal_code_offset)

        if header.size != expected_size:
            raise ValueError("Invalid size", header.size, expected_size)

        end_offset: int = normal_code_offset + header.normal_code_size
        if end_offset > len(data):
            raise ValueError("Truncated", end_offset, len(data))

        burner_code_data: bytes = data[Header.SIZE : burner_code_end_offset]
        _checksum_byte_sum_u16_verify(burner_code_data, header.burner_code_checksum)
        signature_data: bytes = data[burner_code_end_offset:normal_code_offset]
        normal_code_data: bytes = data[normal_code_offset:end_offset]
        _checksum_byte_sum_u16_verify(normal_code_data, header.normal_code_checksum)

        # Verify normal code signature
        if signature_data and normal_code_data:
            signature: Signature = Signature.from_bytes(signature_data)

            if not signature.verify(normal_code_data):
                raise ValueError("Invalid signature")

        burner_code: BurnerCode | None = (
            BurnerCode.from_bytes(burner_code_data) if burner_code_data else None
        )

        normal_code: NormalCode | None = (
            NormalCode.from_bytes(normal_code_data) if normal_code_data else None
        )

        return cls(
            version=header.version,
            date=header.date,
            firmware_type=header.firmware_type,
            install_type=header.install_type,
            has_signature=header.has_signature,
            burner_code=burner_code,
            normal_code=normal_code,
        )

    def __bytes__(self) -> bytes:
        """Return firmware packed to bytes."""
        burner_code_data: bytes = bytes(self.burner_code) if self.burner_code else b""
        normal_code_data: bytes = bytes(self.normal_code) if self.normal_code else b""

        header_data: bytes = bytes(
            self._create_header(burner_code_data, normal_code_data),
        )

        signature_data: bytes = (
            bytes(Signature.generate(normal_code_data)) if self.has_signature else b""
        )

        return header_data + burner_code_data + signature_data + normal_code_data

    def _create_header(
        self,
        burner_code_data: bytes,
        normal_code_data: bytes,
    ) -> Header:
        burner_code_size: int = len(burner_code_data)
        burner_code_checksum: int = _checksum_byte_sum_u16(burner_code_data)

        normal_code_size: int = len(normal_code_data)
        normal_code_checksum: int = _checksum_byte_sum_u16(normal_code_data)

        burner_code_end_offset: int = Header.SIZE + burner_code_size
        normal_code_offset: int
        size: int = burner_code_end_offset + normal_code_size

        if self.has_signature:
            normal_code_offset = burner_code_end_offset + Signature.SIZE
            size += Signature.SIZE_IN_HEADER
        else:
            normal_code_offset = 0

        return Header(
            version=self.version,
            burner_code_size=burner_code_size,
            burner_code_checksum=burner_code_checksum,
            install_type=self.install_type,
            normal_code_size=normal_code_size,
            normal_code_checksum=normal_code_checksum,
            firmware_type=self.firmware_type,
            has_signature=self.has_signature,
            normal_code_offset=normal_code_offset,
            engineering_mode=False,
            size=size,
            date=self.date,
        )

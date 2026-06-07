"""S11 VUC system info parsing."""

import dataclasses
import datetime
import enum
import struct
from typing import ClassVar, Self

from phison_s11 import data as s11_data
from phison_s11 import firmware
from phison_s11.ata import identify

_MONTHS: list[str] = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _parse_date(raw: bytes) -> datetime.date:
    string: str = raw.decode()
    year: int = int(string[:4])
    month: int = _MONTHS.index(string[4:7]) + 1
    day: int = int(string[7:])
    return datetime.date(year, month, day)


class VUCMode(enum.IntEnum):
    """VUC lock mode.

    Attributes:
        LOCKED: Locked.
        ENGINEERING: Engineering.
        UNLOCKED: Unlocked.
        NO_LOCK: No lock (no key configured).

    """

    LOCKED = 1
    ENGINEERING = 2
    UNLOCKED = 3
    NO_LOCK = 4


@dataclasses.dataclass(frozen=True)
class SystemInfo:
    """System information.

    Attributes:
        SIZE: Size in bytes.
        ce_count: Number of flash chip enables.
        channel_count: Number of flash channels.
        sram_size: SRAM size in mebibytes.
        pages_per_block: Pages per flash block if any.
        dies_per_ce: Dies per chip enable if any.
        die_interleave: Die-level interleaving enabled, requires multi-die flash.
        die_interleave_factor: Number of die groups a CE is split into for interleaving.
        blocks_per_die: Blocks per die if any.
        blocks_per_ce: Blocks per chip enable if any.
        sectors_per_page: Sectors per flash page if any.
        channel_interleave_factor: Number of blocks per channel in a superblock if any.
        planes_per_die: Planes per die if any.
        form_factor: Drive form factor if any.
        blocks_per_superblock: Blocks per superblock if any.
        die_stride: Stride between dies in a flash block address value.
        superblock_index_count: Total flash size divided by superblock size.
        sectors_per_superblock: Sectors per superblock if any.
        superblock_count: Useable/allocated superblock count if any.
        ce_error_bitmap: Bitmask of chip enable addresses with errors.
        sectors_per_superblock_page: Sectors per superblock page if any.
        flash_interface: Flash interface type if any.
        protected_mode: Protected mode enabled.
        firmware_update_count: Total firmware update count.
        system_unit_update_count: Total system unit (drive config data) update count.
        ce_bitmap: Bitmask of active chip enable addresses.
        firmware_version: Firmware version.
        firmware_date: Firmware date.
        pram_icode_programmed: PRAM icode programmed.
        physical_page_size: Page size including metadata if any.
        vuc_key: VUC lock key index if any.
        vuc_mode: VUC lock mode if any.

    """

    _MAX_CE_COUNT: ClassVar[int] = 16
    _CHANNEL_COUNT: ClassVar[int] = 2
    _SRAM_SIZE: ClassVar[int] = 32
    _STRUCT: ClassVar[struct.Struct] = struct.Struct(
        "<B"
        "x"
        "2B"
        "H"
        "B"
        "3x"
        "2B"
        "4x"
        "L"
        "8x"
        "L"
        "8x"
        "L"
        "28x"
        "2B"
        "x"
        "B"
        "124x"
        "B"
        "3x"
        "H"
        "2x"
        "3L"
        "16x"
        "2L"
        "B"
        "2x"
        "B"
        "2H"
        "76x"
        "Q"
        "8x"
        "8s"
        "9s"
        "2x"
        "B"
        "54x"
        "H"
        "4x"
        "2s"
        "B"
        "35x"
        "L"
        "46x",
    )
    SIZE: ClassVar[int] = _STRUCT.size

    ce_count: int
    channel_count: int
    sram_size: int
    pages_per_block: int | None
    dies_per_ce: int | None
    die_interleave: bool
    die_interleave_factor: int | None
    blocks_per_die: int | None
    blocks_per_ce: int | None
    sectors_per_page: int | None
    channel_interleave_factor: int | None
    planes_per_die: int | None
    form_factor: identify.FormFactor | None
    blocks_per_superblock: int | None
    die_stride: int | None
    superblock_index_count: int | None
    sectors_per_superblock: int | None
    superblock_count: int | None
    ce_error_bitmap: int
    sectors_per_superblock_page: int | None
    flash_interface: s11_data.FlashInterface | None
    protected_mode: bool
    firmware_update_count: int
    system_unit_update_count: int
    ce_bitmap: int
    firmware_version: firmware.Version
    firmware_date: datetime.date
    pram_icode_programmed: bool
    physical_page_size: int | None
    vuc_key: int | None
    vuc_mode: VUCMode | None

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Unpack system info from bytes.

        Args:
            data: Bytes.

        Returns:
            System info.

        """
        ce_count: int
        channel_count: int
        sram_size_raw: int
        pages_per_block_raw: int
        dies_per_ce_raw: int
        die_interleave_raw: int
        die_interleave_factor_raw: int
        blocks_per_die_raw: int
        blocks_per_ce_raw: int
        sectors_per_page_raw: int
        channel_interleave_factor_raw: int
        planes_per_die_raw: int
        form_factor_raw: int
        blocks_per_superblock_raw: int
        die_stride_raw: int
        superblock_index_count_raw: int
        sectors_per_superblock_raw: int
        superblock_count_raw: int
        ce_error_bitmap_low: int
        sectors_per_superblock_page_raw: int
        flash_interface_raw: int
        protected_mode_raw: int
        firmware_update_count: int
        system_unit_update_count: int
        ce_bitmap: int
        firmware_version_raw: bytes
        firmware_date_raw: bytes
        pram_icode_programmed_raw: int
        physical_page_size_raw: int
        vuc_key_raw: bytes
        vuc_mode_raw: int
        ce_error_bitmap_high: int
        (
            ce_count,
            channel_count,
            sram_size_raw,
            pages_per_block_raw,
            dies_per_ce_raw,
            die_interleave_raw,
            die_interleave_factor_raw,
            blocks_per_die_raw,
            blocks_per_ce_raw,
            sectors_per_page_raw,
            channel_interleave_factor_raw,
            planes_per_die_raw,
            form_factor_raw,
            blocks_per_superblock_raw,
            die_stride_raw,
            superblock_index_count_raw,
            sectors_per_superblock_raw,
            superblock_count_raw,
            ce_error_bitmap_low,
            sectors_per_superblock_page_raw,
            flash_interface_raw,
            protected_mode_raw,
            firmware_update_count,
            system_unit_update_count,
            ce_bitmap,
            firmware_version_raw,
            firmware_date_raw,
            pram_icode_programmed_raw,
            physical_page_size_raw,
            vuc_key_raw,
            vuc_mode_raw,
            ce_error_bitmap_high,
        ) = cls._STRUCT.unpack(data)

        if not (ce_count <= cls._MAX_CE_COUNT):
            raise ValueError("Invalid CE count", ce_count)

        if channel_count != cls._CHANNEL_COUNT:
            raise ValueError("Invalid channel count", channel_count)

        sram_size: int = 1 << sram_size_raw
        if sram_size != cls._SRAM_SIZE:
            raise ValueError("Invalid SRAM size", sram_size)

        pages_per_block: int | None = pages_per_block_raw or None
        dies_per_ce: int | None = dies_per_ce_raw or None
        die_interleave: bool = bool(die_interleave_raw)
        die_interleave_factor: int | None = die_interleave_factor_raw or None
        blocks_per_die: int | None = blocks_per_die_raw or None
        blocks_per_ce: int | None = blocks_per_ce_raw or None
        sectors_per_page: int | None = sectors_per_page_raw or None
        channel_interleave_factor: int | None = channel_interleave_factor_raw or None
        planes_per_die: int | None = planes_per_die_raw or None

        form_factor: identify.FormFactor | None = identify.FormFactor.parse(
            form_factor_raw,
        )

        blocks_per_superblock: int | None = blocks_per_superblock_raw or None
        die_stride: int | None = die_stride_raw or None
        superblock_index_count: int | None = superblock_index_count_raw or None
        sectors_per_superblock: int | None = sectors_per_superblock_raw or None
        superblock_count: int | None = superblock_count_raw or None
        ce_error_bitmap: int = ce_error_bitmap_low | (ce_error_bitmap_high << 32)
        sectors_per_superblock_page: int | None = (
            sectors_per_superblock_page_raw or None
        )

        flash_interface: s11_data.FlashInterface | None = s11_data.FlashInterface.parse(
            flash_interface_raw,
        )

        protected_mode: bool = bool(protected_mode_raw)

        firmware_version: firmware.Version = firmware.Version.from_string(
            identify.decode_string(firmware_version_raw),
        )

        firmware_date: datetime.date = _parse_date(firmware_date_raw)
        pram_icode_programmed: bool = bool(pram_icode_programmed_raw)
        physical_page_size: int | None = physical_page_size_raw or None
        vuc_key: int | None = int.from_bytes(vuc_key_raw, "big") or None
        vuc_mode: VUCMode | None = None if not vuc_mode_raw else VUCMode(vuc_mode_raw)

        if dies_per_ce and dies_per_ce > 1 and not die_stride:
            raise ValueError("Multi-die flash missing die stride")

        return cls(
            ce_count=ce_count,
            channel_count=channel_count,
            sram_size=sram_size,
            pages_per_block=pages_per_block,
            dies_per_ce=dies_per_ce,
            die_interleave=die_interleave,
            die_interleave_factor=die_interleave_factor,
            blocks_per_die=blocks_per_die,
            blocks_per_ce=blocks_per_ce,
            sectors_per_page=sectors_per_page,
            channel_interleave_factor=channel_interleave_factor,
            planes_per_die=planes_per_die,
            form_factor=form_factor,
            blocks_per_superblock=blocks_per_superblock,
            die_stride=die_stride,
            superblock_index_count=superblock_index_count,
            sectors_per_superblock=sectors_per_superblock,
            superblock_count=superblock_count,
            ce_error_bitmap=ce_error_bitmap,
            sectors_per_superblock_page=sectors_per_superblock_page,
            flash_interface=flash_interface,
            protected_mode=protected_mode,
            firmware_update_count=firmware_update_count,
            system_unit_update_count=system_unit_update_count,
            ce_bitmap=ce_bitmap,
            firmware_version=firmware_version,
            firmware_date=firmware_date,
            pram_icode_programmed=pram_icode_programmed,
            physical_page_size=physical_page_size,
            vuc_key=vuc_key,
            vuc_mode=vuc_mode,
        )

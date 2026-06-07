"""ATA command functionality.

Attributes:
    SECTOR_SIZE: Standard sector size.
    SMART_KEY_LBA: SMART command LBA key.

"""

import dataclasses
import enum
import struct
import types
from typing import ClassVar, Self

SECTOR_SIZE: int = 512
SMART_KEY_LBA: int = 0xC24F << 8


class Command(enum.IntEnum):
    """ATA command opcodes.

    Attributes:
        NOP: NOP command.
        DATA_SET_MANAGEMENT: DATA SET MANAGEMENT command.
        READ_SECTORS: READ SECTORS command.
        READ_SECTORS_NO_RETRY: READ SECTORS without retry command.
        READ_SECTORS_EXT: READ SECTORS EXT command.
        READ_DMA_EXT: READ DMA EXT command.
        READ_LOG_EXT: READ LOG EXT command.
        WRITE_SECTORS_NO_RETRY: WRITE SECTORS without retry command.
        WRITE_LOG_EXT: WRITE LOG EXT command.
        ZERO_EXT: ZERO EXT command.
        EXECUTE_DEVICE_DIAGNOSTIC: EXECUTE DEVICE DIAGNOSTIC command.
        DOWNLOAD_MICROCODE: DOWNLOAD MICROCODE command.
        SMART: SMART command.
        STANDBY_IMMEDIATE: STANDBY IMMEDIATE command.
        IDENTIFY_DEVICE: IDENTIFY DEVICE command.

    """

    NOP = 0x0
    DATA_SET_MANAGEMENT = 0x6
    READ_SECTORS = 0x20
    READ_SECTORS_NO_RETRY = 0x21
    READ_SECTORS_EXT = 0x24
    READ_DMA_EXT = 0x25
    READ_LOG_EXT = 0x2F
    WRITE_SECTORS_NO_RETRY = 0x31
    WRITE_LOG_EXT = 0x3F
    ZERO_EXT = 0x44
    EXECUTE_DEVICE_DIAGNOSTIC = 0x90
    DOWNLOAD_MICROCODE = 0x92
    SMART = 0xB0
    STANDBY_IMMEDIATE = 0xE0
    IDENTIFY_DEVICE = 0xEC


class DLMCSubcommand(enum.IntEnum):
    """DOWNLOAD MICROCODE subcommand.

    Attributes:
        SEGMENTED: Mode 3 segmented.
        FULL: Mode 7 full.

    """

    SEGMENTED = 3
    FULL = 7


class SMARTSubcommand(enum.IntEnum):
    """ATA command SMART (0xB0) subcommands.

    Attributes:
        READ_DATA: READ DATA.
        READ_THRESHOLDS: READ ATTRIBUTE THRESHOLDS (obsolete).
        AUTOSAVE: ENABLE/DISABLE ATTRIBUTE AUTOSAVE.
        SAVE: SAVE ATTRIBUTE VALUES (vendor).
        EXECUTE_OFFLINE: EXECUTE OFF-LINE IMMEDIATE.
        READ_LOG: READ LOG.
        WRITE_LOG: WRITE LOG.
        WRITE_THRESHOLDS: WRITE ATTRIBUTE THRESHOLDS (obsolete).
        ENABLE: ENABLE OPERATIONS.
        DISABLE: DISABLE OPERATIONS.
        RETURN_STATUS: RETURN STATUS.

    """

    READ_DATA = 0xD0
    READ_THRESHOLDS = 0xD1
    AUTOSAVE = 0xD2
    SAVE = 0xD3
    EXECUTE_OFFLINE = 0xD4
    READ_LOG = 0xD5
    WRITE_LOG = 0xD6
    WRITE_THRESHOLDS = 0xD7
    ENABLE = 0xD8
    DISABLE = 0xD9
    RETURN_STATUS = 0xDA


class GPLLog(enum.IntEnum):
    """General Purpose Log addresses.

    Attributes:
        DIRECTORY: Log directory.
        SUMMARY_SMART_ERROR: Summary SMART error log.
        COMPREHENSIVE_SMART_ERROR: Comprehensive SMART error log.
        EXT_COMPREHENSIVE_SMART_ERROR: Extended comprehensive SMART
            error log.
        DEVICE_STATISTICS: Device statistics log.
        SMART_SELF_TEST: SMART self-test log.
        EXT_SMART_SELF_TEST: Extended SMART self-test log.
        POWER_CONDITIONS: Power conditions log.
        NCQ_COMMAND_ERROR: NCQ command error log.
        SATA_PHY_EVENT_COUNTERS: SATA PHY event counters log.
        CURRENT_DEVICE_INTERNAL_STATUS: Current device internal
            status log.
        SAVED_DEVICE_INTERNAL_STATUS: Saved device internal status
            log.
        IDENTIFY_DEVICE_DATA: Identify device data log.
        SCT_COMMAND_STATUS: SCT command status log.
        SCT_DATA_TRANSFER: SCT data transfer log.

    """

    DIRECTORY = 0x0
    SUMMARY_SMART_ERROR = 0x1
    COMPREHENSIVE_SMART_ERROR = 0x2
    EXT_COMPREHENSIVE_SMART_ERROR = 0x3
    DEVICE_STATISTICS = 0x4
    SMART_SELF_TEST = 0x6
    EXT_SMART_SELF_TEST = 0x7
    POWER_CONDITIONS = 0x8
    NCQ_COMMAND_ERROR = 0x10
    SATA_PHY_EVENT_COUNTERS = 0x11
    CURRENT_DEVICE_INTERNAL_STATUS = 0x24
    SAVED_DEVICE_INTERNAL_STATUS = 0x25
    IDENTIFY_DEVICE_DATA = 0x30
    SCT_COMMAND_STATUS = 0xE0
    SCT_DATA_TRANSFER = 0xE1


@dataclasses.dataclass(frozen=True)
class GPLDirectory:
    """Directory of GPL logs.

    Attributes:
        version: GPL version.
        entries: Page count of each extant log.

    """

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(f"<{SECTOR_SIZE // 2}H")
    version: int
    entries: types.MappingProxyType[int, int]

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse GPL directory.

        Args:
            data: Raw log directory data.

        Returns:
            Parsed GPL Directory.

        """
        version, *page_counts = cls._STRUCT.unpack(data)

        entries: dict[int, int] = {
            GPLLog(log) if log in GPLLog else log: page_count
            for log, page_count in enumerate(page_counts, 1)
            if page_count
        }

        return cls(version, types.MappingProxyType(entries))


@dataclasses.dataclass
class CommandRegisters:
    """ATA command registers.

    Attributes:
        feature: Feature register.
        count: Count register.
        lba: LBA register.
        device: Device register.
        command: Command register.

    """

    feature: int = 0
    count: int = 0
    lba: int = 0
    device: int = 0
    command: int = 0


class StatusRegister(int):
    """ATA status register.

    Attributes:
        DEVICE_FAULT_MASK: Mask for device fault bit.
        ALIGNMENT_ERROR_MASK: Mask for alignment error bit.
        SENSE_DATA_AVAILABLE_MASK: Mask for sense data available bit.
        ERROR_MASK: Mask for error bit.

    """

    DEVICE_FAULT_MASK: int = 1 << 5
    ALIGNMENT_ERROR_MASK: int = 1 << 2
    SENSE_DATA_AVAILABLE_MASK: int = 1 << 1
    ERROR_MASK: int = 1 << 0

    @property
    def device_fault(self) -> bool:
        """Return device fault bit."""
        return (self & self.DEVICE_FAULT_MASK) != 0

    @property
    def alignment_error(self) -> bool:
        """Return alignment error bit."""
        return (self & self.ALIGNMENT_ERROR_MASK) != 0

    @property
    def sense_data_available(self) -> bool:
        """Return sense data available bit."""
        return (self & self.SENSE_DATA_AVAILABLE_MASK) != 0

    @property
    def error(self) -> bool:
        """Return error bit."""
        return (self & self.ERROR_MASK) != 0


@dataclasses.dataclass(frozen=True)
class ResultRegisters:
    """ATA result registers.

    Attributes:
        error: Error register.
        count: Count register.
        lba: LBA register.
        device: Device register.
        status: Status register.

    """

    error: int = 0
    count: int = 0
    lba: int = 0
    device: int = 0
    status: StatusRegister = dataclasses.field(
        default_factory=lambda: StatusRegister(0),
    )

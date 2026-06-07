"""SCSI command functionality."""

import abc
import dataclasses
import enum
import struct
from typing import ClassVar

from phison_s11.ata import command as ata_command


class CDB(abc.ABC):
    """SCSI Command Descriptor Block base class."""

    @abc.abstractmethod
    def __bytes__(self) -> bytes:
        """Return bytes of CDB."""
        ...


class SATProtocol(enum.IntEnum):
    """SAT protocol field values.

    Attributes:
        NON_DATA: No data transfer.
        PIO_IN: PIO data-in.
        PIO_OUT: PIO data-out.
        DMA: DMA transfer.

    """

    NON_DATA = 3
    PIO_IN = 4
    PIO_OUT = 5
    DMA = 6


class SATTransferLength(enum.IntEnum):
    """SAT T_LENGTH field.

    Attributes:
        NONE: No transfer.
        FEATURES: Transfer length in Features.
        SECTOR_COUNT: Transfer length in Sector Count.

    """

    NONE = 0
    FEATURES = 1
    SECTOR_COUNT = 2


class SATTransferDirection(enum.IntEnum):
    """SAT T_DIR field.

    Attributes:
        TO_DEVICE: Transfer from host to device.
        FROM_DEVICE: Transfer from device to host.

    """

    TO_DEVICE = 0
    FROM_DEVICE = 1


@dataclasses.dataclass(frozen=True)
class ATAPassThrough16(CDB):
    """ATA PASS-THROUGH (16) CDB.

    Attributes:
        protocol: SAT protocol value.
        extend: LBA-48 (extended).
        off_line: Off-line timeout period.
        ck_cond: Check condition.
        t_type: Transfer logical sectors, instead of 512-byte blocks.
        t_dir: Transfer direction.
        byt_blok: t_length is in block units.
        t_length: Transfer length field location.
        registers: ATA registers.
        control: Control byte.

    """

    _OPCODE: ClassVar[int] = 0x85
    _STRUCT: ClassVar[struct.Struct] = struct.Struct(">3B 2H 6s 3B")

    protocol: SATProtocol
    extend: bool
    off_line: int
    ck_cond: bool
    t_type: bool
    t_dir: SATTransferDirection
    byt_blok: bool
    t_length: SATTransferLength
    registers: ata_command.CommandRegisters
    control: int

    def __bytes__(self) -> bytes:
        """Return bytes of CDB."""
        byte1: int = (self.protocol << 1) | int(self.extend)

        byte2: int = (
            ((self.off_line & 0b11) << 6)
            | (int(self.ck_cond) << 5)
            | (int(self.t_type) << 4)
            | (self.t_dir << 3)
            | (int(self.byt_blok) << 2)
            | self.t_length
        )

        lba_raw: bytearray = bytearray(self.registers.lba.to_bytes(6, "little"))
        lba_raw[::2], lba_raw[1::2] = lba_raw[3:], lba_raw[:3]

        return self._STRUCT.pack(
            self._OPCODE,
            byte1,
            byte2,
            self.registers.feature,
            self.registers.count,
            lba_raw,
            self.registers.device,
            self.registers.command,
            self.control,
        )

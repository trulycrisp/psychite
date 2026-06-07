"""SCSI sense functionality."""

import abc
import dataclasses
import enum
import struct
from typing import ClassVar, Self

from phison_s11.ata import command as ata_command


class ResponseCode(enum.IntEnum):
    """Sense response code.

    Attributes:
        FIXED_CURRENT: Fixed format, current errors.
        FIXED_DEFERRED: Fixed format, deferred errors.
        DESCRIPTOR_CURRENT: Descriptor format, current errors.
        DESCRIPTOR_DEFERRED: Descriptor format, deferred errors.

    """

    FIXED_CURRENT = 0x70
    FIXED_DEFERRED = 0x71
    DESCRIPTOR_CURRENT = 0x72
    DESCRIPTOR_DEFERRED = 0x73


class SenseKey(enum.IntEnum):
    """Sense key.

    Attributes:
        NO_SENSE: No specific sense information.
        RECOVERED_ERROR: Command completed with recovery action.
        NOT_READY: Logical unit not ready.
        MEDIUM_ERROR: Unrecoverable read/write error.
        HARDWARE_ERROR: Non-recoverable hardware failure.
        ILLEGAL_REQUEST: Illegal parameter in the CDB.
        UNIT_ATTENTION: Unit attention condition.
        DATA_PROTECT: Read/write to a protected block.
        BLANK_CHECK: Blank or formatted media encountered.
        VENDOR_SPECIFIC: Vendor-specific sense key.
        COPY_ABORTED: COPY or COMPARE command aborted.
        ABORTED_COMMAND: Command aborted by the device.
        VOLUME_OVERFLOW: Buffered write past end of medium.
        MISCOMPARE: Source and medium data differ.
        COMPLETED: Command completed with sense data.

    """

    NO_SENSE = 0x0
    RECOVERED_ERROR = 0x1
    NOT_READY = 0x2
    MEDIUM_ERROR = 0x3
    HARDWARE_ERROR = 0x4
    ILLEGAL_REQUEST = 0x5
    UNIT_ATTENTION = 0x6
    DATA_PROTECT = 0x7
    BLANK_CHECK = 0x8
    VENDOR_SPECIFIC = 0x9
    COPY_ABORTED = 0xA
    ABORTED_COMMAND = 0xB
    VOLUME_OVERFLOW = 0xD
    MISCOMPARE = 0xE
    COMPLETED = 0xF

    @property
    def error(self) -> bool:
        """Does sense key represent an error."""
        return self in (
            self.NOT_READY,
            self.MEDIUM_ERROR,
            self.HARDWARE_ERROR,
            self.ILLEGAL_REQUEST,
            self.DATA_PROTECT,
            self.COPY_ABORTED,
            self.ABORTED_COMMAND,
            self.VOLUME_OVERFLOW,
            self.MISCOMPARE,
        )


class Sense(abc.ABC):
    """Sense base class."""

    @classmethod
    @abc.abstractmethod
    def parse(
        cls,
        response_code: ResponseCode,
        data: bytes,
    ) -> Self:
        """Parse sense data.

        Args:
            response_code: Already-parsed response code.
            data: Raw sense data.

        Returns:
            Parsed sense.

        """
        ...


@dataclasses.dataclass(frozen=True)
class ATAReturnFixed:
    """SAT ATA registers from fixed-format sense.

    Attributes:
        registers: ATA registers.
        extend: LBA-48 extended.
        count_upper_nonzero: Count register upper byte was non-zero.
        lba_upper_nonzero: LBA registers upper bytes were non-zero.
        log_index: Index in the ATA PASS-THROUGH Results log page, if logged.

    """

    registers: ata_command.ResultRegisters
    extend: bool
    count_upper_nonzero: bool
    lba_upper_nonzero: bool
    log_index: int | None


@dataclasses.dataclass(frozen=True)
class FixedSense(Sense):
    """Fixed-format sense data.

    Attributes:
        valid: Information field valid (otherwise vendor-specific).
        response_code: Response code.
        filemark: Filemark detected.
        eom: End-of-medium.
        ili: Incorrect length indicator.
        sdat_ovfl: Sense data overflow.
        sense_key: Sense key.
        information: Information.
        csi: Command-Specific Information if any.
        asc: Additional Sense Code if any.
        ascq: Additional Sense Code Qualifier if any.
        fru: Field Replaceable Unit if any.
        sks: Sense-Key Specific if any.
        sksv: Sense-Key Specific Valid if any.

    """

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(">B x B 4s B")
    _CSI_OFFSET: ClassVar[int] = 0
    _CSI_SIZE: ClassVar[int] = 4
    _ASC_OFFSET: ClassVar[int] = _CSI_OFFSET + _CSI_SIZE
    _ASC_SIZE: ClassVar[int] = 1
    _ASCQ_OFFSET: ClassVar[int] = _ASC_OFFSET + _ASC_SIZE
    _ASCQ_SIZE: ClassVar[int] = 1
    _FRU_OFFSET: ClassVar[int] = _ASCQ_OFFSET + _ASCQ_SIZE
    _FRU_SIZE: ClassVar[int] = 1
    _SKS_OFFSET: ClassVar[int] = _FRU_OFFSET + _FRU_SIZE
    _SKS_SIZE: ClassVar[int] = 3

    valid: bool
    response_code: ResponseCode
    filemark: bool
    eom: bool
    ili: bool
    sdat_ovfl: bool
    sense_key: SenseKey
    information: bytes
    csi: bytes | None
    asc: int | None
    ascq: int | None
    fru: int | None
    sks: bytes | None
    sksv: bool | None

    @classmethod
    def parse(cls, response_code: ResponseCode, data: bytes) -> Self:
        """Parse fixed-format sense data.

        Args:
            response_code: Already-parsed response code.
            data: Raw sense data.

        Returns:
            Parsed sense.

        """
        byte0: int
        byte2: int
        information: bytes
        additional_length: int
        byte0, byte2, information, additional_length = cls._STRUCT.unpack_from(data)

        valid: bool = bool(byte0 & (1 << 7))
        filemark: bool = bool(byte2 & (1 << 7))
        eom: bool = bool(byte2 & (1 << 6))
        ili: bool = bool(byte2 & (1 << 5))
        sdat_ovfl: bool = bool(byte2 & (1 << 4))
        sense_key: SenseKey = SenseKey(byte2 & 0xF)

        additional: bytes = data[
            cls._STRUCT.size : cls._STRUCT.size + additional_length
        ]

        csi_raw: bytes
        asc_raw: bytes
        ascq_raw: bytes
        fru_raw: bytes
        sks_raw: bytes
        csi_raw, asc_raw, ascq_raw, fru_raw, sks_raw = (
            additional[x : x + y]
            for x, y in (
                (cls._CSI_OFFSET, cls._CSI_SIZE),
                (cls._ASC_OFFSET, cls._ASC_SIZE),
                (cls._ASCQ_OFFSET, cls._ASCQ_SIZE),
                (cls._FRU_OFFSET, cls._FRU_SIZE),
                (cls._SKS_OFFSET, cls._SKS_SIZE),
            )
        )

        csi: bytes | None = csi_raw or None
        asc: int | None
        ascq: int | None
        fru: int | None
        asc, ascq, fru = (
            int.from_bytes(x) if x else None for x in (asc_raw, ascq_raw, fru_raw)
        )

        sks: bytes | None = sks_raw or None
        sksv: bool | None = bool(sks_raw[0] & (1 << 7)) if sks_raw else None

        return cls(
            valid=valid,
            response_code=response_code,
            filemark=filemark,
            eom=eom,
            ili=ili,
            sdat_ovfl=sdat_ovfl,
            sense_key=sense_key,
            information=information,
            csi=csi,
            asc=asc,
            ascq=ascq,
            fru=fru,
            sks=sks,
            sksv=sksv,
        )

    @property
    def ata_return(self) -> ATAReturnFixed | None:
        """SAT ATA return if any."""
        # Requires CSI field
        if not self.csi:
            return None

        # Don't check valid before parsing information,
        # some SATLs seem not to set it
        error: int
        status: int
        device: int
        count: int
        error, status, device, count = self.information

        # valid ATA status register should never be 0
        if not status:
            return None

        csi_byte0: int = self.csi[0]
        extend: bool = bool(csi_byte0 & (1 << 7))
        count_upper_nonzero: bool = bool(csi_byte0 & (1 << 6))
        lba_upper_nonzero: bool = bool(csi_byte0 & (1 << 5))
        log_index: int | None = (csi_byte0 & 0xF) or None

        lba: int = int.from_bytes(self.csi[1:], "little")

        registers: ata_command.ResultRegisters = ata_command.ResultRegisters(
            error=error,
            count=count,
            lba=lba,
            device=device,
            status=ata_command.StatusRegister(status),
        )

        return ATAReturnFixed(
            registers=registers,
            extend=extend,
            count_upper_nonzero=count_upper_nonzero,
            lba_upper_nonzero=lba_upper_nonzero,
            log_index=log_index,
        )


class DescriptorType(enum.IntEnum):
    """Sense descriptor type.

    Attributes:
        INFORMATION: Information descriptor.
        COMMAND_SPECIFIC: Command-specific information descriptor.
        SENSE_KEY_SPECIFIC: Sense key specific descriptor.
        FRU: Field Replaceable Unit descriptor.
        STREAM: Stream commands descriptor.
        ATA_RETURN: ATA Return descriptor.

    """

    INFORMATION = 0x0
    COMMAND_SPECIFIC = 0x1
    SENSE_KEY_SPECIFIC = 0x2
    FRU = 0x3
    STREAM = 0x4
    ATA_RETURN = 0x9


class Descriptor(abc.ABC):
    """Sense descriptor base class."""

    _STRUCT: struct.Struct = struct.Struct(">2B")

    @classmethod
    def parse(cls, data: bytes, offset: int) -> tuple[Self | None, int]:
        """Parse descriptor from bytes.

        Args:
            data: Bytes.
            offset: Data offset.

        Returns:
            (Descriptor if any, Descriptor size).

        """
        descriptor_type: int
        additional_length: int
        descriptor_type, additional_length = cls._STRUCT.unpack_from(data, offset)

        size: int = cls._STRUCT.size + additional_length
        additional: bytes = data[offset + cls._STRUCT.size : offset + size]

        descriptor: Self | None
        match descriptor_type:
            case DescriptorType.ATA_RETURN:
                descriptor = ATAReturnDescriptor.from_bytes(additional)
            case _:
                descriptor = None

        return descriptor, size

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse descriptor from bytes.

        Args:
            data: Bytes (descriptor additional).

        Returns:
            Parsed descriptor.

        """
        ...


@dataclasses.dataclass(frozen=True)
class ATAReturnDescriptor(Descriptor):
    """ATA Return descriptor.

    ATA registers returned from SAT command.

    Attributes:
        registers: ATA registers.

    """

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(">2B H 6s 2B")

    registers: ata_command.ResultRegisters

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse ATA return descriptor from bytes.

        Args:
            data: Bytes (descriptor additional).

        Returns:
            Parsed descriptor.

        """
        flags: int
        error: int
        count: int
        lba_raw: bytes
        device: int
        status: int
        (
            flags,
            error,
            count,
            lba_raw,
            device,
            status,
        ) = cls._STRUCT.unpack(data)

        lba: int = int.from_bytes(lba_raw[1::2], "little")

        extend: bool = bool(flags & (1 << 0))
        if extend:
            lba |= int.from_bytes(lba_raw[::2], "little") << 24
        else:
            count &= 0xFF

        return cls(
            registers=ata_command.ResultRegisters(
                error=error,
                count=count,
                lba=lba,
                device=device,
                status=ata_command.StatusRegister(status),
            ),
        )


@dataclasses.dataclass(frozen=True)
class DescriptorSense(Sense):
    """Descriptor-format sense data.

    Attributes:
        response_code: Response code.
        sense_key: Sense key.
        asc: Additional Sense Code.
        ascq: Additional Sense Code Qualifier.
        descriptors: Parsed sense descriptors.

    """

    _STRUCT: ClassVar[struct.Struct] = struct.Struct(">x 3B 3x B")

    response_code: ResponseCode
    sense_key: SenseKey
    asc: int
    ascq: int
    descriptors: tuple[Descriptor, ...]

    @classmethod
    def parse(
        cls,
        response_code: ResponseCode,
        data: bytes,
    ) -> Self:
        """Parse descriptor-format sense data.

        Args:
            response_code: Already-parsed response code.
            data: Raw sense data.

        Returns:
            Parsed sense.

        """
        byte1: int
        asc: int
        ascq: int
        additional_length: int
        byte1, asc, ascq, additional_length = cls._STRUCT.unpack_from(data)

        sense_key: SenseKey = SenseKey(byte1 & 0xF)

        descriptors: list[Descriptor] = []
        offset: int = cls._STRUCT.size

        while offset < cls._STRUCT.size + additional_length:
            descriptor: Descriptor | None
            descriptor_size: int
            descriptor, descriptor_size = Descriptor.parse(data, offset)

            if descriptor:
                descriptors.append(descriptor)

            offset += descriptor_size

        return cls(
            response_code=response_code,
            sense_key=sense_key,
            asc=asc,
            ascq=ascq,
            descriptors=tuple(descriptors),
        )

    def find_descriptor[T: Descriptor](self, descriptor_type: type[T]) -> T | None:
        """Find first descriptor of type.

        Args:
            descriptor_type: Descriptor type.

        Returns:
            Descriptor if any.

        """
        return next(
            (x for x in self.descriptors if isinstance(x, descriptor_type)),
            None,
        )


def parse(data: bytes) -> Sense:
    """Parse sense data.

    Args:
        data: Sense data.

    Returns:
        Parsed sense.

    """
    response_code: ResponseCode = ResponseCode(data[0] & 0b1111111)

    match response_code:
        case ResponseCode.FIXED_CURRENT | ResponseCode.FIXED_DEFERRED:
            return FixedSense.parse(response_code, data)
        case ResponseCode.DESCRIPTOR_CURRENT | ResponseCode.DESCRIPTOR_DEFERRED:
            return DescriptorSense.parse(response_code, data)
        case x:
            raise ValueError("Unsupported response code", x)

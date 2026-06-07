"""ATA drive interface."""

import dataclasses
import pathlib
import types
from typing import Self

from phison_s11.ata import command as ata_command
from phison_s11.ata import identify
from phison_s11.scsi import command as scsi_command
from phison_s11.scsi import drive as scsi_drive
from phison_s11.scsi import sense as scsi_sense


class Drive:
    """Drive.

    Attributes:
        DLMC_SEGMENT_SECTORS: Default segment sectors for DLMC.

    """

    DLMC_SEGMENT_SECTORS: int = 1

    def __init__(self, path: pathlib.Path) -> None:
        """Open ATA drive.

        Args:
            path: Path to drive.

        """
        self._scsi: scsi_drive.Drive = scsi_drive.Drive(path)

    def __enter__(self) -> Self:
        """Context manager enter.

        Returns:
            Self.

        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        """Context manager exit.

        Args:
            exc_type: Exception type.
            exc_value: Exception value.
            traceback: Exception traceback.

        """
        self.close()

    def close(self) -> None:
        """Close drive."""
        self._scsi.close()

    def _parse_sense(
        self,
        sense: scsi_sense.Sense,
    ) -> ata_command.ResultRegisters | None:
        registers: ata_command.ResultRegisters | None
        if isinstance(sense, scsi_sense.FixedSense):
            ata_return: scsi_sense.ATAReturnFixed | None = sense.ata_return
            registers = ata_return.registers if ata_return else None
        else:
            descriptor: scsi_sense.ATAReturnDescriptor | None = sense.find_descriptor(
                scsi_sense.ATAReturnDescriptor,
            )
            registers = descriptor.registers if descriptor else None

        if registers and (registers.status.device_fault or registers.status.error):
            raise OSError(f"ATA command failed {registers}")

        if sense.sense_key.error:
            raise OSError(f"SCSI sense error {sense}")

        return registers

    def command(
        self,
        registers: ata_command.CommandRegisters,
        data: bytes | int | None = None,
        dma: bool = False,
        extend: bool = False,
        timeout: int = scsi_drive.DEFAULT_TIMEOUT,
    ) -> tuple[bytes | None, ata_command.ResultRegisters | None]:
        """Execute ATA command.

        Args:
            registers: Input registers.
            data: Data for write or data-size for read if any.
            dma: DMA.
            extend: LBA-48 extended.
            timeout: Timeout in seconds.

        Returns:
            Read data and output registers, if any.

        Raises:
            OSError: Command failed.

        """
        is_write: bool = isinstance(data, bytes)
        data_size: int = len(data) if is_write else data or 0

        if data_size:
            # For SAT passthrough with data, count register must match size
            count: int = -(data_size // -ata_command.SECTOR_SIZE)
            registers = dataclasses.replace(registers, count=count)

        protocol: scsi_command.SATProtocol
        if not data:
            protocol = scsi_command.SATProtocol.NON_DATA
        elif dma:
            protocol = scsi_command.SATProtocol.DMA
        elif is_write:
            protocol = scsi_command.SATProtocol.PIO_OUT
        else:
            protocol = scsi_command.SATProtocol.PIO_IN

        t_dir: scsi_command.SATTransferDirection = (
            scsi_command.SATTransferDirection.TO_DEVICE
            if is_write or not data
            else scsi_command.SATTransferDirection.FROM_DEVICE
        )

        t_length: scsi_command.SATTransferLength = (
            scsi_command.SATTransferLength.NONE
            if not data
            else scsi_command.SATTransferLength.SECTOR_COUNT
        )

        cdb: scsi_command.ATAPassThrough16 = scsi_command.ATAPassThrough16(
            protocol=protocol,
            extend=extend,
            off_line=0,
            ck_cond=True,
            t_type=False,
            t_dir=t_dir,
            byt_blok=True,
            t_length=t_length,
            registers=registers,
            control=0,
        )

        # Round up data to sector size multiple for SCSI
        scsi_data: bytes | int | None
        if not data:
            scsi_data = None
        elif is_write:
            scsi_data = data + b"\0" * (-len(data) % ata_command.SECTOR_SIZE)
        else:
            scsi_data = -(data // -ata_command.SECTOR_SIZE) * ata_command.SECTOR_SIZE

        out_data: bytes | None
        sense: scsi_sense.Sense | None
        out_data, sense = self._scsi.command(cdb, scsi_data, timeout)

        # Parse/handle sense
        out_registers: ata_command.ResultRegisters | None = (
            self._parse_sense(sense) if sense else None
        )

        # Verify out data size matches requested
        if out_data is not None and len(out_data) != scsi_data:
            raise OSError(f"Data size mismatch {len(out_data)} != {scsi_data}")

        # Truncate out data to read size
        if out_data:
            out_data = out_data[:data_size]

        return out_data, out_registers

    def _cmd_read_ext(
        self,
        command: ata_command.Command,
        lba: int,
        size: int,
        dma: bool,
    ) -> bytes:
        if size <= 0:
            raise ValueError("Invalid size", size)

        device: int = 1 << 6

        data: bytes
        data, _ = self.command(
            ata_command.CommandRegisters(
                lba=lba,
                device=device,
                command=command,
            ),
            data=size,
            dma=dma,
            extend=True,
        )

        return data

    def cmd_read_sectors_ext(self, lba: int, size: int) -> bytes:
        """Command READ SECTORS EXT.

        Args:
            lba: Logical block address.
            size: Size.

        Returns:
            Read data.

        """
        return self._cmd_read_ext(
            ata_command.Command.READ_SECTORS_EXT,
            lba,
            size,
            dma=False,
        )

    def cmd_read_dma_ext(self, lba: int, size: int) -> bytes:
        """Command READ DMA EXT.

        Args:
            lba: Logical block address.
            size: Size.

        Returns:
            Read data.

        """
        return self._cmd_read_ext(ata_command.Command.READ_DMA_EXT, lba, size, dma=True)

    def cmd_identify_device(self) -> identify.Identify:
        """Command IDENTIFY DEVICE.

        Returns:
            Response.

        """
        data: bytes
        data, _ = self.command(
            ata_command.CommandRegisters(command=ata_command.Command.IDENTIFY_DEVICE),
            ata_command.SECTOR_SIZE,
        )

        return identify.Identify.from_bytes(data)

    def cmd_download_microcode(
        self,
        data: bytes,
        subcommand: int,
        offset: int = 0,
    ) -> None:
        """Command DOWNLOAD MICROCODE.

        Args:
            data: Data.
            subcommand: Subcommand field.
            offset: Buffer offset field.

        """
        if not data:
            raise ValueError("Invalid data size", len(data))

        # DLMC spec puts count upper-bits in lower-bits of LBA, incompatible
        # with SAT so this should only be used when count fits a single byte
        lba: int = offset << 8

        self.command(
            ata_command.CommandRegisters(
                feature=subcommand,
                lba=lba,
                command=ata_command.Command.DOWNLOAD_MICROCODE,
            ),
            data,
        )

    def cmd_download_microcode_full(self, data: bytes) -> None:
        """Command DOWNLOAD MICROCODE (mode 7/full).

        Args:
            data: Data.

        """
        self.cmd_download_microcode(data, ata_command.DLMCSubcommand.FULL)

    def cmd_download_microcode_segmented(
        self,
        data: bytes,
        segment_sectors: int | None = None,
    ) -> None:
        """Command DOWNLOAD MICROCODE (mode 3/segmented).

        Args:
            data: Data.
            segment_sectors: Sector count per segment if any, otherwise default.

        """
        if not data:
            raise ValueError("Invalid data size", len(data))

        if not segment_sectors:
            segment_sectors = self.DLMC_SEGMENT_SECTORS

        sector_count: int = -(len(data) // -ata_command.SECTOR_SIZE)
        segment_size: int = segment_sectors * ata_command.SECTOR_SIZE

        for offset in range(0, sector_count, segment_sectors):
            segment_start: int = offset * ata_command.SECTOR_SIZE
            segment: bytes = data[segment_start : segment_start + segment_size]

            self.cmd_download_microcode(
                segment,
                ata_command.DLMCSubcommand.SEGMENTED,
                offset,
            )

    def _cmd_smart(
        self,
        subcommand: ata_command.SMARTSubcommand,
        data: bytes | int | None,
        lba: int,
    ) -> bytes | None:
        lba = (lba & 0xFF) | ata_command.SMART_KEY_LBA

        out_data: bytes | None
        out_data, _ = self.command(
            ata_command.CommandRegisters(
                feature=subcommand,
                lba=lba,
                command=ata_command.Command.SMART,
            ),
            data,
        )

        return out_data

    def cmd_smart_read_log(
        self,
        log: int,
        size: int = ata_command.SECTOR_SIZE,
    ) -> bytes:
        """Command SMART subcommand READ LOG.

        Args:
            log: Log number.
            size: Read size.

        Returns:
            Read data.

        """
        if size <= 0:
            raise ValueError("Invalid size", size)

        return self._cmd_smart(ata_command.SMARTSubcommand.READ_LOG, size, log)

    def cmd_read_log_ext(
        self,
        log: int,
        page: int = 0,
        size: int = ata_command.SECTOR_SIZE,
    ) -> bytes:
        """Command READ LOG EXT.

        Args:
            log: Log.
            page: Page.
            size: Size.

        Returns:
            Log data.

        Raises:
            ValueError: Invalid size.

        """
        if size <= 0:
            raise ValueError("Invalid size", size)

        lba: int = log | ((page & 0xFF) << 8) | ((page & 0xFF00) << 24)

        data: bytes
        data, _ = self.command(
            ata_command.CommandRegisters(
                lba=lba,
                command=ata_command.Command.READ_LOG_EXT,
            ),
            size,
            extend=True,
        )

        return data

    def cmd_write_log_ext(self, log: int, data: bytes, page: int = 0) -> None:
        """Command WRITE LOG EXT.

        Args:
            log: Log.
            data: Data.
            page: Page.

        """
        lba: int = log | ((page & 0xFF) << 8) | ((page & 0xFF00) << 24)

        self.command(
            ata_command.CommandRegisters(
                lba=lba,
                command=ata_command.Command.WRITE_LOG_EXT,
            ),
            data,
            extend=True,
        )

    def gpl_directory(self) -> ata_command.GPLDirectory:
        """Read GPL directory (through READ LOG EXT).

        Returns:
            GPL directory.

        """
        return ata_command.GPLDirectory.from_bytes(
            self.cmd_read_log_ext(ata_command.GPLLog.DIRECTORY),
        )

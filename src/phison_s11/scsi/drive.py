"""SCSI drive interface.

Attributes:
    DEFAULT_TIMEOUT: Default command timeout in seconds.

"""

import enum
import pathlib
import sys
import types
from typing import Self

from phison_s11.scsi import command as scsi_command
from phison_s11.scsi import sense as scsi_sense

if sys.platform == "linux":
    from phison_s11.scsi import interface_linux as scsi_interface_os
elif sys.platform == "win32":
    from phison_s11.scsi import interface_windows as scsi_interface_os
else:
    raise OSError("Unsupported platform")

DEFAULT_TIMEOUT: int = 30


class Status(enum.IntEnum):
    """SCSI status.

    Attributes:
        GOOD: Command completed successfully.
        CHECK_CONDITION: Sense data available.
        CONDITION_MET: Requested condition met.
        BUSY: Logical unit is busy.
        RESERVATION_CONFLICT: Reservation conflict.
        TASK_SET_FULL: Task set full.
        ACA_ACTIVE: Auto Contingent Allegiance active.
        TASK_ABORTED: Task aborted.

    """

    GOOD = 0x0
    CHECK_CONDITION = 0x2
    CONDITION_MET = 0x4
    BUSY = 0x8
    RESERVATION_CONFLICT = 0x18
    TASK_SET_FULL = 0x28
    ACA_ACTIVE = 0x30
    TASK_ABORTED = 0x40


class Drive:
    """SCSI drive."""

    def __init__(self, path: pathlib.Path) -> None:
        """Initialise drive.

        Args:
            path: Drive path.

        """
        self._interface: scsi_interface_os.Interface | None = (
            scsi_interface_os.Interface(path)
        )

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
        try:
            if self._interface is not None:
                self._interface.close()
        finally:
            self._interface = None

    def command(
        self,
        cdb: scsi_command.CDB,
        data: bytes | int | None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> tuple[bytes | None, scsi_sense.Sense | None]:
        """SCSI command.

        Args:
            cdb: Command descriptor block.
            data: Data (write) or data-size (read), if any.
            timeout: Timeout in seconds.

        Returns:
            Read data if any, and sense if any.

        Raises:
            OSError: Command failed.
            RuntimeError: Drive closed.

        """
        if self._interface is None:
            raise RuntimeError("Closed")

        # Convert zero-size transfer to non-data
        data = data or None

        status: int
        data_out: bytes | None
        sense_raw: bytes | None
        status, data_out, sense_raw = self._interface.command(
            bytes(cdb),
            data,
            timeout,
        )

        sense: scsi_sense.Sense | None = None

        match status:
            case Status.GOOD:
                pass
            case Status.CHECK_CONDITION:
                if sense_raw:
                    sense = scsi_sense.parse(sense_raw)
            case x:
                raise OSError(f"SCSI status {x:#x}")

        return data_out, sense

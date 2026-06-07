"""Abstract SCSI OS interface.

Attributes:
    SENSE_BUFFER_SIZE: Stendard sense buffer size in bytes.

"""

import abc
import pathlib

SENSE_BUFFER_SIZE: int = 252


class Interface(abc.ABC):
    """Abstract base class for SCSI OS interface."""

    @abc.abstractmethod
    def __init__(self, path: pathlib.Path) -> None:
        """Initialise interface.

        Args:
            path: Drive path.

        """
        ...

    def __del__(self) -> None:
        """Delete interface."""
        try:
            self.close()
        except Exception:
            pass

    @abc.abstractmethod
    def close(self) -> None:
        """Close interface."""
        ...

    @abc.abstractmethod
    def command(
        self,
        cdb: bytes,
        data: bytes | int | None,
        timeout: int,
    ) -> tuple[int, bytes | None, bytes | None]:
        """Execute command.

        Args:
            cdb: Command descriptor block.
            data: Data (write) or data-size (read), if any.
            timeout: Timeout in seconds.

        Returns:
            (status, read data if any, sense if any).

        """
        ...

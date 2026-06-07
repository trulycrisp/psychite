"""SCSI Linux interface."""

import ctypes
import ctypes.util
import enum
import os
import pathlib

from phison_s11.scsi import interface

_MS_PER_SECOND: int = 1000
_SG_IO_INTERFACE_ID: int = ord("S")


class _Ioctl(enum.IntEnum):
    """Ioctl request codes.

    Attributes:
        SG_GET_VERSION_NUM: SG_GET_VERSION_NUM.
        SG_IO: SG_IO.

    """

    SG_GET_VERSION_NUM = 0x2282
    SG_IO = 0x2285


class _SGDirection(enum.IntEnum):
    """SG_IO transfer direction.

    Attributes:
        NONE: None.
        TO_DEV: To device.
        FROM_DEV: From device.

    """

    NONE = -1
    TO_DEV = -2
    FROM_DEV = -3


class _SGFlag(enum.IntFlag):
    """SG_IO header flags.

    Attributes:
        NO_DXFER: No data transfer.

    """

    NO_DXFER = 0x10000


class _SGIOHeader(ctypes.Structure):
    """sg_io_hdr_t structure."""

    _fields_ = [
        ("interface_id", ctypes.c_int),
        ("dxfer_direction", ctypes.c_int),
        ("cmd_len", ctypes.c_ubyte),
        ("mx_sb_len", ctypes.c_ubyte),
        ("iovec_count", ctypes.c_ushort),
        ("dxfer_len", ctypes.c_uint),
        ("dxferp", ctypes.c_void_p),
        ("cmdp", ctypes.c_void_p),
        ("sbp", ctypes.c_void_p),
        ("timeout", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("pack_id", ctypes.c_int),
        ("usr_ptr", ctypes.c_void_p),
        ("status", ctypes.c_ubyte),
        ("masked_status", ctypes.c_ubyte),
        ("msg_status", ctypes.c_ubyte),
        ("sb_len_wr", ctypes.c_ubyte),
        ("host_status", ctypes.c_ushort),
        ("driver_status", ctypes.c_ushort),
        ("resid", ctypes.c_int),
        ("duration", ctypes.c_uint),
        ("info", ctypes.c_uint),
    ]


class Interface(interface.Interface):
    """SCSI Linux interface."""

    def __init__(self, path: pathlib.Path) -> None:
        """Initialise interface.

        Args:
            path: Drive path.

        Raises:
            OSError: If libc not found or drive open failed.

        """
        libc_name: str | None = ctypes.util.find_library("c")

        if not libc_name:
            raise OSError("Couldn't find libc")

        self._libc: ctypes.CDLL = ctypes.CDLL(libc_name, use_errno=True)
        self._libc.ioctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p]
        self._libc.ioctl.restype = ctypes.c_int

        self._fd: int | None = os.open(path, os.O_RDWR | os.O_NONBLOCK)

        # Confirm handle supports SG
        sg_version: ctypes.c_int = ctypes.c_int()
        try:
            self._ioctl(_Ioctl.SG_GET_VERSION_NUM, sg_version)
        except Exception:
            self.close()
            raise

    def _ioctl(self, request: _Ioctl, argument: ctypes._CData) -> None:
        if self._fd is None:
            raise RuntimeError("Closed")

        ret: int = self._libc.ioctl(self._fd, request, ctypes.byref(argument))

        if ret < 0:
            errno: int = ctypes.get_errno()
            raise OSError(errno, os.strerror(errno))

    def close(self) -> None:
        """Close interface."""
        if self._fd is None:
            return

        try:
            os.close(self._fd)
        finally:
            self._fd = None

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

        Raises:
            OSError: On failure.

        """
        is_write: bool = isinstance(data, bytes)
        data_size: int = len(data) if is_write else data or 0

        data_buffer: ctypes.Array | None = (
            ctypes.create_string_buffer(data if is_write else b"", data_size)
            if data
            else None
        )

        dxfer_direction: _SGDirection = (
            _SGDirection.TO_DEV
            if is_write
            else _SGDirection.FROM_DEV
            if data
            else _SGDirection.NONE
        )

        dxferp: int | None = ctypes.addressof(data_buffer) if data_buffer else None
        cdb_buffer: ctypes.Array = ctypes.create_string_buffer(cdb, len(cdb))

        sense_buffer: ctypes.Array = ctypes.create_string_buffer(
            interface.SENSE_BUFFER_SIZE,
        )

        timeout_ms: int = timeout * _MS_PER_SECOND

        flags: _SGFlag = (
            _SGFlag.NO_DXFER if dxfer_direction == _SGDirection.NONE else _SGFlag(0)
        )

        sg_io_header: _SGIOHeader = _SGIOHeader(
            interface_id=_SG_IO_INTERFACE_ID,
            dxfer_direction=dxfer_direction,
            cmd_len=ctypes.sizeof(cdb_buffer),
            mx_sb_len=ctypes.sizeof(sense_buffer),
            dxfer_len=data_size,
            dxferp=dxferp,
            cmdp=ctypes.addressof(cdb_buffer),
            sbp=ctypes.addressof(sense_buffer),
            timeout=timeout_ms,
            flags=flags,
        )

        self._ioctl(_Ioctl.SG_IO, sg_io_header)

        status: int = sg_io_header.status
        host_status: int = sg_io_header.host_status
        sense: bytes | None = sense_buffer.raw[: sg_io_header.sb_len_wr] or None

        # If sense returned or non-zero status always return to SCSI layer to check
        # for SCSI-level errors, only otherwise check for SG-level errors
        if host_status and not status and not sense:
            raise OSError(f"SG_IO host status {host_status:#x}")

        data_size -= sg_io_header.resid
        data_out: bytes | None = (
            data_buffer.raw[:data_size] if data and not is_write else None
        )

        return status, data_out, sense

"""SCSI Windows interface."""

import ctypes
import pathlib
from ctypes import wintypes

from phison_s11.scsi import interface

_INVALID_HANDLE_VALUE: int = ctypes.c_void_p(-1).value
_OPEN_EXISTING: int = 3
_FILE_SHARE_READ: int = 1
_FILE_SHARE_WRITE: int = 2
_GENERIC_READ: int = 0x80000000
_GENERIC_WRITE: int = 0x40000000
_IOCTL_SCSI_PASS_THROUGH_DIRECT: int = 0x4D014
_SCSI_IOCTL_DATA_OUT: int = 0
_SCSI_IOCTL_DATA_IN: int = 1
_SCSI_IOCTL_DATA_UNSPECIFIED: int = 2
# Each adapters has an alignment requirement, this is the maximum possible
_ALIGNMENT: int = 512


class _SCSIPassThroughDirect(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("ScsiStatus", ctypes.c_ubyte),
        ("PathId", ctypes.c_ubyte),
        ("TargetId", ctypes.c_ubyte),
        ("Lun", ctypes.c_ubyte),
        ("CdbLength", ctypes.c_ubyte),
        ("SenseInfoLength", ctypes.c_ubyte),
        ("DataIn", ctypes.c_ubyte),
        ("DataTransferLength", wintypes.ULONG),
        ("TimeOutValue", wintypes.ULONG),
        ("DataBuffer", wintypes.LPVOID),
        ("SenseInfoOffset", wintypes.ULONG),
        ("Cdb", ctypes.c_ubyte * 16),
    ]


class _SCSIPassThroughDirectSense(ctypes.Structure):
    _fields_ = [
        ("sptd", _SCSIPassThroughDirect),
        (
            "sense",
            ctypes.c_ubyte * interface.SENSE_BUFFER_SIZE,
        ),
    ]


class Interface(interface.Interface):
    """SCSI Windows interface."""

    def __init__(self, path: pathlib.Path) -> None:
        """Initialise interface.

        Args:
            path: Drive path.

        Raises:
            OSError: Failed.

        """
        self._kernel32: ctypes.WinDLL = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )

        self._kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self._kernel32.CreateFileW.restype = wintypes.HANDLE

        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL

        self._kernel32.DeviceIoControl.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.LPDWORD,
            wintypes.LPVOID,
        ]
        self._kernel32.DeviceIoControl.restype = wintypes.BOOL

        self._handle: int | None = self._kernel32.CreateFileW(
            str(path),
            _GENERIC_READ | _GENERIC_WRITE,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE,
            None,
            _OPEN_EXISTING,
            0,
            None,
        )

        if self._handle == _INVALID_HANDLE_VALUE:
            raise OSError(
                "CreateFileW failed",
            ) from ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        """Close interface.

        Raises:
            OSError: Failed.

        """
        if self._handle is None:
            return

        try:
            if not self._kernel32.CloseHandle(self._handle):
                raise OSError(
                    "CloseHandle failed",
                ) from ctypes.WinError(
                    ctypes.get_last_error(),
                )
        finally:
            self._handle = None

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
            OSError: Command execution failed.

        """
        if self._handle is None:
            raise RuntimeError("Closed")

        is_write: bool = isinstance(data, bytes)
        data_size: int = len(data) if is_write else data or 0

        # IOCTL_SCSI_PASS_THROUGH_DIRECT requires an aligned data address
        data_buffer: ctypes.Array | None
        data_aligned_address: int | None
        if data:
            data_buffer = (ctypes.c_ubyte * (data_size + _ALIGNMENT - 1))()
            data_aligned_address = (
                -(-ctypes.addressof(data_buffer) // _ALIGNMENT) * _ALIGNMENT
            )

            if is_write:
                ctypes.memmove(data_aligned_address, data, data_size)
        else:
            data_buffer = None
            data_aligned_address = None

        data_in: int = (
            _SCSI_IOCTL_DATA_UNSPECIFIED
            if not data
            else _SCSI_IOCTL_DATA_OUT
            if is_write
            else _SCSI_IOCTL_DATA_IN
        )

        ioctl_buffer: _SCSIPassThroughDirectSense = _SCSIPassThroughDirectSense(
            sptd=_SCSIPassThroughDirect(
                Length=ctypes.sizeof(_SCSIPassThroughDirect),
                CdbLength=len(cdb),
                SenseInfoLength=_SCSIPassThroughDirectSense.sense.size,
                DataIn=data_in,
                DataTransferLength=data_size,
                TimeOutValue=timeout,
                DataBuffer=data_aligned_address,
                SenseInfoOffset=_SCSIPassThroughDirectSense.sense.offset,
            ),
        )
        ioctl_buffer.sptd.Cdb[: len(cdb)] = cdb

        bytes_returned: wintypes.DWORD = wintypes.DWORD(0)

        result: int = self._kernel32.DeviceIoControl(
            self._handle,
            _IOCTL_SCSI_PASS_THROUGH_DIRECT,
            ctypes.byref(ioctl_buffer),
            ctypes.sizeof(ioctl_buffer),
            ctypes.byref(ioctl_buffer),
            ctypes.sizeof(ioctl_buffer),
            ctypes.byref(bytes_returned),
            None,
        )

        status: int = ioctl_buffer.sptd.ScsiStatus
        sense: bytes | None = (
            bytes(ioctl_buffer.sense[: ioctl_buffer.sptd.SenseInfoLength]) or None
        )

        # Only handle as an OS-level error of if sense and status not received
        # otherwise return to SCSI layer to parse as SCSI error
        if not result and not status and not sense:
            raise OSError(
                "IOCTL_SCSI_PASS_THROUGH_DIRECT failed",
            ) from ctypes.WinError(ctypes.get_last_error())

        data_out: bytes | None = (
            ctypes.string_at(data_aligned_address, ioctl_buffer.sptd.DataTransferLength)
            if data and not is_write
            else None
        )

        return status, data_out, sense

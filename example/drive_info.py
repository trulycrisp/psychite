#!/usr/bin/env python

"""Drive information."""

import argparse
import dataclasses
import pathlib

from phison_s11 import drive as s11_drive

_EFUSE_WRITE_ADDRESS: int = 0x04002400
_EFUSE_WRITE_START: bytes = (3).to_bytes(4, "little")
_EFUSE_WRITE_END: bytes = (0).to_bytes(4, "little")
_EFUSE_DEBUG_ADDRESS: int = 0x04002440
_EFUSE_DEBUG_MASK_JTAG: int = 0b1
_EFUSE_DEBUG_MASK_UART: int = 0b10
_EFUSE_CONTROLLER_ID_ADDRESSES: tuple[int, ...] = (0x0400247C, 0x040024BC)
_EFUSE_CONTROLLER_VERSION_ADDRESS: int = 0x0400303E


@dataclasses.dataclass
class ControllerID:
    """Controller silicon ID decoded from eFuses.

    Attributes:
        x_coordination: Wafer X coordinate.
        y_coordination: Wafer Y coordinate.
        wafer_id: Wafer identifier.
        lot_id4: Lot ID digit 4.
        lot_id3: Lot ID digit 3.
        lot_id2: Lot ID digit 2.
        lot_id1: Lot ID digit 1.

    """

    x_coordination: int
    y_coordination: int
    wafer_id: int
    lot_id4: int
    lot_id3: int
    lot_id2: int
    lot_id1: int


@dataclasses.dataclass
class ControllerInfo:
    """Controller hardware information from efuses.

    Attributes:
        controller_id: Controller ID.
        controller_version: Hardware revision.
        jtag_disabled: JTAG disabled.
        uart_disabled: UART disabled.

    """

    controller_id: ControllerID
    controller_version: int
    jtag_disabled: bool
    uart_disabled: bool


def controller_info(drive: s11_drive.Drive) -> ControllerInfo:
    """Read controller hardware information.

    Returns:
        Controller information.

    """
    # Write to start eFuse access
    drive.vuc_write_register(_EFUSE_WRITE_ADDRESS, _EFUSE_WRITE_START)

    # Read debug efuse
    efuse_debug_data: bytes = drive.vuc_read_register(_EFUSE_DEBUG_ADDRESS, 4)

    # Read controller ID efuses
    controller_id_data: bytes = b"".join(
        drive.vuc_read_register(x, 4) for x in _EFUSE_CONTROLLER_ID_ADDRESSES
    )

    # Read controller version efuses
    controller_version_data: bytes = drive.vuc_read_register(
        _EFUSE_CONTROLLER_VERSION_ADDRESS,
        1,
    )

    # Write to end eFuse access
    drive.vuc_write_register(_EFUSE_WRITE_ADDRESS, _EFUSE_WRITE_END)

    efuse_debug: int = int.from_bytes(efuse_debug_data, "little")
    jtag_disabled: bool = bool(efuse_debug & _EFUSE_DEBUG_MASK_JTAG)
    uart_disabled: bool = bool(efuse_debug & _EFUSE_DEBUG_MASK_UART)

    controller_id: ControllerID = ControllerID(
        x_coordination=controller_id_data[0] & 0x3F,
        y_coordination=(controller_id_data[0] >> 6)
        | ((controller_id_data[1] & 0x1F) << 2),
        wafer_id=(controller_id_data[2] & 3) << 3 | (controller_id_data[1] >> 5),
        lot_id4=controller_id_data[2] >> 2,
        lot_id3=controller_id_data[3] & 0x3F,
        lot_id2=(controller_id_data[3] >> 6) | ((controller_id_data[4] & 0xF) << 2),
        lot_id1=(controller_id_data[4] >> 4) | ((controller_id_data[5] & 3) << 4),
    )

    controller_version: int = controller_version_data[0]

    return ControllerInfo(
        controller_id=controller_id,
        controller_version=controller_version,
        jtag_disabled=jtag_disabled,
        uart_disabled=uart_disabled,
    )


def _main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("drive")
    args: argparse.Namespace = parser.parse_args()
    path: pathlib.Path = pathlib.Path(args.drive)

    drive: s11_drive.Drive
    with s11_drive.Drive(path) as drive:
        print("===", "System Info", "===")
        print(drive.vuc_system_info())
        print()

        print("===", "Controller Info", "===")
        print(controller_info(drive))
        print()

        print("===", "Flash Info", "===")
        print(drive.vuc_flash_id_all())
        print()

        print("===", "Drive Info", "===")
        print(drive.vuc_read_info_block())


if __name__ == "__main__":
    _main()

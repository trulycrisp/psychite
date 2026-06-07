#!/usr/bin/env python

"""Update drive firmware."""

import argparse
import pathlib
from typing import TYPE_CHECKING

from phison_s11 import drive as s11_drive
from phison_s11 import firmware as s11_firmware

if TYPE_CHECKING:
    from phison_s11.ata import identify as ata_identify


def _main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("drive")
    parser.add_argument("firmware")
    args: argparse.Namespace = parser.parse_args()
    drive_path: pathlib.Path = pathlib.Path(args.drive)
    firmware_path: pathlib.Path = pathlib.Path(args.firmware)

    firmware: s11_firmware.Firmware = s11_firmware.Firmware.from_bytes(
        firmware_path.read_bytes(),
    )
    # Burner code unnecessary for DLMC
    firmware.burner_code = None

    print("Updating firmware:", firmware)

    drive: s11_drive.Drive
    with s11_drive.Drive(drive_path) as drive:
        drive.cmd_download_microcode_segmented(bytes(firmware_path.read_bytes()))
        identify: ata_identify.Identify = drive.cmd_identify_device()

    print("Firmware updated:", identify.firmware)


if __name__ == "__main__":
    _main()

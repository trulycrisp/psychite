#!/usr/bin/env python

"""Load drive with burner firmware."""

import argparse
import pathlib
from typing import TYPE_CHECKING

from phison_s11 import drive as s11_drive
from phison_s11 import firmware as s11_firmware

if TYPE_CHECKING:
    from phison_s11.ata import identify as ata_identify


def load_burner(
    drive: s11_drive.Drive,
    burner: s11_firmware.BurnerCode,
) -> None:
    """Load burner code.

    Args:
        drive: Drive.
        burner: Burner code.

    """
    # Load boot ROM code
    drive.mode = s11_drive.Mode.ROM

    # Load main code
    section: s11_firmware.CodeSection
    for section in burner.code_main:
        drive.vuc_program_pram(section.burner_address, bytes(section.code))

    # Run main code
    drive.vuc_jump()

    # Load icode
    icode_data: bytes | None = burner.code_icode_encrypted
    if icode_data:
        drive.vuc_program_pram_icode(icode_data)

    if drive.mode != s11_drive.Mode.BURNER:
        raise ValueError("Unexpected mode", drive.mode)

    # Unlock burner VUC
    drive.vuc_unlock()


def _main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("drive")
    parser.add_argument("firmware")
    args: argparse.Namespace = parser.parse_args()

    drive_path: pathlib.Path = pathlib.Path(args.drive)
    firmware_path: pathlib.Path = pathlib.Path(args.firmware)

    firmware_data: bytes = firmware_path.read_bytes()
    firmware: s11_firmware.Firmware = s11_firmware.Firmware.from_bytes(
        firmware_data,
    )

    if not firmware.burner_code:
        raise ValueError("Firmware has no burner code")

    print("Loading burner:", firmware.burner_code)

    drive: s11_drive.Drive
    with s11_drive.Drive(drive_path) as drive:
        load_burner(drive, firmware.burner_code)
        identify: ata_identify.Identify = drive.cmd_identify_device()

    print(f"Burner Loaded: {identify.model}, {identify.firmware}")


if __name__ == "__main__":
    _main()

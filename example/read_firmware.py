#!/usr/bin/env python

"""Read firmware from drive."""

import argparse
import datetime
import pathlib

from phison_s11 import drive as s11_drive
from phison_s11 import firmware as s11_firmware
from phison_s11 import flash as s11_flash

_INSTRUCTION_RAM_ADDRESS: int = 0x5C0C8000


def read_firmware(drive: s11_drive.Drive) -> s11_firmware.Firmware:
    """Read installed firmware from drive.

    Returns:
        Firmware.

    """
    # Seed for normal code
    seed: s11_firmware.Seed = s11_firmware.Seed()

    # Send seed so VUC verify flash output uses its key for encryption
    drive.vuc_send_seed(seed)

    # Read firmware data from flash
    flash_header: s11_flash.FirmwareHeader
    sections_data: tuple[bytes, ...]
    flash_header, sections_data = drive.vuc_verify_flash()

    # Read drive system info
    system_info: s11_drive.SystemInfo = drive.vuc_system_info()

    # Copy section info from to seed
    seed.sections = flash_header.sections

    # If instruction RAM load enabled, map the source address to where it ends up
    if (
        flash_header.normal_sections_load_iram
        and flash_header.normal_sections_load_iram_size
    ):
        for section in (
            x
            for x in seed.sections
            if x and x.normal_address == flash_header.normal_sections_load_iram_address
        ):
            section.normal_address = _INSTRUCTION_RAM_ADDRESS

    # Construct normal code section as in a firmware file
    normal_code_data: bytes = bytes(seed) + b"".join(map(bytes, sections_data))
    # Parse this new normal code section
    normal_code: s11_firmware.NormalCode = s11_firmware.NormalCode.from_bytes(
        normal_code_data,
    )

    # Create final firmware
    version: s11_firmware.Version = system_info.firmware_version
    date: datetime.datetime = datetime.datetime.combine(
        system_info.firmware_date,
        datetime.time(),
    )

    return s11_firmware.Firmware(
        version=version,
        date=date,
        normal_code=normal_code,
    )


def _main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("drive")
    parser.add_argument("output")
    args: argparse.Namespace = parser.parse_args()
    drive_path: pathlib.Path = pathlib.Path(args.drive)
    output_path: pathlib.Path = pathlib.Path(args.output)

    drive: s11_drive.Drive
    with s11_drive.Drive(drive_path) as drive:
        firmware: s11_firmware.Firmware = read_firmware(drive)

        print("Firmware:", firmware)
        output_path.write_bytes(bytes(firmware))
        print("Saved to:", output_path)


if __name__ == "__main__":
    _main()

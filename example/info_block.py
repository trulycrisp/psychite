#!/usr/bin/env python

"""Read and write drive info block."""

import argparse
import dataclasses
import json
import pathlib

from phison_s11 import drive as s11_drive
from phison_s11 import info_block as s11_info_block

_ACTION_READ: str = "read"
_ACTION_WRITE: str = "write"
_ARG_DRIVE: str = "drive"
_ARG_FILE: str = "file"


@dataclasses.dataclass
class InfoBlockFields:
    """Drive info block fields.

    Attributes:
        serial: Serial number.
        model: Model name.
        firmware: Firmware version string.
        firmware_enable: Enable preceding field firmware.

    """

    serial: str
    model: str
    firmware: str | None
    firmware_enable: bool


def _infoblock_read(drive_path: pathlib.Path, file_path: pathlib.Path) -> None:
    drive: s11_drive.Drive
    with s11_drive.Drive(drive_path) as drive:
        info_block: s11_info_block.InfoBlock = drive.vuc_read_info_block()

    fields: InfoBlockFields = InfoBlockFields(
        serial=info_block.serial,
        model=info_block.model,
        firmware=info_block.firmware,
        firmware_enable=info_block.firmware_enable,
    )

    file_path.write_text(json.dumps(dataclasses.asdict(fields)))
    print("Read", fields)


def _infoblock_write(file_path: pathlib.Path, drive_path: pathlib.Path) -> None:
    fields: InfoBlockFields = InfoBlockFields(**json.loads(file_path.read_text()))

    drive: s11_drive.Drive
    with s11_drive.Drive(drive_path) as drive:
        info_block: s11_info_block.InfoBlock = drive.vuc_read_info_block()

    info_block.serial = fields.serial
    info_block.model = fields.model
    info_block.firmware = fields.firmware
    info_block.firmware_enable = fields.firmware_enable

    with s11_drive.Drive(drive_path) as drive:
        drive.vuc_write_info_block(info_block)

    print("Wrote", fields)


def _main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers: argparse.Action = parser.add_subparsers(dest="action", required=True)

    read_parse: argparse.ArgumentParser = subparsers.add_parser(_ACTION_READ)
    read_parse.add_argument(_ARG_DRIVE)
    read_parse.add_argument(_ARG_FILE)

    write_parse: argparse.ArgumentParser = subparsers.add_parser(_ACTION_WRITE)
    write_parse.add_argument(_ARG_FILE)
    write_parse.add_argument(_ARG_DRIVE)

    args: argparse.Namespace = parser.parse_args()
    drive_path: pathlib.Path = pathlib.Path(args.drive)
    file_path: pathlib.Path = pathlib.Path(args.file)

    match args.action:
        case x if x == _ACTION_READ:
            _infoblock_read(drive_path, file_path)
        case x if x == _ACTION_WRITE:
            _infoblock_write(file_path, drive_path)
        case x:
            raise ValueError("Invalid action", x)


if __name__ == "__main__":
    _main()

#!/usr/bin/env python

"""Tool to pack/unpack firmware."""

import argparse
import dataclasses
import datetime
import json
import pathlib
import shutil

from phison_s11 import firmware as s11_firmware

_ACTION_INFO: str = "info"
_ACTION_PACK: str = "pack"
_ACTION_UNPACK: str = "unpack"
_ARG_FIRMWARE: str = "firmware"
_ARG_DIRECTORY: str = "directory"
_INFO_FILE_NAME: str = "info.json"


@dataclasses.dataclass
class Info:
    """Firmware info.

    Attributes:
        version: Version.
        date: Date.
        firmware_type: Type.
        xor_0561: Uses XOR-0561.
        has_signature: Has cryptographic signature.

    """

    version: str
    date: str | None
    firmware_type: int
    xor_0561: bool
    has_signature: bool


def firmware_info(firmware_path: pathlib.Path) -> None:
    """Firmware information.

    Args:
        firmware_path: Firmware file.

    """
    firmware_data: bytes = firmware_path.read_bytes()
    firmware: s11_firmware.Firmware = s11_firmware.Firmware.from_bytes(
        firmware_data,
    )

    print(firmware)


def firmware_pack(directory_path: pathlib.Path, firmware_path: pathlib.Path) -> None:
    """Pack firmware.

    Args:
        directory_path: Unpacked directory.
        firmware_path: Firmware file.

    """
    info_path: pathlib.Path = directory_path / _INFO_FILE_NAME
    info: Info = Info(**json.loads(info_path.read_text()))

    version: s11_firmware.Version = s11_firmware.Version.from_string(
        info.version,
    )

    date: datetime.datetime | None = (
        datetime.datetime.fromisoformat(info.date) if info.date else None
    )

    firmware_type: s11_firmware.FirmwareType = s11_firmware.FirmwareType(
        info.firmware_type,
    )

    sections: list[s11_firmware.NormalCodeSection | None] = []
    for section_index in range(s11_firmware.SECTION_COUNT):
        section: s11_firmware.NormalCodeSection | None
        section_file_prefix: str = f"{section_index}_"

        try:
            section_path: pathlib.Path = next(
                directory_path.glob(f"{section_file_prefix}*.bin"),
            )
        except StopIteration:
            section = None
        else:
            normal_address: int = int(
                section_path.stem.removeprefix(section_file_prefix),
                0x10,
            )

            section_code: bytes = section_path.read_bytes()

            section = s11_firmware.NormalCodeSection(
                burner_address=0,
                normal_address=normal_address,
                code=section_code,
            )

        sections.append(section)

    normal_code: s11_firmware.NormalCode = s11_firmware.NormalCode(
        sections=tuple(sections),
        xor_0561=info.xor_0561,
    )

    firmware: s11_firmware.Firmware = s11_firmware.Firmware(
        version=version,
        date=date,
        firmware_type=firmware_type,
        has_signature=info.has_signature,
        normal_code=normal_code,
    )

    firmware_path.write_bytes(bytes(firmware))
    print("Firmware:", firmware)
    print("Packed to:", firmware_path)


def firmware_unpack(firmware_path: pathlib.Path, directory_path: pathlib.Path) -> None:
    """Unpack firmware.

    Args:
        firmware_path: Firmware file.
        directory_path: Unpack directory.

    """
    firmware_data: bytes = firmware_path.read_bytes()

    firmware: s11_firmware.Firmware = s11_firmware.Firmware.from_bytes(
        firmware_data,
    )

    if not firmware.normal_code:
        raise ValueError("No normal code to unpack")

    info: Info = Info(
        version=str(firmware.version),
        date=firmware.date.isoformat() if firmware.date else None,
        firmware_type=int(firmware.firmware_type),
        xor_0561=firmware.normal_code.xor_0561,
        has_signature=firmware.has_signature,
    )

    if directory_path.exists():
        shutil.rmtree(directory_path)
    directory_path.mkdir(exist_ok=True)

    info_path: pathlib.Path = directory_path / _INFO_FILE_NAME
    info_path.write_text(json.dumps(dataclasses.asdict(info)))

    for index, section in enumerate(firmware.normal_code.sections):
        if not section:
            continue

        section_path: pathlib.Path = (
            directory_path / f"{index}_{section.normal_address:08x}.bin"
        )
        section_path.write_bytes(bytes(section))

    print("Firmware:", firmware)
    print("Unpacked to:", directory_path)


def _main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers: argparse.Action = parser.add_subparsers(dest="action", required=True)

    info_parse: argparse.ArgumentParser = subparsers.add_parser(_ACTION_INFO)
    info_parse.add_argument(_ARG_FIRMWARE)

    pack_parse: argparse.ArgumentParser = subparsers.add_parser(_ACTION_PACK)
    pack_parse.add_argument(_ARG_DIRECTORY)
    pack_parse.add_argument(_ARG_FIRMWARE)

    unpack_parse: argparse.ArgumentParser = subparsers.add_parser(_ACTION_UNPACK)
    unpack_parse.add_argument(_ARG_FIRMWARE)
    unpack_parse.add_argument(_ARG_DIRECTORY)

    args: argparse.Namespace = parser.parse_args()
    firmware_path: pathlib.Path = pathlib.Path(args.firmware)

    match args.action:
        case x if x == _ACTION_INFO:
            firmware_info(firmware_path)
        case x if x == _ACTION_PACK:
            firmware_pack(pathlib.Path(args.directory), firmware_path)
        case x if x == _ACTION_UNPACK:
            firmware_unpack(firmware_path, pathlib.Path(args.directory))
        case x:
            raise ValueError("Invalid action", x)


if __name__ == "__main__":
    _main()

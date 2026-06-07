#!/usr/bin/env python

"""Dump drive System Area (SA)."""

import argparse
import pathlib
import shutil

from phison_s11 import drive as s11_drive
from phison_s11 import system_info as s11_system_info

_FIRST_CHANNEL: int = 0
_FIRST_CHANNEL_FIRST_CE: int = 0


def _dump_block(
    drive: s11_drive.Drive,
    system_info: s11_system_info.SystemInfo,
    die: int,
    block: int,
    page_count: int,
    output_path: pathlib.Path,
) -> None:
    print(f"Dumping CE: {_FIRST_CHANNEL_FIRST_CE}, die: {die}, block: {block}")

    for page in range(page_count):
        data: bytes
        magic: int
        data, magic = drive.vuc_read_flash(
            _FIRST_CHANNEL_FIRST_CE,
            die,
            block,
            page,
            True,
            system_info,
        )

        if not magic:
            continue

        out_name: str = f"{page}_{magic:x}.bin"
        page_path: pathlib.Path = output_path / str(die) / str(block) / out_name
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_bytes(data)


def _main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("drive")
    parser.add_argument("output")
    args: argparse.Namespace = parser.parse_args()
    drive_path: pathlib.Path = pathlib.Path(args.drive)
    output_path: pathlib.Path = pathlib.Path(args.output)

    if output_path.exists():
        shutil.rmtree(output_path)

    with s11_drive.Drive(drive_path) as drive:
        system_info: s11_system_info.SystemInfo = drive.vuc_system_info()

        block_map: tuple[tuple[tuple[s11_drive.BlockType, int] | None, ...], ...] = (
            drive.vuc_block_map(_FIRST_CHANNEL)
        )

        die_map: tuple[tuple[s11_drive.BlockType, int] | None, ...]
        for die, die_map in enumerate(block_map):
            for block, map_entry in enumerate(die_map):
                if not map_entry:
                    continue

                block_type: s11_drive.BlockType
                page_count: int
                block_type, page_count = map_entry

                if block_type != s11_drive.BlockType.SYSTEM:
                    continue

                _dump_block(drive, system_info, die, block, page_count, output_path)

    print("Dumped to:", output_path)


if __name__ == "__main__":
    _main()

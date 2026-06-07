"""S11 common data structures and types."""

import enum
from typing import ClassVar, Self

_BOOL_MAP: dict[int, bool] = {0: False, 0x33: True}


def bool_pack(value: bool) -> int:
    """Pack custom boolean format used in data.

    Args:
        value: Value to pack.

    Returns:
        Packed integer.

    """
    return next(k for k, v in _BOOL_MAP.items() if v == value)


def bool_unpack(value: int) -> bool:
    """Unpack custom boolean format used in data.

    Args:
        value: Value to unpack.

    Returns:
        Unpacked boolean.

    """
    try:
        return _BOOL_MAP[value]
    except KeyError as e:
        raise ValueError("Invalid boolean value", value) from e


class FlashInterface(enum.IntEnum):
    """NAND flash interface type.

    Attributes:
        SDR: Async SDR.
        TOGGLE_1: Toggle DDR 1.0.
        TOGGLE_2: Toggle DDR 2.0.
        NV_DDR: NV-DDR.
        NV_DDR_2: NV-DDR2.
        NV_DDR_3: NV-DDR3.

    """

    _NONE_VALUES: ClassVar[tuple[int, ...]] = enum.nonmember((0, 0xFF))

    SDR = 1
    TOGGLE_1 = 2
    TOGGLE_2 = 3
    NV_DDR = 4
    NV_DDR_2 = 5
    NV_DDR_3 = 8

    @classmethod
    def parse(cls, value: int) -> Self | None:
        """Parse flash interface.

        Args:
            value: Raw value.

        Returns:
            Parsed flash interface.

        """
        if value in cls._NONE_VALUES:
            return None

        return cls(value)

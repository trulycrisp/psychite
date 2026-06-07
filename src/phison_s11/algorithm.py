"""Phison S11 algorithms."""

import struct
from importlib import resources

_BYTE_BITS: int = 8
_U16_SIZE: int = 2
_U16_BITS: int = _U16_SIZE * _BYTE_BITS
_U16_MASK: int = (1 << _U16_BITS) - 1
_U32_SIZE: int = 4
_U32_BITS: int = _U32_SIZE * _BYTE_BITS
_U32_MASK: int = (1 << _U32_BITS) - 1

_CIPHER_XOR_0561_DATA: bytes = (
    resources.files(__package__).joinpath("xor_0561_data.bin").read_bytes()
)

_CRC16_POLYNOMIAL: int = 0x8005
_CIPHER_CRC16_BLOCK_STRUCT: struct.Struct = struct.Struct("<16H")
_CIPHER_CRC16_BLOCKS_PER_CHUNK: int = 16
_CIPHER_CRC16_CHUNK_SIZE: int = (
    _CIPHER_CRC16_BLOCKS_PER_CHUNK * _CIPHER_CRC16_BLOCK_STRUCT.size
)
_CIPHER_CRC16_INITIAL_STATE: int = 0x1234

_CRC32_POLYNOMIAL: int = 0x04C11DB7


def _xor_data(data1: bytes | bytearray, data2: bytes | bytearray) -> bytes:
    data1_size: int = len(data1)
    data2_size: int = len(data2)

    if data1_size != data2_size:
        raise ValueError("length mismatch", data1_size, data2_size)

    data1_value: int = int.from_bytes(data1, "little")
    data2_value: int = int.from_bytes(data2, "little")
    return (data1_value ^ data2_value).to_bytes(data1_size, "little")


def cipher_xor_0561(data: bytes | bytearray) -> bytes:
    """Encrypt/decrypt with XOR-0561 algorithm.

    Symmetric data scrambling algorithm used for flash storage, different variants used
    by many Phison flash controllers.

    Args:
        data: Input (ciphertext or plaintext).

    Returns:
        Output (ciphertext or plaintext).

    """
    chunk: bytes = _CIPHER_XOR_0561_DATA
    keystream: bytes = (
        chunk * (len(data) // len(chunk)) + chunk[: len(data) % len(chunk)]
    )

    return _xor_data(data, keystream)


def _crc_advance(
    state: int,
    width: int,
    polynomial: int,
    steps: int,
) -> int:
    mask: int = (1 << width) - 1
    high_bit: int = 1 << (width - 1)

    for _ in range(steps):
        feedback: bool = bool(state & high_bit)
        state = (state << 1) & mask

        if feedback:
            state ^= polynomial

    return state


def _crc_advance_table(
    index_bits: int,
    register_bits: int,
    polynomial: int,
) -> list[int]:
    shift: int = register_bits - index_bits
    table: list[int] = [0] * (1 << index_bits)

    for bit_index in range(index_bits):
        bit_value: int = 1 << bit_index
        table[bit_value] = _crc_advance(
            bit_value << shift,
            register_bits,
            polynomial,
            steps=index_bits,
        )

        for previous in range(1, bit_value):
            table[bit_value | previous] = table[bit_value] ^ table[previous]

    return table


def _cipher_crc16_keystream(size: int, seed: int, offset: int) -> bytes:
    # CRC-16 advance lookup table
    advance_table: list[int] = _crc_advance_table(
        _U16_BITS,
        _U16_BITS,
        _CRC16_POLYNOMIAL,
    )

    # 16-bit integer bit reversal lookup table
    u16_reverse_table: list[int] = [
        int(f"{i:016b}"[::-1], 2) for i in range(1 << _U16_BITS)
    ]

    output: bytearray = bytearray()
    chunk_start: int = offset // _CIPHER_CRC16_CHUNK_SIZE
    chunk_end: int = -((offset + size) // -_CIPHER_CRC16_CHUNK_SIZE)
    chunk_skip: int = offset % _CIPHER_CRC16_CHUNK_SIZE

    for chunk in range(chunk_start, chunk_end):
        chunk_seed: int = (seed + chunk) & _U32_MASK
        state: int = advance_table[
            _CIPHER_CRC16_INITIAL_STATE ^ u16_reverse_table[chunk_seed & _U16_MASK]
        ]
        state = advance_table[state ^ u16_reverse_table[chunk_seed >> _U16_BITS]]

        for _ in range(_CIPHER_CRC16_BLOCKS_PER_CHUNK):
            reversed_state: int = u16_reverse_table[state]
            not_state: int = state ^ _U16_MASK
            not_reversed_state: int = reversed_state ^ _U16_MASK

            pattern: tuple[int, ...] = (
                ((state << 4) & 0xFF00) | ((state >> 2) & 0xFF),
                ((not_reversed_state << 10) & 0xF000) | ((state >> 3) & 0xFFF),
                ((reversed_state << 4) & 0xFFF0) | ((not_state >> 8) & 0xF),
                ((state << 3) & 0xFFF0) | ((reversed_state >> 2) & 0xF),
                reversed_state,
                ((not_state << 8) | (state >> 8)) & _U16_MASK,
                ((reversed_state << 4) & 0xF000) | (not_state & 0xFFF),
                state,
                ((reversed_state << 1) & 0xFFF0) | ((state >> 11) & 0xF),
                not_reversed_state,
                ((state << 8) | (state >> 8)) & _U16_MASK,
                ((reversed_state << 8) | (reversed_state >> 8)) & _U16_MASK,
                not_state,
                reversed_state,
                ((state << 2) & 0xFFF0) | ((reversed_state >> 1) & 0xF),
                state,
            )

            output += _CIPHER_CRC16_BLOCK_STRUCT.pack(*pattern)

            for value in pattern:
                state = advance_table[state ^ u16_reverse_table[value]]

    return bytes(output[chunk_skip : chunk_skip + size])


def cipher_crc16(data: bytes | bytearray, seed: int, offset: int = 0) -> bytes:
    """CRC-16 based cipher.

    Symmetric cipher based on CRC-16. Controller implements it in hardware, Phison tools
    seemingly refer to it as 'CPU RandSetValue DMAC'.

    Args:
        data: Input (ciphertext or plaintext).
        seed: Seed value used as key.
        offset: Keystream offset.

    Returns:
        Output (ciphertext or plaintext).

    """
    return _xor_data(data, _cipher_crc16_keystream(len(data), seed, offset))


def checksum_crc32(data: bytes | bytearray, seed: int) -> int:
    """CRC32-based checksum algorithm.

    Custom checksum algorithm based on CRC-32, Phison tools refer to it just as 'CRC'.

    Args:
        data: Data, size must be 4-byte aligned.
        seed: Seed value.

    Returns:
        Checksum value.

    """
    if len(data) % _U32_SIZE != 0:
        raise ValueError("Data size must be 4-byte aligned", len(data))

    # Build CRC-32 advance lookup table
    advance_table: list[int] = _crc_advance_table(
        _U16_BITS,
        _U32_BITS,
        _CRC32_POLYNOMIAL,
    )

    state: int = seed
    for offset in range(0, len(data), _U32_SIZE):
        state ^= int.from_bytes(data[offset : offset + _U32_SIZE], "little")
        state = ((state << _U16_BITS) & _U32_MASK) ^ advance_table[state >> _U16_BITS]
        state = ((state << _U16_BITS) & _U32_MASK) ^ advance_table[state >> _U16_BITS]

    return state

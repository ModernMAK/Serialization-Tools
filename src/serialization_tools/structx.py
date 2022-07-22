from __future__ import annotations

import re
import struct

try:
    from ctypes import _CData
except ImportError:
    pass
from pickle import PickleBuffer
from struct import calcsize, unpack, pack
from array import array
from mmap import mmap
from typing import Union, BinaryIO, Tuple, Any, Iterator, List

_StructFormat = Union[str, bytes]
WriteableBuffer = Union[bytearray, memoryview, array[Any], mmap, _CData, PickleBuffer]
ReadableBuffer = Union[bytes, WriteableBuffer]

_Byte = struct.Struct("c")
_UInt32 = struct.Struct("I")


def unpack_stream(__format: _StructFormat, __stream: BinaryIO) -> Tuple[Any, ...]:
    size = calcsize(__format)
    buffer = __stream.read(size)
    return unpack(__format, buffer)


def iter_unpack_stream(
    __format: _StructFormat, __stream: BinaryIO
) -> Iterator[Tuple[Any, ...]]:
    size = calcsize(__format)
    while True:
        buffer = __stream.read(size)
        if len(buffer) == 0:  # End of Stream; job's done
            break
        elif len(buffer) != size:  # End of Stream BUT can't unpack, raise an error
            raise NotImplementedError  # TODO
        else:
            yield unpack(__format, buffer)


def pack_stream(fmt: _StructFormat, __stream: BinaryIO, *v: Any) -> int:
    buffer = pack(fmt, *v)
    return __stream.write(buffer)


def unpack_len_encoded_bytes(
    buffer: ReadableBuffer,
    length_layout: _StructFormat = _UInt32.format,
    data_layout: _StructFormat = _Byte.format,
) -> bytes:
    data_size: int = struct.calcsize(data_layout)
    length_size: int = struct.calcsize(length_layout)
    count: int = struct.unpack_from(length_layout, buffer)[0]
    result: bytes = struct.unpack_from(f"{count * data_size}s", buffer, length_size)[0]
    return result


def pack_len_encoded_bytes(
    value: bytes, length_layout: _StructFormat = _UInt32.format
) -> bytes:
    count: int = len(value)
    len_buffer = struct.pack(length_layout, count)
    return len_buffer + value


def unpack_len_encoded(
    buffer: ReadableBuffer,
    length_layout: _StructFormat = _UInt32.format,
    data_layout: _StructFormat = _Byte.format,
) -> Tuple[Tuple[Any, ...], ...]:
    len_size = struct.calcsize(length_layout)
    data_size = struct.calcsize(data_layout)

    count: int = struct.unpack(length_layout, buffer)[0]
    items = [
        struct.unpack_from(data_layout, buffer, len_size + data_size * i)
        for i in range(count)
    ]
    return tuple(items)


def pack_len_encoded(
    value: List[Any],
    data_layout: _StructFormat,
    length_layout: _StructFormat = _UInt32.format,
) -> bytes:
    count: int = len(value)
    buffer = bytearray(struct.pack(length_layout, count))
    for item in value:
        buffer.extend(struct.pack(data_layout, item))
    return buffer


def unpack_len_encoded_str(
    buffer: ReadableBuffer,
    length_layout: _StructFormat = _UInt32.format,
    encoding: str = "ascii",
) -> str:
    buffer = unpack_len_encoded_bytes(buffer, length_layout)
    return buffer.decode(encoding)


def pack_len_encoded_str(
    value: str, length_layout: _StructFormat = _UInt32.format, encoding: str = "ascii"
) -> bytes:
    buffer = value.encode(encoding)
    len_buffer = struct.pack(length_layout, len(buffer))
    return len_buffer + buffer


_STRUCT_CHARS = r"cbB?hHiIlLqQnNefdpPs"
struct_re = re.compile(
    rf"(?:([0-9]*)([{_STRUCT_CHARS}]))"
)  # 'x' is excluded because it is padding


def count_args(fmt: str) -> int:
    count = 0
    pos = 0
    while pos < len(fmt):
        match = struct_re.search(fmt, pos)
        if match is None:
            break
        else:
            repeat = match.group(1)
            code = match.group(2)
            if code == "s":
                count += 1
            else:
                count += int(repeat) if repeat else 1
            pos = match.span()[1]
    return count


class Struct(struct.Struct):
    def __init__(self, format: str):
        super().__init__(format)
        self.args = count_args(format)

    def unpack_stream(self, __stream: BinaryIO) -> Tuple[Any, ...]:
        buffer = __stream.read(self.size)
        return self.unpack(buffer)

    def iter_unpack_stream(self, __stream: BinaryIO) -> Iterator[Tuple[Any, ...]]:
        while True:
            buffer = __stream.read(self.size)
            if len(buffer) == 0:  # End of Stream; job's done
                break
            elif (
                len(buffer) != self.size
            ):  # End of Stream BUT can't unpack, raise an error
                raise NotImplementedError  # TODO
            else:
                yield self.unpack(buffer)

    def pack_stream(self, __stream: BinaryIO, *v: Any) -> int:
        buffer = self.pack(*v)
        return __stream.write(buffer)

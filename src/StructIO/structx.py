from __future__ import annotations

import struct
from array import array
from mmap import mmap
from struct import *
from typing import Union, BinaryIO, Tuple, Any, Iterator, List

from StructIO.structio import Byte, UInt32

_StructFormat = Union[str, bytes]
_BufferFormat = Union[bytes, bytearray, memoryview, array, mmap]


# _StructAble = Union[Struct, str, bytes]


def unpack_stream(__format: _StructFormat, __stream: BinaryIO) -> Tuple[Any, ...]:
    size = calcsize(__format)
    buffer = __stream.read(size)
    return unpack(__format, buffer)


def iter_unpack_stream(__format: _StructFormat, __stream: BinaryIO) -> Iterator[Tuple[Any, ...]]:
    size = calcsize(__format)
    while True:
        buffer = __stream.read(size)
        if len(buffer) == 0:  # End of Stream; job's done
            break
        elif len(buffer) != size:  # End of Stream BUT can't unpack, raise an error
            raise NotImplementedError  # TODO
        else:
            yield unpack(__format, buffer)


def pack_stream(fmt: _StructFormat, __stream: BinaryIO, *v) -> int:
    buffer = pack(fmt, *v)
    return __stream.write(buffer)


def unpack_len_encoded_bytes(buffer: _BufferFormat, length_layout: _StructFormat = UInt32, data_layout: _StructFormat = Byte) -> bytes:
    len_size = struct.calcsize(length_layout)
    data_size = struct.calcsize(data_layout)
    count: int = struct.unpack(length_layout, buffer)[0]
    return struct.unpack_from(f"{count * data_size}s", buffer, len_size)[0]


def pack_len_encoded_bytes(value: bytes, length_layout: _StructFormat = UInt32) -> bytes:
    count: int = len(value)
    len_buffer = struct.pack(length_layout, count)
    return len_buffer + value


def unpack_len_encoded(buffer: _BufferFormat, length_layout: _StructFormat = UInt32, data_layout: _StructFormat = Byte) -> Tuple[Tuple[Any, ...], ...]:
    len_size = struct.calcsize(length_layout)
    data_size = struct.calcsize(data_layout)

    count: int = struct.unpack(length_layout, buffer)[0]
    items = [struct.unpack_from(data_layout, buffer, len_size + data_size * i) for i in range(count)]
    return tuple(items)


def pack_len_encoded(self, value: List, data_layout: _StructFormat, length_layout: _StructFormat = UInt32) -> bytes:
    count: int = len(value)
    buffer = bytearray(struct.pack(length_layout, count))
    for item in value:
        buffer.extend(self.pack(data_layout, item))
    return buffer


def unpack_len_encoded_str(buffer: _BufferFormat, length_layout: _StructFormat = UInt32, encoding: str = None) -> str:
    buffer = unpack_len_encoded_bytes(buffer, length_layout)
    return buffer.decode(encoding)


def pack_len_encoded_str(value: str, length_layout: _StructFormat = UInt32, encoding: str = None) -> bytes:
    buffer = value.encode(encoding)
    len_buffer = struct.pack(length_layout, len(buffer))
    return len_buffer + buffer


class Struct(struct.Struct):
    def unpack_stream(self, __stream: BinaryIO) -> Tuple[Any, ...]:
        buffer = __stream.read(self.size)
        return self.unpack(buffer)

    def iter_unpack_stream(self, __stream: BinaryIO) -> Iterator[Tuple[Any, ...]]:
        while True:
            buffer = __stream.read(self.size)
            if len(buffer) == 0:  # End of Stream; job's done
                break
            elif len(buffer) != self.size:  # End of Stream BUT can't unpack, raise an error
                raise NotImplementedError  # TODO
            else:
                yield self.unpack(buffer)

    def pack_stream(self, __stream: BinaryIO, *v) -> int:
        buffer = self.pack(*v)
        return __stream.write(buffer)

#
# class BinaryIO(typing.BinaryIO):
#     def __init__(self, stream: typing.BinaryIO):
#         self._stream = stream
#
#     def close(self) -> None:
#         self._stream.close()
#
#     def fileno(self) -> int:
#         return self._stream.fileno()
#
#     def flush(self) -> None:
#         self._stream.flush()
#
#     def isatty(self) -> bool:
#         return self._stream.isatty()
#
#     def read(self, n: int = ...) -> AnyStr:
#         return self._stream.read(n)
#
#     def readable(self) -> bool:
#         return self._stream.readable()
#
#     def readline(self, limit: int = ...) -> AnyStr:
#         return self._stream.readline(limit)
#
#     def readlines(self, hint: int = ...) -> list[AnyStr]:
#         return self._stream.readlines(hint)
#
#     def seek(self, offset: int, whence: int = ...) -> int:
#         return self.seek(offset, whence)
#
#     def seekable(self) -> bool:
#         return self._stream.seekable()
#
#     def tell(self) -> int:
#         return self._stream.tell()
#
#     def truncate(self, size: int | None = ...) -> int:
#         return self._stream.truncate(size)
#
#     def writable(self) -> bool:
#         return self._stream.writable()
#
#     def write(self, s: AnyStr) -> int:
#         return self._stream.write(s)
#
#     def writelines(self, lines: Iterable[AnyStr]) -> None:
#         return self._stream.writelines(lines)
#
#     def __next__(self) -> AnyStr:
#         return self._stream.__next__()
#
#     def __iter__(self) -> Iterator[AnyStr]:
#         return self._stream.__iter__()
#
#     def __exit__(self, t: Type[BaseException] | None, value: BaseException | None, traceback: TracebackType | None) -> bool | None:
#         return self._stream.__exit__(t, value, traceback)
#
#     def __enter__(self) -> BinaryIO:
#         return self._stream.__enter__()
#
#     @contextmanager
#     def bookmark(self):
#         now = self.tell()
#         yield
#         self.seek(now)

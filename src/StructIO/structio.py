# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from array import array
from contextlib import contextmanager
from mmap import mmap
from types import TracebackType
from typing import BinaryIO, Tuple, Any, List, Union, Optional, Type, Iterator, AnyStr, Iterable

from .structx import Struct

StructAble = Union[Struct, str, bytes]
UInt8 = Struct("B")
UInt16 = Struct("H")
UInt32 = Struct("I")
Int32 = Struct("i")
UInt64 = Struct("Q")
Int64 = Struct("q")
Byte = Struct("c")

StructFormat = Union[str, bytes]
BufferFormat = Union[bytes, bytearray, memoryview, array, mmap]


def as_hex_adr(value: int) -> str:
    return "0x" + value.to_bytes(4, "big").hex()


def has_data(stream: BinaryIO) -> bool:
    now = stream.tell()
    b = stream.read(1)
    stream.seek(now)
    return len(b) != 0


def end_of_stream(stream: BinaryIO) -> bool:
    now = stream.tell()
    stream.seek(0, 2)
    then = stream.tell()
    stream.seek(now)
    return now == then


class StructIO:
    str_null_terminated_default = False
    _struct_cache = {}

    def __init__(self, stream: BinaryIO, str_null_terminated: bool = None):
        self.stream = stream
        self._str_null_terminated = str_null_terminated or self.str_null_terminated_default

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def EOS(self) -> bool:
        with self.bookmark():
            return len(self.read(1)) == 0

    def read(self, n: int = ...) -> bytes:
        return self.stream.read(n)

    def write(self, value: bytes) -> int:
        return self.stream.write(value)

    def seek(self, offset: int, whence: int = None) -> int:
        return self.stream.seek(offset, whence) if whence else self.stream.seek(offset)

    def tell(self) -> int:
        return self.stream.tell()

    @contextmanager
    def bookmark(self):
        pos = self.stream.tell()
        yield
        self.stream.seek(pos)

    def unpack(self, layout: StructAble) -> Any:
        layout = self._parse_struct(layout)
        buffer = self.stream.read(layout.size)
        result = layout.unpack(buffer)
        if isinstance(result, tuple) and len(result) == 1:
            return result[0]
        else:
            return result

    def pack(self, layout: StructAble, data: Any) -> int:
        layout = self._parse_struct(layout)
        buffer = layout.pack(data)
        return self.stream.write(buffer)

    def unpack_len_encoded_bytes(self, length_layout: StructAble = UInt32, data_layout: StructAble = Byte) -> bytes:
        length_layout = self._parse_struct(length_layout)
        data_layout = self._parse_struct(data_layout)

        count: int = self.unpack(length_layout)
        return self.read(count * data_layout.size)

    def unpack_len_encoded(self, length_layout: StructAble = UInt32, data_layout: StructAble = Byte) -> Tuple:
        length_layout = self._parse_struct(length_layout)
        data_layout = self._parse_struct(data_layout)

        count: int = self.unpack(length_layout)
        items = [self.unpack(data_layout) for _ in range(count)]
        return tuple(items)

    def pack_len_encoded_bytes(self, value: bytes, length_layout: StructAble = UInt32) -> int:
        length_layout = self._parse_struct(length_layout)

        count: int = len(value)
        written = self.pack(length_layout, count)
        written += self.write(value)
        return written

    def pack_len_encoded(self, value: List, data_layout: StructAble, length_layout: StructAble = UInt32) -> int:
        length_layout = self._parse_struct(length_layout)
        data_layout = self._parse_struct(data_layout)

        count: int = len(value)
        written = self.pack(length_layout, count)
        for item in value:
            written += self.pack(data_layout, item)
        return written

    def unpack_len_encoded_str(self, length_layout: StructAble = UInt32, encoding: str = None, errors: str = None, null_terminated: bool = None) -> str:
        null_terminated = null_terminated or self._str_null_terminated
        length_layout = self._parse_struct(length_layout)
        count: int = self.unpack(length_layout)
        bm = self.tell()
        buffer: bytes = self.read(count)
        try:
            decoded = self._decode(buffer, encoding, errors)
            if null_terminated:
                if len(decoded) > 0 and decoded[-1] != "\0":
                    raise ValueError(f"Expected null terminated string; null-charachter was not found! '{decoded}'")
                else:
                    decoded = decoded[:-1]
            return decoded
        except UnicodeDecodeError:
            raise ValueError(bm, "0x" + bm.to_bytes(4, "big").hex())

    def pack_len_encoded_str(self, value: str, length_layout: StructAble = UInt32, encoding: str = None, errors: str = None, null_terminated: bool = None) -> int:
        null_terminated = null_terminated or self._str_null_terminated

        if null_terminated and (len(value) > 0 and value[-1] != "\0"):
            value += "\0"

        length_layout = self._parse_struct(length_layout)
        buffer = self._encode(value, encoding, errors)
        count: int = len(buffer)
        written = self.pack(length_layout, count)
        written += self.write(buffer)
        return written

    @classmethod
    def _encode(cls, value: str, encoding: str = None, errors: str = None) -> bytes:
        if not encoding:
            return value.encode(errors=errors) if errors else value.encode()
        else:
            return value.encode(encoding=encoding, errors=errors) if errors else value.encode(encoding=encoding)

    @classmethod
    def _decode(cls, value: bytes, encoding: str = None, errors: str = None) -> str:
        if not encoding:
            return value.decode(errors=errors) if errors else value.decode()
        else:
            return value.decode(encoding=encoding, errors=errors) if errors else value.decode(encoding=encoding)

    @classmethod
    def _parse_struct(cls, layout: StructAble) -> Struct:
        if isinstance(layout, Struct):
            return layout
        elif layout in cls._struct_cache:
            return cls._struct_cache[layout]
        else:
            result = cls._struct_cache[layout] = Struct(layout)
            return result


class StreamPtr:
    def __init__(self, stream: BinaryIO, offset: int = None, whence: int = 0):
        self.stream = stream
        self.offset = offset or stream.tell()
        self.whence = whence

    @contextmanager
    def jump_to(self) -> BinaryIO:
        prev = self.stream.tell()
        self.stream.seek(self.offset, self.whence)
        yield self.stream
        self.stream.seek(prev)


class BinaryWindow(BinaryIO):
    @classmethod
    def slice(cls, stream: BinaryIO, size: int):
        now = stream.tell()
        return cls(stream, now, now + size)

    def __init__(self, stream: BinaryIO, start: int, end: int):
        self._stream = stream
        self._start = start
        self._end = end
        assert self._start <= self._end

    @property
    def __remaining_bytes(self) -> int:
        remaining = self._end - self._stream.tell()
        return remaining if remaining >= 0 else 0

    @property
    def __window_size(self) -> int:
        return self._end - self._start

    @property
    def __window_valid(self) -> bool:
        return self._start <= self._stream.tell() <= self._end

    def abs_tell(self) -> int:
        if isinstance(self._stream, BinaryWindow):
            return self._stream.abs_tell()
        else:
            return self._stream.tell()

    def close(self) -> None:
        # DO NOT CLOSE THE STREAM
        pass

    def fileno(self) -> int:
        return self._stream.fileno()

    def flush(self) -> None:
        self._stream.flush()  # TODO this may be a bad thing? look into it

    def isatty(self) -> bool:
        return self.isatty()

    def read(self, n: int = -1) -> AnyStr:
        if n == -1:
            return self._stream.read(self.__remaining_bytes)
        elif self.__remaining_bytes >= n:
            return self._stream.read(n)
        else:
            return self._stream.read(self.__remaining_bytes)

    def readable(self) -> bool:
        return self._stream.readable()

    def readline(self, limit: int = ...) -> AnyStr:
        raise NotImplementedError

    def readlines(self, hint: int = ...) -> list[AnyStr]:
        raise NotImplementedError

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._stream.seek(self._start + offset, 0)
        elif whence == 1:
            self._stream.seek(offset, 1)
        elif whence == 2:
            self._stream.seek(self._end - offset, 0)
        else:
            self._stream.seek(offset, whence)

        if not self.__window_valid:
            raise Exception("Seek made the window invalid!")
        return self.tell()

    def seekable(self) -> bool:
        return self._stream.seekable()

    def tell(self) -> int:
        return self._stream.tell() - self._start

    def truncate(self, size: Optional[int] = ...) -> int:
        raise NotImplementedError

    def writable(self) -> bool:
        return self._stream.writable()

    def write(self, s: AnyStr) -> int:
        n = len(s)
        if self.__remaining_bytes >= n:
            return self._stream.write(s)
        else:
            raise Exception("Write would write outside the size of the BinaryWindow!")

    def writelines(self, lines: Iterable[AnyStr]) -> None:
        raise NotImplementedError

    def __next__(self) -> AnyStr:
        raise NotImplementedError

    def __iter__(self) -> Iterator[AnyStr]:
        raise NotImplementedError

    def __exit__(self, t: Optional[Type[BaseException]], value: Optional[BaseException], traceback: Optional[TracebackType]) -> Optional[bool]:
        pass
        # return self.__stream.__exit__(t, value, traceback) # CANT CALL BASE BECAUSE IT CLOSES STREAM

    def __enter__(self) -> BinaryIO:
        return self


class StreamWindowPtr(StreamPtr):
    def __init__(self, stream: BinaryIO, size: int, offset: int = None, whence: int = 0):
        super().__init__(stream, offset, whence)
        self.size = size

    @contextmanager
    def jump_to(self) -> BinaryIO:
        with super(self).jump_to() as inner:  # We dont have to use inner, but it makes it obvious that the inner stream has correctly jumped
            return BinaryWindow.slice(inner, self.size)

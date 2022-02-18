# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from array import array
from contextlib import contextmanager
from mmap import mmap
from types import TracebackType
from typing import BinaryIO, Union, Optional, Type, Iterator, AnyStr, Iterable

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

    # noinspection SpellCheckingInspection
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

    # noinspection SpellCheckingInspection
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
        return self.tell_abs()

    def tell_abs(self) -> int:
        return self._stream.tell()

    def tell_rel(self) -> int:
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
        # return self.__stream.__exit__(t, value, traceback) # CAN'T CALL BASE BECAUSE IT CLOSES STREAM

    def __enter__(self) -> 'BinaryWindow':
        return self


class StreamWindowPtr(StreamPtr):
    def __init__(self, stream: BinaryIO, size: int, offset: int = None, whence: int = 0):
        super().__init__(stream, offset, whence)
        self.size = size

    @contextmanager
    def jump_to(self) -> BinaryIO:
        with super(self).jump_to() as inner:  # We don't have to use inner, but it makes it obvious that the inner stream has correctly jumped
            return BinaryWindow.slice(inner, self.size)

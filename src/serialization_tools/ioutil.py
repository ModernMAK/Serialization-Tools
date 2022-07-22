from __future__ import annotations
from array import array
from contextlib import contextmanager
from mmap import mmap
from types import TracebackType
from typing import (
    BinaryIO,
    Union,
    Optional,
    Type,
    Iterator,
    AnyStr,
    Iterable,
    Generator,
    Any,
    TypeVar,
)

from .error import ParsingError
from .size import KiB
from .structx import Struct

StructAble = Union[Struct, str, bytes]
StructFormat = Union[str, bytes]
BufferFormat = Union[bytes, bytearray, memoryview, array, mmap]

AnyBinaryIO = TypeVar("AnyBinaryIO", bound=BinaryIO)


@contextmanager
def as_parsing_window(stream: AnyBinaryIO) -> Generator[AnyBinaryIO, None, None]:
    start = abs_tell(stream)
    try:
        yield stream
    except ParsingError as e:
        raise  # Dont wrap a parsing error
    except KeyboardInterrupt as e:
        raise  # Dont wrap a Keyboard Interrupt
    except BaseException as e:
        try:
            now = abs_tell(stream)
        except:
            now = None
            pass
        raise ParsingError(start, now) from e


def as_hex_adr(value: int, size: int = 4) -> str:
    return "0x" + value.to_bytes(size, "big").hex()


def has_data(stream: BinaryIO) -> bool:
    now = stream.tell()
    b = stream.read(1)
    stream.seek(now)
    return len(b) != 0


def end_of_stream(stream: BinaryIO) -> bool:
    if isinstance(stream, BinaryWindow):
        raise Exception(
            "BinaryWindow really breaks this, until tests are done, use has_data"
        )
    now = stream.tell()
    stream.seek(0, 2)
    then = stream.tell()
    stream.seek(now)
    return now == then


def iter_read(stream: BinaryIO, chunk_size: int = 64 * KiB) -> Iterable[bytes]:
    while has_data(stream):
        yield stream.read(chunk_size)


def abs_tell(stream: BinaryIO) -> int:
    if hasattr(stream, "abs_tell"):
        return stream.abs_tell()  # type: ignore # mypy doesn't support hasattr checks
    else:
        return stream.tell()


def stream2hex(stream: BinaryIO, **kwargs: Any) -> str:
    now = abs_tell(stream)
    return as_hex_adr(now, **kwargs)


class Ptr:
    def __init__(self, offset: int, whence: int = 0):
        self.offset = offset
        self.whence = whence

    @contextmanager
    def stream_jump_to(self, stream: BinaryIO) -> Generator[BinaryIO, None, None]:
        prev = stream.tell()
        stream.seek(self.offset, self.whence)
        yield stream
        stream.seek(prev)


class StreamPtr(Ptr):
    def __init__(self, stream: BinaryIO, offset: Optional[int] = None, whence: int = 0):
        super().__init__(offset or stream.tell(), whence)
        self.stream = stream

    @contextmanager
    def jump_to(self) -> Generator[BinaryIO, None, None]:
        with self.stream_jump_to(self.stream) as stream:
            yield stream


class BinaryWindow(BinaryIO):
    @classmethod
    def slice(cls, stream: BinaryIO, size: Optional[int] = None) -> BinaryWindow:
        now = stream.tell()
        if size is not None:
            return cls(stream, now, now + size)
        else:
            end = stream.seek(0, 2)
            stream.seek(now)
            return cls(stream, now, end)

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

    def read(self, n: int = -1) -> bytes:
        if n == -1:
            return self._stream.read(self.__remaining_bytes)
        if self.__remaining_bytes >= n:
            return self._stream.read(n)
        return self._stream.read(self.__remaining_bytes)

    def readable(self) -> bool:
        return self._stream.readable()

    def readline(self, limit: int = ...) -> bytes:
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
        return self._stream.tell() - self._start

    def truncate(self, size: Optional[int] = ...) -> int:
        raise NotImplementedError

    def writable(self) -> bool:
        return self._stream.writable()

    def write(self, s: bytes) -> int:
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

    def __exit__(
        self,
        t: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        return None
        # return self.__stream.__exit__(t, value, traceback) # CAN'T CALL BASE BECAUSE IT CLOSES STREAM

    def __enter__(self) -> "BinaryWindow":
        return self

    @contextmanager
    def as_parsing_window(self) -> Generator[BinaryWindow, None, None]:
        with as_parsing_window(self) as pw:
            yield pw


class WindowPtr(Ptr):
    def __init__(self, offset: int, size: Optional[int] = None, whence: int = 0):
        super().__init__(offset, whence)
        self.size = size

    @contextmanager
    def stream_jump_to(self, stream: BinaryIO) -> Generator[BinaryIO, None, None]:
        with super().stream_jump_to(stream) as inner:
            with BinaryWindow.slice(inner, self.size) as window:
                yield window


class StreamWindowPtr(StreamPtr, WindowPtr):
    def __init__(
        self,
        stream: BinaryIO,
        offset: Optional[int] = None,
        size: Optional[int] = None,
        whence: int = 0,
    ):
        offset = offset if offset is not None else stream.tell()
        StreamPtr.__init__(self, stream, offset, whence)
        WindowPtr.__init__(self, offset, size, whence)

    @contextmanager
    def jump_to(self) -> Generator[BinaryIO, None, None]:
        with self.stream_jump_to(
            self.stream
        ) as inner:  # We don't have to use inner, but it makes it obvious that the inner stream has correctly jumped
            yield inner

import struct
from dataclasses import dataclass
from os.path import join
from typing import BinaryIO, Optional, Iterable, Any, Generator

from .structx import Struct
from .walkutil import OsWalk


def read_magic_word(stream: BinaryIO, layout: Struct, advance: bool = True) -> Optional[bytes]:
    origin = stream.tell()
    try:
        return layout.unpack_stream(stream)[0]
    except (struct.error, UnicodeDecodeError):
        return None
    finally:
        if not advance:  # Useful for checking the header before reading it
            stream.seek(origin)


def assert_magic_word(stream: BinaryIO, layout: Struct, word: bytes, advance: bool = True) -> None:
    magic = read_magic_word(stream, layout=layout, advance=advance)
    assert magic == word, (magic, word)


def check_magic_word(stream: BinaryIO, layout: Struct, word: bytes, advance: bool = True) -> bool:
    magic = read_magic_word(stream, layout=layout, advance=advance)
    return magic == word


def write_magic_word(stream: BinaryIO, layout: Struct, word: bytes) -> int:
    # We could just as easily write the word directly, but we don't
    return layout.pack_stream(stream, word)


@dataclass
class MagicWord:
    layout: Struct
    word: bytes

    def read_magic_word(self, stream: BinaryIO, advance: bool = True) -> Optional[bytes]:
        return read_magic_word(stream, self.layout, advance)

    def write_magic_word(self, stream: BinaryIO) -> int:
        return write_magic_word(stream, self.layout, self.word)

    def assert_magic_word(self, stream: BinaryIO, advance: bool = True) -> None:
        assert_magic_word(stream, self.layout, self.word, advance)

    def check_magic_word(self, stream: BinaryIO, advance: bool = False) -> bool:
        return check_magic_word(stream, self.layout, self.word, advance)


@dataclass
class MagicWordIO(MagicWord):

    def check_stream(self, stream: BinaryIO, advance_stream: bool = False) -> bool:
        return self.check_magic_word(stream, advance=advance_stream)

    def check_file(self, file: str, root: Optional[str] = None) -> bool:
        if root:
            file = join(root, file)
        with open(file, "rb") as handle:
            # we set advance to true to avoid pointlessly fixing the stream, since we are just going to close it
            return self.check_stream(handle, True)

    def iter_check_file(self, files: Iterable[str], root: Optional[str] = None) -> Generator[str, None, None]:
        return (file for file in files if self.check_file(file, root))

    # Pass in the os.walk() generator
    # Root and Folders will remain unchanged
    # Files will be replaced with files starting with the proper magic word
    def walk(self, walk: OsWalk) -> OsWalk:
        for root, _, files in walk:
            magic_files = [file for file in files if self.check_file(join(root, file))]
            yield root, _, magic_files

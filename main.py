# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from contextlib import contextmanager
from struct import Struct
from typing import BinaryIO, Tuple, Any


class BinarySerializer:
    UInt8 = Struct("B")
    UInt16 = Struct("H")
    UInt32 = Struct("I")
    UInt64 = Struct("L")
    Byte = Struct("c")

    def __init__(self, stream: BinaryIO):
        self.stream = stream

    def read(self, n: int = ...) -> bytes:
        return self.stream.read(n)

    def seek(self, offset: int = None, whence: int = ...):
        self.stream.seek(offset, whence)

    @contextmanager
    def bookmark(self):
        pos = self.stream.tell()
        yield
        self.stream.seek(pos)

    def unpack(self, layout: Struct):
        buffer = self.stream.read(layout.size)
        result = layout.unpack(buffer)
        if isinstance(result, tuple) and len(result) == 1:
            return result[0]
        else:
            return result

    def write(self, layout: Struct, data: Any) -> int:
        buffer = layout.pack(data)
        return self.stream.write(buffer)

    def read_len_encoded_bytes(self, length_layout: Struct = UInt32, data_layout: Struct = Byte) -> bytes:
        count: int = self.unpack(length_layout)
        return self.read(count * data_layout.size)

    def read_len_encoded(self, length_layout: Struct = UInt32, data_layout: Struct = Byte) -> Tuple:
        count: int = self.unpack(length_layout)
        items = [self.unpack(data_layout) for _ in range(count)]
        return tuple(items)

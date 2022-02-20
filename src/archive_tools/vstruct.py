import re
import struct
from typing import BinaryIO, Tuple, Any, Iterator, List

from . import structx
from .ioutil import as_hex_adr, BinaryWindow
from .structx import Struct, _StructFormat, _BufferFormat

WriteableBuffer = ReadableBuffer = _BufferFormat

_UInt32 = Struct("I")


def unpack_stream(__format: _StructFormat, __stream: BinaryIO) -> Tuple[Any, ...]:
    raise NotImplementedError


def iter_unpack_stream(__format: _StructFormat, __stream: BinaryIO) -> Iterator[Tuple[Any, ...]]:
    raise NotImplementedError


def pack_stream(fmt: _StructFormat, __stream: BinaryIO, *v) -> int:
    raise NotImplementedError


class _VarLenStruct(structx.Struct):
    __Int32 = structx.Struct("i")
    __UInt32 = structx.Struct("I")
    __map = {'v': __Int32, 'V': __UInt32}

    # noinspection PyMissingConstructor
    # We explicitly do not want to call super
    def __init__(self, fmt: str):
        self.char = fmt[-1]
        try:
            self.length = int(fmt[:-1])
        except ValueError:
            self.length = 1

    @property
    def size(self) -> int:
        return self.__map.get(self.char).size * self.length

    def unpack(self, __buffer: ReadableBuffer) -> Tuple[Any, ...]:
        return self.unpack_from_size(__buffer, 0)[0]

    def unpack_size(self, __buffer: ReadableBuffer) -> Tuple[Tuple[Any, ...], int]:
        return self.unpack_from_size(__buffer, 0)

    def unpack_from(self, buffer: ReadableBuffer, offset: int = ...) -> Tuple[Any, ...]:
        return self.unpack_from_size(buffer, offset)[0]

    def unpack_from_size(self, buffer: ReadableBuffer, offset: int = ...) -> Tuple[Tuple[Any, ...], int]:
        s_layout = self.__map.get(self.char)
        p = []
        buf_len = len(buffer)
        o = offset
        for _ in range(self.length):
            s: int = s_layout.unpack_from(buffer, o)[0]
            o += s_layout.size
            if o + s > buf_len:
                raise NotImplementedError
            v = buffer[o:o + s]

            p.append(v)
            o += s
        return tuple(p), o - offset

    def unpack_stream(self, __stream: BinaryIO) -> Tuple[Any, ...]:
        return self.unpack_stream_size(__stream)[0]

    def unpack_stream_size(self, __stream: BinaryIO) -> Tuple[Tuple[Any, ...], int]:
        s_layout = self.__map.get(self.char)
        p = []
        now = __stream.tell()
        for _ in range(self.length):
            s: int = s_layout.unpack_stream(__stream)[0]
            assert s >= 0, (s, "@", as_hex_adr((__stream.abs_tell() if isinstance(__stream, BinaryWindow) else __stream.tell()) - 4))  # TODO REMOVE DEBUG
            v: bytes = __stream.read(s)
            if len(v) != s:
                raise NotImplementedError
            p.append(v)
        then = __stream.tell()
        return tuple(p), then - now

    def pack(self, *v: Any) -> bytes:
        s_layout = self.__map.get(self.char)
        if len(v) != self.length:
            raise ValueError
        else:
            r = bytearray()
            for val in v:
                if not isinstance(val, (bytes, bytearray)):
                    raise ValueError
                v_len = s_layout.pack(len(val))
                r.extend(v_len)
                r.extend(val)
            return r

    def pack_into(self, buffer: WriteableBuffer, offset: int, *v: Any) -> None:
        s_layout = self.__map.get(self.char)
        if len(v) != self.length:
            raise ValueError
        else:
            o = offset
            for val in v:
                if not isinstance(val, (bytes, bytearray)):
                    raise ValueError
                s_layout.pack_into(buffer, o, len(val))
                o += s_layout.size
                # TODO make this better
                for i in range(len(val)):
                    buffer[o + i] = val[i]
                o += len(val)

    def pack_stream(self, __stream: BinaryIO, *v) -> int:
        s_layout = self.__map.get(self.char)
        if len(v) != self.length:
            raise ValueError
        else:
            w = 0
            for val in v:
                if not isinstance(val, (bytes, bytearray)):
                    raise ValueError
                w += s_layout.pack_stream(__stream, len(val))
                w += __stream.write(val)
            return w


def pack_len_encoded_str(value: str, length_layout: _StructFormat = _UInt32, encoding: str = None) -> bytes:
    buffer = value.encode(encoding)
    len_buffer = struct.pack(length_layout, len(buffer))
    return len_buffer + buffer


v_len_re = re.compile(r"([0-9]*[vV])")


def separate_vlen_format(fmt: str) -> List[str]:
    pos = 0
    parts = []
    while pos < len(fmt):
        match = v_len_re.search(fmt, pos)
        if match is None:
            parts.append(fmt[pos:])
            break
        else:
            s = match.span()
            if s[0] != pos:
                parts.append(fmt[pos:s[0]])
            parts.append(fmt[s[0]:s[1]])
            pos = s[1]
    return parts


def parse_vlen_format(fmt: List[str]) -> List[Struct]:
    p = []
    for f in fmt:
        f = f.strip()  # ensures format has no whitespace before '<=>@' characters
        if "v" in f or "V" in f:
            s = _VarLenStruct(f)  # Special struct for VLen handling
        else:
            s = Struct(f)
        p.append(s)
    return p


class VStruct:

    # 32bit "v" character represents a variable length byte object
    # v Int32 ~ V UInt32
    # note "v" does not respect alignment/padding!
    def __init__(self, fmt: str):
        self.is_variable_size = "v" in fmt or "V" in fmt
        self.__layout = self.__multi_layout = None
        if self.is_variable_size:
            f_list = separate_vlen_format(fmt)
            struct_list = parse_vlen_format(f_list)
            if len(struct_list) == 1:
                self.__layout = struct_list[0]
            else:
                self.__multi_layout = struct_list
        else:
            self.__layout = Struct(fmt)
        self.format = fmt

    @property
    def min_size(self) -> int:
        if self.is_variable_size:
            if self.__layout:
                return self.__layout.size
            else:
                s = 0
                for f in self.__multi_layout:
                    s += f.size
                return s
        else:
            return self.size

    @property
    def size(self) -> int:
        if self.is_variable_size:
            raise NotImplementedError
        else:
            return self.__layout.size

    def unpack(self, __buffer: _BufferFormat) -> Tuple[Any, ...]:
        if self.__multi_layout:
            return self.unpack_from(__buffer, 0)
        else:
            return self.__layout.unpack(__buffer)

    def unpack_from(self, __buffer: _BufferFormat, offset: int = ...) -> Tuple[Any, ...]:
        if self.__multi_layout:
            unpacked = []
            o = offset
            for part in self.__multi_layout:
                if isinstance(part, _VarLenStruct):
                    v, s = part.unpack_from_size(__buffer, o)
                else:
                    v = part.unpack_from(__buffer, o)
                    s = part.size
                o += s
                unpacked.append(v)
            return tuple(unpacked)
        else:
            return self.__layout.unpack_from(__buffer, offset)

    def unpack_stream(self, stream: BinaryIO) -> Tuple[Any, ...]:
        if self.__multi_layout:
            unpacked = []
            for part in self.__multi_layout:
                v = part.unpack_stream(stream)
                unpacked.extend(v)
            return tuple(unpacked)
        else:
            return self.__layout.unpack_stream(stream)

    def iter_unpack_stream(self, __stream: BinaryIO) -> Iterator[Tuple[Any, ...]]:
        while True:
            bm = __stream.tell()
            try:
                yield self.unpack_stream(__stream)
            except NotImplementedError:
                __stream.seek(bm)
                if len(__stream.read(1)) > 0:
                    __stream.seek(bm)
                    raise
                else:
                    break  # End of Stream; job's done

    def pack_stream(self, __stream: BinaryIO, *v) -> int:
        raise NotImplementedError

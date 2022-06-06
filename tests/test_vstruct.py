import math
import struct
from io import BytesIO
from math import floor
from typing import Tuple, Any, List, Iterable, Callable

from serialization_tools import vstruct
from serialization_tools.vstruct import _VarLenStruct, VStruct

__STRUCT_CHARS = r"cbB?hHiIlLqQnNefdpPs"
__VSTRUCT_CHARS = __STRUCT_CHARS + r"Vv"

INT_MIN_MAX = {
    "b": (-(2 ** 7), (2 ** 7) - 1),
    "B": (0, (2 ** 8) - 1),
    "h": (-(2 ** 15), (2 ** 15) - 1),
    "H": (0, (2 ** 16) - 1),
    "i": (-(2 ** 31), (2 ** 31) - 1),
    "I": (0, (2 ** 32) - 1),
    "l": (-(2 ** 31), (2 ** 31) - 1),
    "L": (0, (2 ** 32) - 1),
    "q": (-(2 ** 63), (2 ** 63) - 1),
    "Q": (0, (2 ** 64) - 1),
}
BOOL_MAP = {True: b"\x01", False: b"\x00"}
NATIVE_INT_MIN_MAX = {
    "n": INT_MIN_MAX["i"],
    "N": INT_MIN_MAX["I"],
}

WORDS = ["The Quick Brown Dog Jumped Over The Lazy Fox", "The", "Quick", "Brown", "Dog", "Jumped", "Over", "The", "Lazy", "Fox"]


def data_generator(c: str, l: int = None) -> Iterable[Any]:
    if l is None:
        l = 1
    if c in INT_MIN_MAX:  # Int-likes
        min_val, max_val = INT_MIN_MAX[c]
        step = floor((max_val - min_val) / l)
        for i in range(l):
            yield min_val + step * i
    elif c in ["c"]:  # Byte Array
        min_val, max_val = INT_MIN_MAX["B"]  # reuse UByte
        step = floor((max_val - min_val) / l)
        for i in range(l):
            val = step * i
            yield val.to_bytes(1, byteorder="little")
    elif c in ["?"]:  # Byte Array
        for i in range(l):
            flag = (i % 2) == 0  # is multiple of prime 2?
            PRIMES = [19, 17, 13, 11, 7, 5, 3]
            # For variety, longer arrays check for different primes
            for p in PRIMES:
                if l > p ** 2:
                    flag = (i % p) == 0
                    break
            yield flag
    elif c in NATIVE_INT_MIN_MAX:
        min_val, max_val = NATIVE_INT_MIN_MAX[c]  # Separate map since this is a HACK
        step = floor((max_val - min_val) / l)
        for i in range(l):
            yield min_val + step * i
    elif c in ["e", "f", "d"]:
        for i in range(l):
            yield 2 * (i / (l - 1 if (l > 1) else 1)) - 1  # [-1f,1f], we could use larger values but this range is simple
    elif c in _VarLenStruct.SPECIAL:
        gen = WORDS
        gen_enc = [g.encode("ascii") for g in gen]
        for i in range(l):
            yield gen_enc[i % len(gen_enc)]
    elif c in ["s"]:
        AB = "Abcdefghijklmnopqrstuvwxyz "
        # PRIMES = [2, 3, 5, 7, 11, 101, 131, 151, 181, 191, 313, 353, 373, 383, 727, 757, 787, 797, 919, 929]
        # for __ in range(l): #
        #     prime = PRIMES[__ % len(PRIMES)]
        prime = 929  # cant reutnr multiple results for `s`
        word = "".join(AB[(_ * prime) % len(AB)] for _ in range(l))
        yield word.encode("ascii")  # Still needs to be a bytes object
    else:
        raise NotImplementedError(c)


def get_data_and_buffer() -> Iterable[Tuple[str, List[Any], bytes]]:
    for f in __VSTRUCT_CHARS:
        for args in range(10):
            f_c = args + 1
            fmt = f"{f_c}{f}"
            data = list(data_generator(f, f_c))  # +1 to get [1,10]
            if f in __STRUCT_CHARS and f not in _VarLenStruct.SPECIAL:
                buffer = struct.pack(fmt, *data)
            else:
                buffer = vstruct.pack(fmt, *data)
            yield fmt, data, buffer


def shared_test_unpack(unpack_func: Callable[[str, List, bytes], Tuple[Any, ...]]):
    for (fmt, data, buffer) in get_data_and_buffer():
        result = unpack_func(fmt, data, buffer)
        for src, res in zip(data, result):
            f = fmt[-1]
            if f in ["f", "e", "d"]:
                closeness = {'e': 0.001, 'f': 0.00001, 'd': 0.000000001}
                assert math.isclose(src, res, rel_tol=closeness[f])
            else:
                assert src == res


def shared_test_pack(pack_func: Callable[[str, List, bytes], bytes]):
    for (fmt, data, buffer) in get_data_and_buffer():
        result = pack_func(fmt, data, buffer)
        assert buffer == result


class TestModule:
    def test_unpack_stream(self):
        def do_unpack(fmt: str, data: List, buffer: bytes):
            with BytesIO(buffer) as stream:
                return vstruct.unpack_stream(fmt, stream)

        shared_test_unpack(do_unpack)

    def test_unpack_from(self):
        shared_test_unpack(lambda fmt, data, buffer: vstruct.unpack_from(fmt, buffer, 0))

    def test_unpack(self):
        shared_test_unpack(lambda fmt, data, buffer: vstruct.unpack(fmt, buffer))

    def test_pack_stream(self):
        def do_pack(fmt: str, data: List, buffer: bytes):
            with BytesIO() as stream:
                vstruct.pack_stream(fmt, stream, *data)
                stream.seek(0)
                return stream.read()

        shared_test_pack(do_pack)

    def test_pack_into(self):
        def do_pack(fmt: str, data: List, buffer: bytes):
            write_buf = bytearray(len(buffer))
            vstruct.pack_into(fmt, write_buf, 0, *data)
            return write_buf

        shared_test_pack(do_pack)

    def test_pack(self):
        shared_test_pack(lambda fmt, data, buffer: vstruct.pack(fmt, *data))


class TestVStruct:
    def test_unpack_stream(self):
        def do_unpack(fmt: str, data: List, buffer: bytes):
            with BytesIO(buffer) as stream:
                return VStruct(fmt).unpack_stream(stream)

        shared_test_unpack(do_unpack)

    def test_unpack_from(self):
        shared_test_unpack(lambda fmt, data, buffer: VStruct(fmt).unpack_from(buffer, 0))

    def test_unpack(self):
        shared_test_unpack(lambda fmt, data, buffer: VStruct(fmt).unpack( buffer))

    def test_pack_stream(self):
        def do_pack(fmt: str, data: List, buffer: bytes):
            with BytesIO() as stream:
                VStruct(fmt).pack_stream(stream, *data)
                stream.seek(0)
                return stream.read()

        shared_test_pack(do_pack)

    def test_pack_into(self):
        def do_pack(fmt: str, data: List, buffer: bytes):
            write_buf = bytearray(len(buffer))
            VStruct(fmt).pack_into(write_buf, 0, *data)
            return write_buf

        shared_test_pack(do_pack)

    def test_pack(self):
        shared_test_pack(lambda fmt, data, buffer: VStruct(fmt).pack(*data))

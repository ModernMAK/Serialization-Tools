import itertools
from io import BytesIO
from serialization_tools.structx import Struct
from typing import Tuple, Any, BinaryIO

import pytest
import serialization_tools.magic as m


def assert_advance(start: int, end: int, advance: bool):
    if advance:
        assert start != end
    else:
        assert start == end


_EndianAlignCodes = "<>=@!"
_IntCodes = "bBhHiIlLqQ"
_FloatCodes = "efd"
_StringCode = "s"
_CharCode = "c"
_SIZES = [1, 2, 4, 8, 16]

_INTS = [
    Struct(f"{e_code}{s_code}")
    for e_code, s_code in itertools.product(_EndianAlignCodes, _IntCodes)
]
_FLOATS = [
    Struct(f"{e_code}{s_code}")
    for e_code, s_code in itertools.product(_EndianAlignCodes, _FloatCodes)
]
_STRINGS = {
    size: [Struct(f"{e_code}{size}{_StringCode}") for e_code in _EndianAlignCodes]
    for size in _SIZES
}
_INT_SAMPLES = [0, 15, 63, 127]
_FLOAT_SAMPLES = [0.0, 0.5, 1, 1.5]
_RAW_STRING_SAMPLES = [
    b"My Magic Word\0\0\0",
    b"\xde\xad\xbe\xed\0\0\0\0\xde\xad\xbe\xed\0\0\0\0",
    b"dead-beef. abba!",
    b"The quick brown.",
]
_STRING_SAMPLES = {size: [s[:size] for s in _RAW_STRING_SAMPLES] for size in _SIZES}

_INTS_AND_DATA = itertools.product(_INTS, _INT_SAMPLES)
_FLOATS_AND_DATA = itertools.product(_FLOATS, _FLOAT_SAMPLES)
_STRINGS_AND_DATA = [
    itertools.product(_STRINGS[size], _STRING_SAMPLES[size]) for size in _SIZES
]

_LAYOUTS_AND_DATA = [*_INTS_AND_DATA, *_FLOATS_AND_DATA]
for _STRING_AND_DATA in _STRINGS_AND_DATA:
    _LAYOUTS_AND_DATA.extend(_STRING_AND_DATA)


def garbagify(layout: Struct, data: Any):
    return bytes([byte ^ 0xFF for byte in layout.pack(data)])


class SharedTestData:
    @pytest.fixture(params=_LAYOUTS_AND_DATA)
    def stream_layout_and_result(self, request) -> Tuple[BytesIO, Struct, Any]:
        layout: Struct
        data: Any
        layout, data = request.param
        encoded = layout.pack(data)
        return BytesIO(encoded), layout, data

    @pytest.fixture(params=[True, False])
    def advance(self, request) -> bool:
        return request.param


class TestModule(SharedTestData):
    def test_read_magic_word(self, stream_layout_and_result, advance: bool):
        stream, layout, data = stream_layout_and_result

        start = stream.tell()
        result = m.read_magic_word(stream, layout, advance)
        end = stream.tell()

        assert data == result
        assert_advance(start, end, advance)

    def test_assert_magic_word_pass(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result

        start = stream.tell()
        try:
            m.assert_magic_word(stream, layout, data, advance)
        except AssertionError:
            raise AssertionError(
                "The stream asserted that the magic word did not match, when it should have."
            )
        end = stream.tell()
        assert_advance(start, end, advance)

    def test_assert_magic_word_fail(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        garbage = garbagify(layout, data)
        start = stream.tell()
        try:
            m.assert_magic_word(stream, layout, garbage, advance)
        except AssertionError:
            pass
        else:
            raise AssertionError(
                "The stream asserted that the magic word matched, when it shouldn't have."
            )
        end = stream.tell()
        assert_advance(start, end, advance)

    def test_check_magic_word_pass(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result

        start = stream.tell()
        result = m.check_magic_word(stream, layout, data, advance)
        end = stream.tell()

        assert result
        assert_advance(start, end, advance)

    def test_check_magic_word_fail(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        garbage = garbagify(layout, data)

        start = stream.tell()
        result = m.check_magic_word(stream, layout, garbage, advance)
        end = stream.tell()

        assert not result
        assert_advance(start, end, advance)

    def test_write_magic_word(self, stream_layout_and_result):
        stream, layout, data = stream_layout_and_result
        with BytesIO() as writable:
            written = m.write_magic_word(writable, layout, data)
            writable.seek(0)
            expected = stream.read()
            result = writable.read()
            assert expected == result
            assert len(result) == written
            assert written == layout.size


class TestMagicWord(SharedTestData):
    def create_mw(self, layout: Struct, data: Any) -> m.MagicWord:
        return m.MagicWord(layout, data)

    def test_read_magic_word(self, stream_layout_and_result, advance: bool):
        stream, layout, data = stream_layout_and_result
        magic = self.create_mw(layout, data)

        start = stream.tell()
        result = magic.read_magic_word(stream, advance)
        end = stream.tell()

        assert data == result
        assert_advance(start, end, advance)

    def test_assert_magic_word_pass(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        magic = self.create_mw(layout, data)
        start = stream.tell()
        try:
            magic.assert_magic_word(stream, advance)
        except AssertionError:
            raise AssertionError(
                "The stream asserted that the magic word did not match, when it should have."
            )
        end = stream.tell()
        assert_advance(start, end, advance)

    def test_assert_magic_word_fail(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        garbage = garbagify(layout, data)
        magic = self.create_mw(layout, garbage)
        start = stream.tell()
        try:
            magic.assert_magic_word(stream, advance)
        except AssertionError:
            pass
        else:
            raise AssertionError(
                "The stream asserted that the magic word matched, when it shouldn't have."
            )
        end = stream.tell()
        assert_advance(start, end, advance)

    def test_check_magic_word_pass(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        magic = self.create_mw(layout, data)

        start = stream.tell()
        result = magic.check_magic_word(stream, advance)
        end = stream.tell()

        assert result
        assert_advance(start, end, advance)

    def test_check_magic_word_fail(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        garbage = garbagify(layout, data)
        magic = self.create_mw(layout, garbage)
        start = stream.tell()
        result = magic.check_magic_word(stream, advance)
        end = stream.tell()

        assert not result
        assert_advance(start, end, advance)

    def test_write_magic_word(self, stream_layout_and_result):
        stream, layout, data = stream_layout_and_result
        magic = self.create_mw(layout, data)
        with BytesIO() as writable:
            written = magic.write_magic_word(writable)
            writable.seek(0)
            expected = stream.read()
            result = writable.read()
            assert expected == result
            assert len(result) == written
            assert written == layout.size


class TestMagicWordIO(TestMagicWord):
    def create_mw(self, layout: Struct, data: Any) -> m.MagicWordIO:
        return m.MagicWordIO(layout, data)

    def test_check_magic_word_pass(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        magic = self.create_mw(layout, data)

        start = stream.tell()
        result = magic.check_stream(stream, advance)
        end = stream.tell()

        assert result
        assert_advance(start, end, advance)

    def test_check_magic_word_fail(self, stream_layout_and_result, advance):
        stream, layout, data = stream_layout_and_result
        garbage = garbagify(layout, data)
        magic = self.create_mw(layout, garbage)
        start = stream.tell()
        result = magic.check_stream(stream, advance)
        end = stream.tell()
        assert not result
        assert_advance(start, end, advance)

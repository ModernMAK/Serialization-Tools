import importlib
from types import ModuleType

import pytest


def get_attr(module: ModuleType, attr: str):
    parts = attr.split(".")
    result = module
    for name in parts:
        result = getattr(result, name)
    return result


class RegressionTests:
    def test_module(self, module: str):
        try:
            _ = importlib.import_module(module)
        except ImportError:
            raise AssertionError(f"Possible regression; {module} cannot be imported!")

    def test_attribute(self, module: str, attr: str):
        try:
            m = importlib.import_module(module)
            _ = get_attr(m, attr)
        except ImportError:
            raise AssertionError(f"Possible regression; {module} cannot be imported!")
        except AttributeError as e:
            raise AssertionError(
                f"Possible regression; {attr} cannot be imported from {module}!"
            )


class TestSerializationTools(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize("attr", [])
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


class TestCommonDirectories(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.common_directories"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize(
        "attr",
        ["read_install_path_from_registry", "get_steam_install_dir", "get_appdata_dir"],
    )
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


class TestError(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.error"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize(
        "attr",
        ["ParsingError", "packing_args_error"],
    )
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


_IOUTIL_ALL = [
    "as_parsing_window",
    "as_hex_adr",
    "has_data",
    "end_of_stream",
    "iter_read",
    "abs_tell",
    "stream2hex",
    "Ptr",
    "Ptr.stream_jump_to",
    "StreamPtr",
    "StreamPtr.jump_to",
    "BinaryWindow",
    "BinaryWindow.slice",
    "BinaryWindow.abs_tell",
    "BinaryWindow.close",
    "BinaryWindow.fileno",
    "BinaryWindow.flush",
    "BinaryWindow.isatty",
    "BinaryWindow.read",
    "BinaryWindow.readable",
    "BinaryWindow.readline",
    "BinaryWindow.readlines",
    "BinaryWindow.seek",
    "BinaryWindow.seekable",
    "BinaryWindow.tell",
    "BinaryWindow.truncate",
    "BinaryWindow.writable",
    "BinaryWindow.write",
    "BinaryWindow.writelines",
    "BinaryWindow.__next__",
    "BinaryWindow.__iter__",
    "BinaryWindow.__exit__",
    "BinaryWindow.__enter__",
    "BinaryWindow.as_parsing_window",
    "WindowPtr",
    "WindowPtr.stream_jump_to",
    "StreamWindowPtr",
    "StreamWindowPtr.jump_to",
]


class TestIOUtil(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.ioutil"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize("attr", _IOUTIL_ALL)
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


_MAGIC_ALL = [
    "read_magic_word",
    "assert_magic_word",
    "check_magic_word",
    "write_magic_word",
    "MagicWord.read_magic_word",
    "MagicWord.assert_magic_word",
    "MagicWord.check_magic_word",
    "MagicWord.write_magic_word",
    "MagicWordIO.check_stream",
    "MagicWordIO.check_file",
    "MagicWordIO.iter_check_file",
]


class TestMagic(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.magic"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize("attr", _MAGIC_ALL)
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


_SIZE_PREFIX = "KMGTPEZY"
_SIZE_ALL = [
    "B",
    *[f"{c}B" for c in _SIZE_PREFIX],
    *[f"{c}iB" for c in _SIZE_PREFIX],
    "BinarySI",
    "SI",
    "SI_Power",
]


class TestSize(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.size"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize("attr", _SIZE_ALL)
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


_STRUCTX_ALL = [
    "unpack_stream",
    "unpack_from",
    "pack_into",
    "iter_unpack_stream",
    "pack_stream",
    "unpack_len_encoded_bytes",
    "pack_len_encoded_bytes",
    "unpack_len_encoded",
    "pack_len_encoded",
    "unpack_len_encoded_str",
    "pack_len_encoded_str",
    "count_args",
    "Struct",
    "Struct.pack_stream",
    "Struct.iter_unpack_stream",
    "Struct.unpack_stream",
]


class TestStructx(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.structx"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize("attr", _STRUCTX_ALL)
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


_VSTRUCT_ALL = [
    "iter_unpack_stream",
    "pack",
    "pack_into",
    "pack_len_encoded_str",
    "pack_stream",
    "parse_vlen_format",
    "ReadableBuffer",
    "separate_vlen_format",
    "unpack",
    "unpack_from",
    "unpack_stream",
    "WriteableBuffer",
    "VStruct",
    "VStruct.args",
    "VStruct.iter_unpack_stream",
    "VStruct.min_size",
    "VStruct.pack",
    "VStruct.pack_into",
    "VStruct.pack_stream",
    "VStruct.size",
    "VStruct.unpack",
    "VStruct.unpack_from",
    "VStruct.unpack_stream",
]


class TestVStruct(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.vstruct"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize("attr", _VSTRUCT_ALL)
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)


_WALKUTIL_ALL = [
    "WhiteList",
    "BlackList",
    "OsWalkResult",
    "OsWalk",
    "WalkPredicate",
    "strict_whitelisted",
    "whitelisted",
    "strict_blacklisted",
    "blacklisted",
    "file_extension_allowed",
    "file_extension_allowed_predicate",
    "filter_by_file_extension",
    "path_allowed",
    "path_allowed_predicate",
    "filter_by_path",
    "filter_files_by_predicate",
    "filter_folders_by_predicate",
    "filter_by_predicate",
    "collapse_walk_on_files",
]


class TestWalkUtil(RegressionTests):
    @pytest.fixture
    def module(self) -> str:
        return "serialization_tools.walkutil"

    def test_module(self, module: str):
        return super().test_module(module)

    @pytest.mark.parametrize("attr", _WALKUTIL_ALL)
    def test_attribute(self, module: str, attr: str):
        return super().test_attribute(module, attr)

import os
import sys
from pathlib import PureWindowsPath as RegPath, Path
from typing import Optional

_VALVE_REG_PATH = RegPath(r"Valve\Steam")
_INSTALL_PATH = "InstallPath"

_SOFTWARE_REG_ROOTS = {
    32: RegPath(r"SOFTWARE"),
    64: RegPath(r"SOFTWARE\WOW6432Node"),
}

if sys.platform.startswith("win32"):
    from winreg import HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx  # QueryValue fails for some reason?! Have to use QueryValueEx


    def read_install_path_from_registry(sub_path: os.PathLike[str], bit_mode: int = 32) -> str:
        key_path = _SOFTWARE_REG_ROOTS[bit_mode]
        full_path = key_path / sub_path
        with OpenKey(HKEY_LOCAL_MACHINE, str(full_path)) as key_handle:
            value:str = QueryValueEx(key_handle, _INSTALL_PATH)[0]
            return value


else:
    def read_install_path_from_registry(sub_path: str, bit_mode: int = 32) -> Optional[str]:
        raise TypeError("Not supported on non-windows platforms")


def get_steam_install_dir() -> Path:
    try:  # Try 64 bit first
        steam = read_install_path_from_registry(_VALVE_REG_PATH, 64)
    except FileNotFoundError:  # otherwise, try 32 bit
        steam = read_install_path_from_registry(_VALVE_REG_PATH, 32)
    return Path(steam)


def get_appdata_dir(sub_dir: Optional[str] = None) -> Path:
    path = Path("~/Appdata").expanduser()
    if sub_dir:
        path /= sub_dir
    return path


if __name__ == "__main__":
    print(get_steam_install_dir())
    print(get_appdata_dir())

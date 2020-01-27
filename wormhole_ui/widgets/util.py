import os
from pathlib import Path

SHELL_FOLDERS = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders"
DOWNLOADS_GUID = "{374DE290-123F-4565-9164-39C4925E467B}"


def get_download_path_or_cwd():
    download_path = get_download_path()
    if download_path is None or not Path(download_path).exists():
        return Path.cwd()
    else:
        return download_path.resolve()


def get_download_path():
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SHELL_FOLDERS) as key:
                return Path(winreg.QueryValueEx(key, DOWNLOADS_GUID)[0])
        except Exception:
            return None
    else:
        return Path.home() / "Downloads"

import os
from pathlib import Path

from ...errors import DiskSpaceError, RespondError


class DestFile:
    def __init__(self, filename, filesize):
        self.id = None
        # Path().name is intended to protect us against
        # "~/.ssh/authorized_keys" and other attacks
        self.name = Path(filename).name
        self.full_path = None
        self.final_bytes = filesize
        self.transfer_bytes = self.final_bytes
        self.file_object = None
        self._temp_path = None

    def open(self, id, dest_path):
        self.id = id
        self.full_path = Path(dest_path).resolve() / self.name
        self._temp_path = _find_unique_path(
            self.full_path.with_suffix(self.full_path.suffix + ".part")
        )

        if not _has_disk_space(self.full_path, self.transfer_bytes):
            raise RespondError(
                DiskSpaceError(
                    f"Insufficient free disk space (need {self.transfer_bytes}B)"
                )
            )

        self.file_object = open(self._temp_path, "wb")

    def finalise(self):
        self.file_object.close()

        self.full_path = _find_unique_path(self.full_path)
        self.name = self.full_path.name
        return self._temp_path.rename(self.full_path)

    def cleanup(self):
        self.file_object.close()
        try:
            self._temp_path.unlink()
        except Exception:
            pass


def _find_unique_path(path):
    path_attempt = path
    count = 1
    while path_attempt.exists():
        path_attempt = path.with_suffix(f".{count}" + path.suffix)
        count += 1

    return path_attempt


def _has_disk_space(target, target_size):
    # f_bfree is the blocks available to a root user. It might be more
    # accurate to use f_bavail (blocks available to non-root user), but we
    # don't know which user is running us, and a lot of installations don't
    # bother with reserving extra space for root, so let's just stick to the
    # basic (larger) estimate.
    try:
        s = os.statvfs(target.parent)
        return s.f_frsize * s.f_bfree > target_size
    except AttributeError:
        return True

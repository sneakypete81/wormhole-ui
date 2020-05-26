import os
from pathlib import Path
import tempfile
import zipfile

from twisted.internet import defer, threads

from ...errors import SendFileError


def source_factory(id, path):
    if Path(path).is_file():
        return SourceFile(id, path)
    elif Path(path).is_dir():
        return SourceDirectory(id, path)

    raise SendFileError("Can only send files or directories")


class Source:
    def __init__(self, id, path):
        path = Path(path).resolve()
        assert path.exists()

        self.id = id
        self.name = path.name
        self.full_path = path
        self.final_bytes = None
        self.transfer_bytes = None
        self.num_files = None
        self.file_object = None

    def open(self):
        raise NotImplementedError


class SourceFile(Source):
    def open(self):
        self.file_object = open(self.full_path, "rb")
        self.file_object.seek(0, 2)
        self.final_bytes = self.file_object.tell()
        self.transfer_bytes = self.final_bytes
        self.file_object.seek(0, 0)
        self.num_files = 1


class SourceDirectory(Source):
    @defer.inlineCallbacks
    def open(self):
        # We're sending a directory. Create a zipfile and send that
        # instead. SpooledTemporaryFile will use RAM until our size
        # threshold (10MB) is reached, then moves everything into a
        # tempdir (it tries $TMPDIR, $TEMP, $TMP, then platform-specific
        # paths like /tmp).
        self.file_object = tempfile.SpooledTemporaryFile(max_size=10 * 1000 * 1000)

        # workaround for https://bugs.python.org/issue26175 (STF doesn't
        # fully implement IOBase abstract class), which breaks the new
        # zipfile in py3.7 that expects .seekable
        if not hasattr(self.file_object, "seekable"):
            # AFAICT all the filetypes that STF wraps can seek
            self.file_object.seekable = lambda: True

        yield threads.deferToThread(self._build_zipfile)
        self.file_object.seek(0, 2)
        self.transfer_bytes = self.file_object.tell()
        self.file_object.seek(0, 0)

    def _build_zipfile(self):
        self.num_files = 0
        self.final_bytes = 0

        with zipfile.ZipFile(
            self.file_object, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        ) as zf:
            filepaths = self.full_path.rglob("*")
            for filepath in [f for f in filepaths if f.is_file()]:
                try:
                    zf.write(filepath, filepath.relative_to(self.full_path))
                    self.final_bytes += os.stat(filepath).st_size
                    self.num_files += 1
                except OSError as e:
                    errmsg = u"{}: {}".format(filepath, e.strerror)
                    raise SendFileError(errmsg)

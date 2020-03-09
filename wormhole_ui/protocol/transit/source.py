from pathlib import Path

from ...errors import SendFileError


def source_factory(id, file_path):
    if file_path.is_file():
        return SourceFile(id, file_path)
    elif file_path.is_dir():
        return SourceDir(id, file_path)

    raise SendFileError("Only files or directories can be sent")


class Source:
    def __init__(self, id, file_path):
        file_path = Path(file_path).resolve()
        assert file_path.exists()

        self.id = id
        self.name = file_path.name
        self.full_path = file_path
        self.final_bytes = None
        self.transfer_bytes = None
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


class SourceDir(Source):
    def open(self):
        raise NotImplementedError

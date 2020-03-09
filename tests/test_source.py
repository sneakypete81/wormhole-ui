from pathlib import Path
import zipfile

from hamcrest import assert_that, is_, ends_with, has_length
import pytest

from wormhole_ui.protocol.transit.source import SourceDir, SourceFile


@pytest.fixture
def test_file_path():
    return str(Path(__file__).parent / "test_files" / "file.txt")


@pytest.fixture
def test_dir_path():
    return str(Path(__file__).parent / "test_files")


class TestSourceFile:
    def test_attributes_are_set(self, test_file_path):
        source_file = SourceFile(13, test_file_path)

        assert_that(source_file.id, is_(13))
        assert_that(source_file.name, is_("file.txt"))

    def test_open_creates_file_object(self, test_file_path):
        source_file = SourceFile(13, test_file_path)

        source_file.open()

        assert_that(source_file.file_object.name, ends_with("file.txt"))

    def test_open_gets_file_size(self, test_file_path):
        source_file = SourceFile(13, test_file_path)

        source_file.open()

        assert_that(source_file.transfer_bytes, is_(33))
        assert_that(source_file.final_bytes, is_(33))


class TestSourceDir:
    def test_attributes_are_set(self, test_dir_path):
        source_dir = SourceDir(13, test_dir_path)

        assert_that(source_dir.id, is_(13))
        assert_that(source_dir.name, is_("test_files"))

    def test_open_creates_a_zipfile_object(self, test_dir_path):
        source_dir = SourceDir(13, test_dir_path)

        source_dir.open()

        assert_that(source_dir.file_object.closed, is_(False))
        assert_that(source_dir.num_files, is_(2))

    def test_open_gets_file_size(self, test_dir_path):
        source_dir = SourceDir(13, test_dir_path)

        source_dir.open()

        assert_that(source_dir.final_bytes, is_(67))
        assert_that(source_dir.transfer_bytes, is_(288))

    def test_open_zips_directory_contents(self, test_dir_path):
        source_dir = SourceDir(13, test_dir_path)

        source_dir.open()

        with zipfile.ZipFile(source_dir.file_object) as zf:
            assert_that(zf.infolist(), has_length(2))
            assert_that(zf.read("file.txt"), is_(b"This is a file used for testing.\n"))
            assert_that(
                zf.read("subdir/file2.txt"),
                is_(b"This is a file in a subdirectory.\n"),
            )

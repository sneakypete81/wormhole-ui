from pathlib import Path

from hamcrest import assert_that, is_, ends_with
import pytest

from wormhole_ui.transit.source_file import SourceFile


@pytest.fixture
def test_file_path():
    return str(Path(__file__).parent / "test_files" / "file.txt")


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

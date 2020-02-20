from hamcrest import assert_that, calling, is_, raises

from wormhole_ui.errors import RespondError
from wormhole_ui.protocol.transit.dest_file import DestFile


class TestDestFile:
    def test_attributes_are_set(self):
        dest_file = DestFile("file.txt", 42)

        assert_that(dest_file.name, is_("file.txt"))
        assert_that(dest_file.final_bytes, is_(42))
        assert_that(dest_file.transfer_bytes, is_(42))

    def test_path_to_filename_is_removed(self):
        dest_file = DestFile("path/to/file.txt", 42)

        assert_that(dest_file.name, is_("file.txt"))

    def test_open_creates_temp_file(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 42)

        dest_file.open(13, str(tmp_path))

        assert_that(dest_file.file_object.name, is_(str(tmp_path / "file.txt.part")))
        assert_that((tmp_path / "file.txt.part").exists())

    def test_open_creates_unique_temp_file(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 42)
        (tmp_path / "file.txt.part").touch()

        dest_file.open(13, str(tmp_path))

        assert_that(dest_file.file_object.name, is_(str(tmp_path / "file.txt.1.part")))
        assert_that((tmp_path / "file.txt.1.part").exists())

    def test_open_raises_error_if_insufficient_disk_space(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 1024 * 1024 * 1024 * 1024 * 1024)

        assert_that(
            calling(dest_file.open).with_args(13, str(tmp_path), raises(RespondError))
        )

    def test_finalise_closes_the_file(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt,", 42)
        dest_file.open(13, tmp_path)

        dest_file.finalise()

        assert_that(dest_file.file_object.closed, is_(True))

    def test_finalise_renames_the_temp_file(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 42)
        dest_file.open(13, tmp_path)

        dest_file.finalise()

        assert_that(dest_file.full_path, is_(tmp_path / "file.txt"))
        assert_that((tmp_path / "file.txt").exists(), is_(True))
        assert_that((tmp_path / "file.txt.part").exists(), is_(False))

    def test_finalise_creates_unique_filename(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 42)
        dest_file.open(13, tmp_path)
        (tmp_path / "file.txt").touch()
        (tmp_path / "file.1.txt").touch()

        dest_file.finalise()

        assert_that(dest_file.name, is_("file.2.txt"))
        assert_that(dest_file.full_path, is_(tmp_path / "file.2.txt"))
        assert_that((tmp_path / "file.2.txt").exists(), is_(True))

    def test_cleanup_closes_the_file(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 42)
        dest_file.open(13, tmp_path)

        dest_file.cleanup()

        assert_that(dest_file.file_object.closed, is_(True))

    def test_cleanup_deletes_the_temp_file(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 42)
        dest_file.open(13, tmp_path)

        dest_file.cleanup()

        assert_that((tmp_path / "file.txt.part").exists(), is_(False))

    def test_cleanup_does_nothing_if_temp_file_already_deleted(self, tmp_path):
        tmp_path = tmp_path.resolve()
        dest_file = DestFile("file.txt", 42)
        dest_file.open(13, tmp_path)
        dest_file.finalise()
        assert_that((tmp_path / "file.txt.part").exists(), is_(False))

        dest_file.cleanup()

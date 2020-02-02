from humanize import naturalsize
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QDialog, QFileDialog

from .ui_dialog import UiDialog
from .util import get_download_path_or_cwd


class SaveFileDialog(UiDialog):
    def __init__(self, parent):
        super().__init__(parent, "SaveFile.ui")

        self.filename = None
        self.destination_edit.setText(str(get_download_path_or_cwd()))

        self.browse_button.clicked.connect(self._on_browse_button)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def open(self, filename, size):
        self.filename = filename

        if self.remember_checkbox.isChecked():
            self.finished.emit(QDialog.Accepted)
            return

        truncated_filename = self.truncate(filename)
        self.filename_label.setText(f"{truncated_filename} [{naturalsize(size)}]")
        super().open()

    def get_destination_directory(self):
        return self.destination_edit.text()

    @Slot()
    def _on_browse_button(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Download Location", self.destination_edit.text()
        )
        if directory != "":
            self.destination_edit.setText(directory)

    @staticmethod
    def truncate(filename, max_chars=40):
        if len(filename) <= max_chars:
            return filename

        stem, suffixes = filename.split(".", maxsplit=1)
        return stem[: max_chars - 3] + "..." + suffixes

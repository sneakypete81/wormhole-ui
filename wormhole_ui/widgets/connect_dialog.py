import platform

from PySide2.QtCore import Slot
from PySide2.QtWidgets import QDialog

from .ui_dialog import UiDialog


class ConnectDialog(UiDialog):
    def __init__(self, parent, wormhole):
        super().__init__(parent, "ConnectDialog.ui")

        self.wormhole = wormhole
        self.code = None

        self.set_code_button.clicked.connect(self._on_set_code_button)
        self.quit_button.clicked.connect(self.reject)

        # MacOS requires a 'Quit' button, since there's no native way of closing a
        # sheet. https://forum.qt.io/topic/27182/solved-qdialog-mac-os-setwindowflags
        # has another possible solution.
        if platform.system() != "Darwin":
            self.quit_button.hide()

        wormhole.signals.wormhole_open.connect(self._on_wormhole_open)
        wormhole.signals.code_received.connect(self._on_code_received)
        wormhole.signals.error.connect(self._on_error)
        wormhole.signals.wormhole_closed.connect(self._on_wormhole_closed)

    def open(self):
        self._request_new_code()
        super().open()

    @Slot()
    def _on_wormhole_open(self):
        """
        Close the dialog if the wormhole is opened successfully.
        """
        self.accept()

    @Slot()
    def _on_wormhole_closed(self):
        """
        Open the dialog and attempt to repen the wormhole if the wormhole is closed.
        Do nothing if the dialog was manually closed.
        """
        if self.result() != QDialog.Rejected:
            self.open()

    @Slot(str)
    def _on_code_received(self, code):
        self.set_code_button.setEnabled(True)
        self.code = code[:100]
        self._refresh()

    @Slot()
    def _on_set_code_button(self):
        self.set_code_button.setDisabled(True)
        self.wormhole.set_code(self.code_edit.text().strip())

    @Slot(Exception, str)
    def _on_error(self, exception, traceback):
        self.set_code_button.setEnabled(True)

    def _request_new_code(self):
        # Don't allow code to be changed until one has been allocated
        self.code_edit.setText("")
        self.set_code_button.setDisabled(True)

        self.code = None
        self._refresh()
        self.wormhole.open()

    def _refresh(self):
        code = self.code
        if code is None:
            code = "[obtaining code...]"
        self.code_label.setText(code)

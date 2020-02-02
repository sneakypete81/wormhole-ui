import logging
import platform

from PySide2.QtCore import Slot
from PySide2.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
)

from .connect_dialog import ConnectDialog
from .errors import get_error_text
from .message_table import MessageTable
from .save_file_dialog import SaveFileDialog
from .shutdown_message import ShutdownMessage
from .ui import CustomWidget, load_ui

WIN_STYLESHEET = """
* {
    font-family: "Calibri";
    font-size: 12pt;
}
QPushButton {
    padding-top: 4px;
    padding-bottom: 4px;
    padding-left: 15px;
    padding-right: 15px;
}
"""


class MainWindow(QMainWindow):
    def __init__(self, wormhole):
        super().__init__()
        load_ui(
            "MainWindow.ui",
            base_instance=self,
            custom_widgets=[CustomWidget(MessageTable, wormhole=wormhole)],
        )

        if platform.system() == "Windows":
            self.setStyleSheet(WIN_STYLESHEET)

        self.wormhole = wormhole

        self._hide_error()
        self.show()

    def run(self):
        self.connect_dialog = ConnectDialog(self, self.wormhole)
        self.save_file_dialog = SaveFileDialog(self)

        self.message_edit.returnPressed.connect(self.send_message_button.clicked)
        self.send_message_button.clicked.connect(self._on_send_message_button)
        self.send_files_button.clicked.connect(self._on_send_files_button)
        self.message_table.send_file.connect(self._on_send_file)

        self.connect_dialog.rejected.connect(self.close)

        self.save_file_dialog.finished.connect(self._on_save_file_dialog_finished)

        s = self.wormhole.signals
        s.wormhole_open.connect(self._hide_error)
        s.message_sent.connect(self._on_message_sent)
        s.message_received.connect(self._on_message_received)
        s.file_receive_pending.connect(self._on_file_receive_pending)
        s.file_transfer_progress.connect(self._on_file_transfer_progress)
        s.file_transfer_complete.connect(self._on_file_transfer_complete)
        s.error.connect(self._on_error)
        s.wormhole_shutdown_received.connect(self._on_wormhole_shutdown_received)
        s.wormhole_shutdown.connect(QApplication.quit)

        self.connect_dialog.open()

    def closeEvent(self, event):
        self.wormhole.signals.error.disconnect(self._on_error)
        self.wormhole.shutdown()

    @Slot()
    def _on_send_message_button(self):
        self._disable_message_entry()
        self.wormhole.send_message(self.message_edit.text())

    @Slot()
    def _on_send_files_button(self):
        dialog = QFileDialog(self, "Send")
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.filesSelected.connect(self._on_send_files_selected)
        dialog.open()

    @Slot(str)
    def _on_send_files_selected(self, filepaths):
        for filepath in filepaths:
            self.message_table.send_file_pending(filepath)

    @Slot(int, str)
    def _on_send_file(self, id, filepath):
        self.wormhole.send_file(id, filepath)

    @Slot()
    def _on_message_sent(self, success):
        self._enable_message_entry()
        if success:
            message = self.message_edit.text()
            self.message_table.add_sent_message(message)
            self.message_edit.clear()

    @Slot(str)
    def _on_message_received(self, message):
        self.message_table.add_received_message(message)

    @Slot(str, int)
    def _on_file_receive_pending(self, filename, size):
        self.save_file_dialog.open(filename, size)

    @Slot(int)
    def _on_save_file_dialog_finished(self, result):
        if result == QDialog.Accepted:
            id = self.message_table.receiving_file(self.save_file_dialog.filename)
            self.wormhole.receive_file(
                id, self.save_file_dialog.get_destination_directory()
            )
        else:
            self.wormhole.reject_file()

    @Slot(int, int, int)
    def _on_file_transfer_progress(self, id, transferred_bytes, total_bytes):
        self.message_table.transfer_progress(id, transferred_bytes, total_bytes)

    @Slot(int, str)
    def _on_file_transfer_complete(self, id, filename):
        self.message_table.transfer_complete(id, filename)

    @Slot(Exception, str)
    def _on_error(self, exception, traceback):
        logging.error(f"Caught Exception: {repr(exception)}")
        if traceback:
            logging.error(f"Traceback: {traceback}")

        self.error_label.setText(get_error_text(exception))
        self.error_label.show()

        self.wormhole.close()

    @Slot()
    def _hide_error(self):
        self.error_label.hide()

    @Slot()
    def _on_wormhole_shutdown_received(self):
        ShutdownMessage(parent=self).exec_()

    def _disable_message_entry(self):
        self.message_edit.setDisabled(True)
        self.send_message_button.setDisabled(True)

    def _enable_message_entry(self):
        self.message_edit.setEnabled(True)
        self.send_message_button.setEnabled(True)

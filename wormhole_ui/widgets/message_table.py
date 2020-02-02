from collections import OrderedDict
from pathlib import Path

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import QHeaderView, QProgressBar, QTableWidget, QTableWidgetItem


class MessageTable(QTableWidget):
    send_file = Signal(int, str)

    def __init__(self, parent, wormhole):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.NoFocus)

        self._send_files_pending = OrderedDict()
        self._wormhole = wormhole

        self._setup_columns()

    def _setup_columns(self):
        self.setColumnCount(2)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

    def add_sent_message(self, message):
        self._append_item(SendItem(f"You: {message}"))

    def add_received_message(self, message):
        self._append_item(ReceiveItem(message))

    def send_file_pending(self, filepath):
        id = self.rowCount()
        self._send_files_pending[id] = filepath
        self._append_item(SendFile(Path(filepath).name))

        if not self._wormhole.is_sending_file():
            self._send_next_file()

        return id

    def receiving_file(self, filepath):
        id = self.rowCount()
        self._append_item(ReceiveFile(Path(filepath).name))

        return id

    def transfer_progress(self, id, transferred_bytes, total_bytes):
        if not isinstance(self.cellWidget(id, 0), QProgressBar):
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setMaximumWidth(32)
            self.setCellWidget(id, 0, bar)

        if total_bytes == 0:
            percent = 100
        else:
            percent = (100 * transferred_bytes) // total_bytes

        self.cellWidget(id, 0).setValue(percent)

    def transfer_complete(self, id, filename):
        self.item(id, 1).transfer_complete(filename)

        if not self._wormhole.is_sending_file():
            self._send_next_file()

    def _send_next_file(self):
        if self._send_files_pending:
            id, filepath = self._send_files_pending.popitem(last=False)
            self.item(id, 1).transfer_started()
            self.send_file.emit(id, filepath)

    def _append_item(self, item):
        item.setFlags(Qt.ItemIsEnabled)
        id = self.rowCount()
        self.insertRow(id)
        self.setItem(id, 1, item)
        self.resizeRowsToContents()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet("background-color: rgba(51, 153, 255, 0.2);")
            event.accept()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()

    def dropEvent(self, event):
        self.setStyleSheet("")
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()

            for url in event.mimeData().urls():
                self.send_file_pending(url.toLocalFile())


class ReceiveItem(QTableWidgetItem):
    pass


class SendItem(QTableWidgetItem):
    def __init__(self, message):
        super().__init__(message)

        font = self.font()
        font.setItalic(True)
        self.setFont(font)


class ReceiveFile(ReceiveItem):
    def __init__(self, filename):
        self._filename = filename
        super().__init__(f"Receiving {self._filename}...")

    def transfer_complete(self, filename):
        self._filename = filename
        self.setText(f"Received {filename}")


class SendFile(SendItem):
    def __init__(self, filename):
        self._filename = filename
        super().__init__(f"Queued {self._filename}...")

    def transfer_started(self):
        self.setText(f"Sending {self._filename}...")

    def transfer_complete(self, filename):
        self._filename = filename
        self.setText(f"Sent {filename}")

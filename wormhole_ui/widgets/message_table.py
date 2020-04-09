from collections import OrderedDict
from pathlib import Path

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PySide2.QtSvg import QSvgWidget

from ..util import RESOURCES_PATH

ICON_COLUMN = 0
TEXT_COLUMN = 1
ICON_COLUMN_WIDTH = 32


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
        header.setSectionResizeMode(ICON_COLUMN, QHeaderView.Fixed)
        header.setSectionResizeMode(TEXT_COLUMN, QHeaderView.Stretch)
        header.resizeSection(ICON_COLUMN, ICON_COLUMN_WIDTH)

    def add_sent_message(self, message):
        self._append_item(SendItem(f"Sent: {message}"))

    def add_received_message(self, message):
        self._append_item(ReceiveItem(message))

    def send_file_pending(self, filepath):
        id = self.rowCount()
        self._send_files_pending[id] = filepath
        self._append_item(SendFile(Path(filepath).name))
        self._draw_progress(id, 0)

        if not self._wormhole.is_sending_file():
            self._send_next_file()

        return id

    def receiving_file(self, filepath):
        id = self.rowCount()
        item = ReceiveFile(Path(filepath).name)
        item.transfer_started()
        self._append_item(item)
        self._draw_progress(id, 0)

        return id

    def transfer_progress(self, id, transferred_bytes, total_bytes):
        if total_bytes == 0:
            percent = 100
        else:
            percent = (100 * transferred_bytes) // total_bytes
        self._draw_progress(id, percent)

    def transfer_complete(self, id, filename):
        self.item(id, TEXT_COLUMN).transfer_complete(filename)
        self._draw_icon(id, "check.svg")

        if not self._wormhole.is_sending_file():
            self._send_next_file()

    def transfers_failed(self):
        for id in range(self.rowCount()):
            item = self.item(id, TEXT_COLUMN)
            if item.in_progress:
                item.transfer_failed()
                self._draw_icon(id, "times.svg")

    def _send_next_file(self):
        if self._send_files_pending:
            id, filepath = self._send_files_pending.popitem(last=False)
            self.item(id, TEXT_COLUMN).transfer_started()
            self.send_file.emit(id, filepath)

    def _append_item(self, item):
        item.setFlags(Qt.ItemIsEnabled)
        id = self.rowCount()
        self.insertRow(id)
        self.setItem(id, TEXT_COLUMN, item)
        self.resizeRowsToContents()

    def _draw_progress(self, id, percent):
        if self.cellWidget(id, ICON_COLUMN) is None:
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedSize(ICON_COLUMN_WIDTH, self.rowHeight(id))

            self.setCellWidget(id, ICON_COLUMN, bar)

        if isinstance(self.cellWidget(id, ICON_COLUMN), QProgressBar):
            self.cellWidget(id, ICON_COLUMN).setValue(percent)

    def _draw_icon(self, id, svg_filename):
        svg = QSvgWidget(str(RESOURCES_PATH / svg_filename))
        height = self.cellWidget(id, ICON_COLUMN).size().height()
        svg.setFixedSize(height, height)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(svg)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)

        self.setCellWidget(id, ICON_COLUMN, container)

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
    def __init__(self, message):
        super().__init__(message)
        self.in_progress = False


class SendItem(QTableWidgetItem):
    def __init__(self, message):
        super().__init__(message)
        self.in_progress = False

        font = self.font()
        font.setItalic(True)
        self.setFont(font)


class ReceiveFile(ReceiveItem):
    def __init__(self, filename):
        self.in_progress = False
        self._filename = filename
        super().__init__(f"Queued: {self._filename}...")

    def transfer_started(self):
        self.in_progress = True
        self.setText(f"Receiving: {self._filename}...")

    def transfer_complete(self, filename):
        self.in_progress = False
        self._filename = filename
        self.setText(f"Received: {filename}")

    def transfer_failed(self):
        self.in_progress = False
        self.setText(f"Failed to receive {self._filename}")


class SendFile(SendItem):
    def __init__(self, filename):
        self.in_progress = False
        self._filename = filename
        super().__init__(f"Queued: {self._filename}...")

    def transfer_started(self):
        self.in_progress = True
        self.setText(f"Sending: {self._filename}...")

    def transfer_complete(self, filename):
        self.in_progress = False
        self._filename = filename
        self.setText(f"Sent: {filename}")

    def transfer_failed(self):
        self.in_progress = False
        self.setText(f"Failed to send {self._filename}")

from PySide2.QtWidgets import QMessageBox

MIN_WIDTH = 450
MIN_HEIGHT = 120


class ShutdownMessage(QMessageBox):
    def exec_(self):
        self.setText("The remote computer has closed the connection.")
        self.setIcon(QMessageBox.Information)
        self.setStandardButtons(QMessageBox.Close)
        self.setDefaultButton(QMessageBox.Close)
        super().exec_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() < MIN_WIDTH:
            self.setFixedWidth(MIN_WIDTH)
        if self.height() < MIN_HEIGHT:
            self.setFixedHeight(MIN_HEIGHT)

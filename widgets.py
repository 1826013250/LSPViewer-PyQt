from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel


class PixmapLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = None
        self.previous_width = self.width()
        self.previous_height = self.height()

    def paintEvent(self, event):
        if self.original_pixmap is not None and \
                    (self.previous_height != self.height() or self.previous_width != self.width()):
            self.previous_height = self.height()
            self.previous_width = self.width()
            self.setPixmap(self.original_pixmap.scaled(QSize(self.size().width() - 10, self.size().height() - 10),
                                                       Qt.AspectRatioMode.KeepAspectRatio,
                                                       Qt.TransformationMode.SmoothTransformation))
        super().paintEvent(event)

    def set_original_pixmap(self, original_pixmap: QPixmap | None):
        self.original_pixmap = original_pixmap
        if self.original_pixmap is not None:
            self.setPixmap(original_pixmap.scaled(QSize(self.size().width() - 10, self.size().height() - 10),
                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))

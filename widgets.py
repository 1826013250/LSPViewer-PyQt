from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QListView, \
    QProgressBar, QHBoxLayout, QRadioButton


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


class TaskViewWindow(QWidget):
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.__init_widgets()
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_list)
        self.timer.start()
        self.selection = "all"
        self.setWindowTitle("Task Viewer")

    def __init_widgets(self):
        self.label = QLabel("Here's the running tasks:")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.label)

        self.list = QListWidget()
        self.layout().addWidget(self.list)

        self.btn_layout = QHBoxLayout()
        self.radio_all = QRadioButton("All")
        self.radio_all.setChecked(True)
        self.radio_all.toggled.connect(self.update_radio_selection)
        self.radio_get = QRadioButton("View")
        self.radio_get.toggled.connect(self.update_radio_selection)
        self.radio_save = QRadioButton("Save")
        self.radio_save.toggled.connect(self.update_radio_selection)
        self.btn_killall = QPushButton("Send KILL signal")
        self.btn_killall.clicked.connect(self.kill_task)
        self.btn_layout.addWidget(self.radio_all)
        self.btn_layout.addWidget(self.radio_get)
        self.btn_layout.addWidget(self.radio_save)
        self.btn_layout.addWidget(self.btn_killall)
        self.layout().addLayout(self.btn_layout)

    def update_radio_selection(self, event):
        if self.radio_all.isChecked():
            self.selection = "all"
        if self.radio_get.isChecked():
            self.selection = "fetch"
        if self.radio_save.isChecked():
            self.selection = "download"

    def kill_task(self):
        self.mainwindow.term_signal.emit(self.selection)

    def update_list(self):
        self.list.clear()
        progresses = self.mainwindow.progresses_getimage
        progresses.update(self.mainwindow.progresses_saveimage)
        for k, v in progresses.items():
            item = QListWidgetItem((k + (" " * 10))[:10])
            self.list.addItem(item)
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setDisabled(True)
            progress.setValue(int(v))
            self.list.setItemWidget(item, progress)


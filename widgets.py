from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, \
    QProgressBar, QHBoxLayout, QRadioButton, QDialog, QTabWidget, QGridLayout, QLineEdit, QSizePolicy, QFileDialog, \
    QMessageBox, QButtonGroup
from functools import partial


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


class ReadOnlyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def contextMenuEvent(self, event):
        event.ignore()

    def keyPressEvent(self, e):
        if (e.text() or e.key() == Qt.Key.Key_Backspace or
                (e.modifiers() == Qt.KeyboardModifier.ControlModifier and e.key() == Qt.Key.Key_X)):
            e.ignore()
        else:
            super().keyPressEvent(e)


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

    def update_radio_selection(self):
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
        progresses = self.mainwindow.progresses_getimage.copy()
        progresses.update(self.mainwindow.progresses_saveimage.copy())
        for k, v in progresses.items():
            item = QListWidgetItem((k + (" " * 10))[:10] + " - %.2f%%" % v)
            self.list.addItem(item)
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setDisabled(True)
            progress.setValue(int(v))
            self.list.setItemWidget(item, progress)


class SettingsDialog(QDialog):
    def __init__(self, configs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setLayout(QVBoxLayout())
        self.tab_widget = QTabWidget()
        self.layout().addWidget(self.tab_widget)
        self.configs = configs.copy()
        self.mainwindow = parent
        self.__init_widgets()

        self.close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        self.close_shortcut.activated.connect(self.close)

    def __init_widgets(self):
        self.download_settings = QWidget()
        self.tab_widget.addTab(self.download_settings, "Images")
        self.download_settings.setLayout(QGridLayout())
        label_save_directory = QLabel("Save Directory:")
        label_save_directory.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        label_save_directory.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.download_settings.layout().addWidget(label_save_directory, 0, 0)
        file_selection_layout = QHBoxLayout()
        self.directory_text = ReadOnlyLineEdit()
        self.directory_text.setText(self.configs["save_dir"])
        self.directory_text.textChanged.connect(self.update_configs_directory)
        file_selection_layout.addWidget(self.directory_text)
        directory_select_btn = QPushButton("Select...")
        directory_select_btn.clicked.connect(self.select_directory)
        directory_select_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        file_selection_layout.addWidget(directory_select_btn)
        self.download_settings.layout().addLayout(file_selection_layout, 0, 1)

        label_r18 = QLabel("R18 State:")
        label_r18.setAlignment(Qt.AlignmentFlag.AlignRight)
        btn_group_r18 = QButtonGroup()
        self.r18_radiobuttons = {
            0: QRadioButton("Off"),
            1: QRadioButton("On"),
            2: QRadioButton("Random")
        }
        self.r18_radiobuttons[self.configs["r18"]].setChecked(True)
        for btn in self.r18_radiobuttons.values():
            btn_group_r18.addButton(btn)
        btn_r18_layout = QHBoxLayout()
        for btn in self.r18_radiobuttons.values():
            btn_r18_layout.addWidget(btn)
        for btn in self.r18_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, 'r18'))
        self.download_settings.layout().addWidget(label_r18, 1, 0)
        self.download_settings.layout().addLayout(btn_r18_layout, 1, 1)

        label_ai = QLabel("Exclude AI works:")
        label_ai.setAlignment(Qt.AlignmentFlag.AlignRight)
        btn_group_r18 = QButtonGroup()
        self.r18_radiobuttons = {
            0: QRadioButton("Off"),
            1: QRadioButton("On"),
            2: QRadioButton("Random")
        }
        self.r18_radiobuttons[self.configs["r18"]].setChecked(True)
        for btn in self.r18_radiobuttons.values():
            btn_group_r18.addButton(btn)
        btn_r18_layout = QHBoxLayout()
        for btn in self.r18_radiobuttons.values():
            btn_r18_layout.addWidget(btn)
        for btn in self.r18_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, 'r18'))
        self.download_settings.layout().addWidget(label_r18, 1, 0)
        self.download_settings.layout().addLayout(btn_r18_layout, 1, 1)

        label_view_quality = QLabel("View Quality:")
        label_view_quality.setAlignment(Qt.AlignmentFlag.AlignRight)
        btn_group_1 = QButtonGroup()
        self.view_quality_radiobuttons = {
            "mini": QRadioButton("Pooh"),
            "thumb": QRadioButton("Low"),
            "small": QRadioButton("Medium"),
            "regular": QRadioButton("High"),
            "original": QRadioButton("Original")
        }
        self.view_quality_radiobuttons[self.configs["view_quality"]].setChecked(True)
        for btn in self.view_quality_radiobuttons.values():
            btn_group_1.addButton(btn)
        btn_layout_1 = QHBoxLayout()
        for btn in self.view_quality_radiobuttons.values():
            btn_layout_1.addWidget(btn)
        for btn in self.view_quality_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, "view"))
        self.download_settings.layout().addWidget(label_view_quality, 3, 0)
        self.download_settings.layout().addLayout(btn_layout_1, 3, 1)

        label_save_quality = QLabel("Save Quality:")
        label_save_quality.setAlignment(Qt.AlignmentFlag.AlignRight)
        btn_group_2 = QButtonGroup()
        self.save_quality_radiobuttons = {
            "mini": QRadioButton("Pooh"),
            "thumb": QRadioButton("Low"),
            "small": QRadioButton("Medium"),
            "regular": QRadioButton("High"),
            "original": QRadioButton("Original")
        }
        self.save_quality_radiobuttons[self.configs["save_quality"]].setChecked(True)
        for btn in self.save_quality_radiobuttons.values():
            btn_group_2.addButton(btn)
        btn_layout_2 = QHBoxLayout()
        for btn in self.save_quality_radiobuttons.values():
            btn_layout_2.addWidget(btn)
        for btn in self.save_quality_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, "save"))
        self.download_settings.layout().addWidget(label_save_quality, 4, 0)
        self.download_settings.layout().addLayout(btn_layout_2, 4, 1)

    def radiobutton_change(self, type_):
        if type_ == "view":
            for k, v in self.view_quality_radiobuttons.items():
                if v.isChecked():
                    self.configs["view_quality"] = k
        if type_ == "save":
            for k, v in self.save_quality_radiobuttons.items():
                if v.isChecked():
                    self.configs["save_quality"] = k
        if type_ == "r18":
            for k, v in self.r18_radiobuttons.items():
                if v.isChecked():
                    self.configs["r18"] = k

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.directory_text.setText(directory)

    def update_configs_directory(self):
        self.configs["save_dir"] = self.directory_text.text()
        print(self.configs["save_dir"])

    def closeEvent(self, event):
        if self.configs != self.mainwindow.configs:
            r = QMessageBox.warning(self, "Warning", "You have unsaved changes.\nSave them?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |
                                    QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Yes:
                self.save_changes()
            elif r == QMessageBox.StandardButton.No:
                pass
            elif r == QMessageBox.StandardButton.Cancel:
                return event.ignore()
        super().closeEvent(event)

    def save_changes(self):
        self.mainwindow.term_signal.emit("fetch")
        self.mainwindow.images.clear()
        self.mainwindow.image_data.clear()
        self.mainwindow.configs = self.config


class WaitForTaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Waiting...")
        self.mainwindow = parent
        self.setLayout(QVBoxLayout())
        label = QLabel("Waiting for the running tasks...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(label)
        self.task_finished = False
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.detect_tasks)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(300, 70)

    def closeEvent(self, event):
        if self.task_finished:
            return super().closeEvent(event)
        event.ignore()

    def keyPressEvent(self, a0):
        a0.ignore()

    def detect_tasks(self):
        self.mainwindow.term_signal.emit("all")
        if not (self.mainwindow.progresses_getimage or self.mainwindow.progresses_saveimage or
                self.mainwindow.getting_url):
            self.task_finished = True
            self.close()

import sys

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, \
    QProgressBar, QHBoxLayout, QRadioButton, QDialog, QTabWidget, QGridLayout, QLineEdit, QSizePolicy, QFileDialog, \
    QMessageBox, QButtonGroup, QSlider, QSpinBox, QTableWidget, QTableWidgetItem
from PyQt6.uic import loadUi
from functools import partial
from os.path import join as p_join


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
    def __init__(self, parent=None, path='.'):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setLayout(QVBoxLayout())
        self.tab_widget = QTabWidget()
        self.layout().addWidget(self.tab_widget)
        self.mainwindow = parent
        self.configs = self.mainwindow.configs.copy()
        self.configs["authors"] = self.mainwindow.configs["authors"].copy()
        self.configs["tag"] = self.mainwindow.configs["tag"].copy()
        self.add_author_dialog = AddAuthorDialog(path)
        self.__init_widgets()
        self.restore_status = False
        self.restore_widget_status()

        self.close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        self.close_shortcut.activated.connect(self.close)

    def __init_widgets(self):
        self.image_settings = QWidget()  # Image/ Download settings tag container
        self.tab_widget.addTab(self.image_settings, "Images")  # add tag
        self.image_settings.setLayout(QGridLayout())  # set layout
        self.image_settings.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.label_save_directory = QLabel("Save Directory:")  # Save destination
        self.label_save_directory.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.label_save_directory.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.image_settings.layout().addWidget(self.label_save_directory, 0, 0)
        self.file_selection_layout = QHBoxLayout()
        self.directory_text = ReadOnlyLineEdit()
        self.file_selection_layout.addWidget(self.directory_text)
        self.directory_select_btn = QPushButton("Select...")
        self.directory_select_btn.clicked.connect(self.select_directory)
        self.directory_select_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.file_selection_layout.addWidget(self.directory_select_btn)
        self.image_settings.layout().addLayout(self.file_selection_layout, 0, 1)

        self.label_r18 = QLabel("R18 State (Sorted by API):")  # R18 State RadioButtons
        self.label_r18.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.btn_group_r18 = QButtonGroup()
        self.r18_radiobuttons = {
            0: QRadioButton("Off"),
            1: QRadioButton("On"),
            2: QRadioButton("Random")
        }
        for btn in self.r18_radiobuttons.values():
            self.btn_group_r18.addButton(btn)
        self.btn_r18_layout = QHBoxLayout()
        for btn in self.r18_radiobuttons.values():
            self.btn_r18_layout.addWidget(btn)
        for btn in self.r18_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, 'r18'))
        self.image_settings.layout().addWidget(self.label_r18, 1, 0)
        self.image_settings.layout().addLayout(self.btn_r18_layout, 1, 1)

        self.ai_exclude_label = QLabel("Exclude AI works:")  # Exclude AI works radiobuttons
        self.ai_exclude_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.btn_group_ai = QButtonGroup()
        self.ex_ai_radiobuttons = {
            0: QRadioButton("No"),
            1: QRadioButton("Yes")
        }
        for btn in self.ex_ai_radiobuttons.values():
            self.btn_group_ai.addButton(btn)
        for btn in self.ex_ai_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, 'ex_ai'))
        self.btn_ai_layout = QHBoxLayout()
        for btn in self.ex_ai_radiobuttons.values():
            self.btn_ai_layout.addWidget(btn)
        self.image_settings.layout().addWidget(self.ai_exclude_label, 2, 0)
        self.image_settings.layout().addLayout(self.btn_ai_layout, 2, 1)

        self.label_view_quality = QLabel("View Quality:")  # View & Save Quality radiobuttons
        self.label_view_quality.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.btn_group_1 = QButtonGroup()
        self.view_quality_radiobuttons = {
            "mini": QRadioButton("Poop"),
            "thumb": QRadioButton("Low"),
            "small": QRadioButton("Medium"),
            "regular": QRadioButton("High"),
            "original": QRadioButton("Original")
        }
        for btn in self.view_quality_radiobuttons.values():
            self.btn_group_1.addButton(btn)
        self.btn_layout_1 = QHBoxLayout()
        for btn in self.view_quality_radiobuttons.values():
            self.btn_layout_1.addWidget(btn)
        for btn in self.view_quality_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, "view"))
        self.image_settings.layout().addWidget(self.label_view_quality, 3, 0)
        self.image_settings.layout().addLayout(self.btn_layout_1, 3, 1)

        self.label_save_quality = QLabel("Save Quality:")
        self.label_save_quality.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.btn_group_2 = QButtonGroup()
        self.save_quality_radiobuttons = {
            "mini": QRadioButton("Poop"),
            "thumb": QRadioButton("Low"),
            "small": QRadioButton("Medium"),
            "regular": QRadioButton("High"),
            "original": QRadioButton("Original")
        }
        for btn in self.save_quality_radiobuttons.values():
            self.btn_group_2.addButton(btn)
        self.btn_layout_2 = QHBoxLayout()
        for btn in self.save_quality_radiobuttons.values():
            self.btn_layout_2.addWidget(btn)
        for btn in self.save_quality_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, "save"))
        self.image_settings.layout().addWidget(self.label_save_quality, 4, 0)
        self.image_settings.layout().addLayout(self.btn_layout_2, 4, 1)

        self.tag_settings = QWidget()  # Tag Settings container
        self.tab_widget.addTab(self.tag_settings, "Tags")
        self.tag_settings.setLayout(QHBoxLayout())
        self.tag_btn_layout = QVBoxLayout()
        self.tags_list = QTableWidget()
        self.tags_list.verticalHeader().hide()
        self.tags_list.itemChanged.connect(self.tags_table_changes)
        self.tags_list.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.tag_settings.layout().addWidget(self.tags_list)
        self.tag_settings.layout().addLayout(self.tag_btn_layout)
        self.tag_add_btn = QPushButton("Add Group")
        self.tag_add_btn.clicked.connect(partial(self.btn_actions, "tag", "add"))
        self.tag_remove_btn = QPushButton("Remove Selected Group")
        self.tag_remove_btn.clicked.connect(partial(self.btn_actions, "tag", "remove"))
        self.tag_remove_all_btn = QPushButton("Remove All")
        self.tag_remove_all_btn.clicked.connect(partial(self.btn_actions, "tag", "remove_all"))
        self.tag_help_btn = QPushButton("Help")
        help_text = "Double click the area below the Groups to add tags.\n" \
                    "Leave a block empty to remove a tag.\n" \
                    "The relationship of each GROUP is \"AND\".\n" \
                    "The relationship of each ITEM in the groups is \"OR\"."
        self.tag_help_btn.clicked.connect(partial(QMessageBox.information, self, "Help", help_text))
        self.tag_btn_layout.addWidget(self.tag_add_btn)
        self.tag_btn_layout.addWidget(self.tag_remove_btn)
        self.tag_btn_layout.addWidget(self.tag_remove_all_btn)
        self.tag_btn_layout.addWidget(self.tag_help_btn)
        self.tag_btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.author_settings = QWidget()  # Set specific authors
        self.author_settings.setLayout(QHBoxLayout())
        self.tab_widget.addTab(self.author_settings, "Authors")
        self.author_list = QListWidget()
        self.author_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.author_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.author_btn_layout = QVBoxLayout()
        self.author_btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.author_btn_add = QPushButton("Add")
        self.author_btn_add.clicked.connect(partial(self.btn_actions, "author", "add"))
        self.author_btn_remove = QPushButton("Remove")
        self.author_btn_remove.clicked.connect(partial(self.btn_actions, "author", "remove"))
        self.author_btn_remove_all = QPushButton("Remove All")
        self.author_btn_remove_all.clicked.connect(partial(self.btn_actions, "author", "remove_all"))
        self.author_btn_layout.addWidget(self.author_btn_add)
        self.author_btn_layout.addWidget(self.author_btn_remove)
        self.author_btn_layout.addWidget(self.author_btn_remove_all)
        self.author_settings.layout().addWidget(self.author_list)
        self.author_settings.layout().addLayout(self.author_btn_layout)

        self.misc_settings = QWidget()  # Others, e.g. cache number...
        self.misc_settings.setLayout(QGridLayout())
        self.misc_settings.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tab_widget.addTab(self.misc_settings, "Misc")
        self.keep_label = QLabel("Number of previous pictures:")  # Previous Pictures limit
        self.keep_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.misc_settings.layout().addWidget(self.keep_label, 0, 0)
        self.keep_layout = QHBoxLayout()
        self.keep_slidebar = QSlider(Qt.Orientation.Horizontal)
        self.keep_slidebar.setRange(0, 20)
        self.keep_slidebar.sliderMoved.connect(partial(self.spinbox_slider_change, "keep"))
        self.keep_layout.addWidget(self.keep_slidebar)
        self.keep_spinbox = QSpinBox()
        self.keep_spinbox.setRange(0, 20)
        self.keep_spinbox.valueChanged.connect(partial(self.spinbox_slider_change, "keep"))
        self.keep_spinbox.setSingleStep(1)
        self.keep_layout.addWidget(self.keep_spinbox)
        self.misc_settings.layout().addLayout(self.keep_layout, 0, 1)

        self.cache_label = QLabel("Number of cache pictures:")  # Cache pictures limit
        self.cache_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.misc_settings.layout().addWidget(self.cache_label, 1, 0)
        self.cache_layout = QHBoxLayout()
        self.cache_slidebar = QSlider(Qt.Orientation.Horizontal)
        self.cache_slidebar.setRange(0, 20)
        self.cache_slidebar.sliderMoved.connect(partial(self.spinbox_slider_change, "cache"))
        self.cache_layout.addWidget(self.cache_slidebar)
        self.cache_spinbox = QSpinBox()
        self.cache_spinbox.setRange(0, 20)
        self.cache_spinbox.valueChanged.connect(partial(self.spinbox_slider_change, "cache"))
        self.cache_spinbox.setSingleStep(1)
        self.cache_layout.addWidget(self.cache_spinbox)
        self.misc_settings.layout().addLayout(self.cache_layout, 1, 1)

        self.suppress_warnings_label = QLabel("Suppress warnings:")  # Suppress warning toggle
        self.suppress_warnings_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.misc_settings.layout().addWidget(self.suppress_warnings_label, 2, 0)
        self.btn_group_suppress_warnings = QButtonGroup()
        self.btn_layout_suppress_warnings = QHBoxLayout()
        self.suppress_warnings_radiobuttons = {
            0: QRadioButton("No"),
            1: QRadioButton("Yes")
        }
        for btn in self.suppress_warnings_radiobuttons.values():
            self.btn_group_suppress_warnings.addButton(btn)
        for btn in self.suppress_warnings_radiobuttons.values():
            self.btn_layout_suppress_warnings.addWidget(btn)
        for btn in self.suppress_warnings_radiobuttons.values():
            btn.clicked.connect(partial(self.radiobutton_change, "suppress"))
        self.misc_settings.layout().addLayout(self.btn_layout_suppress_warnings, 2, 1)

        self.finish_btn_layout = QHBoxLayout()
        self.finish_btn_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(partial(self.close, signal="save"))
        self.ok_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.ok_btn.setDefault(True)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(partial(self.close, signal="dismiss"))
        self.cancel_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.finish_btn_layout.addWidget(self.ok_btn)
        self.finish_btn_layout.addWidget(self.cancel_btn)
        self.layout().addLayout(self.finish_btn_layout)

    def exec(self):
        self.configs = self.mainwindow.configs.copy()
        self.configs["authors"] = self.mainwindow.configs["authors"].copy()
        self.configs["tag"] = self.mainwindow.configs["tag"].copy()
        self.restore_widget_status()
        return super().exec()

    def tags_table_changes(self):
        operated = True
        while operated:
            operated = False
            for col in range(self.tags_list.columnCount()):
                for row in range(self.tags_list.rowCount() - 1):
                    if ((self.tags_list.item(row, col) is None or not self.tags_list.item(row, col).text()) and
                       (self.tags_list.item(row + 1, col) is not None and self.tags_list.item(row + 1, col).text())):
                        self.tags_list.setItem(row, col, self.tags_list.takeItem(row + 1, col))
                        operated = True

        max_row = 0
        for col in range(self.tags_list.columnCount()):
            for row in range(self.tags_list.rowCount()):
                if self.tags_list.item(row, col) is not None and self.tags_list.item(row, col).text():
                    max_row = max(max_row, row + 1)
        self.tags_list.setRowCount(max_row + 1)
        if not self.restore_status:
            tags = []
            for col in range(self.tags_list.columnCount()):
                tag = []
                for row in range(self.tags_list.rowCount()):
                    if self.tags_list.item(row, col) is not None and self.tags_list.item(row, col).text():
                        tag.append(self.tags_list.item(row, col).text())
                tags.append(tag)
            self.configs["tag"] = tags

    def btn_actions(self, type_, action):
        if type_ == "author":
            if action == "add":
                if self.author_list.count() >= 20:
                    return QMessageBox.warning(self, "Warning", "You can only specific up to 20 authors.")
                status = self.add_author_dialog.exec()
                if status:
                    value = self.add_author_dialog.get_data()
                    if value == 'error':
                        QMessageBox.warning(self, "Warning", "Add author failed. Please check the format in the"
                                            "last field.")
                        return self.btn_actions(type_, action)
                    if value["uid"]:
                        for index in range(self.author_list.count()):
                            if value["uid"] == self.author_list.item(index).text().split(" - ")[-1]:
                                return QMessageBox.information(self, "Notice", "The specific uid is already exists.")
                        self.author_list.addItem((f"{value['name']} - " if value['name'] else '') + value['uid'])
                        self.configs['authors'].append([value['uid'], value['name']])
            elif action == "remove":
                items = self.author_list.selectedItems()
                if items:
                    for item in items:
                        index = self.author_list.row(item)
                        self.author_list.takeItem(index)
                        self.configs["authors"].pop(index)
                else:
                    QMessageBox.information(self, "Notice", "You haven't selected any item.")
            elif action == "remove_all":
                self.configs["authors"].clear()
                for index in range(self.author_list.count() - 1, -1, -1):
                    self.author_list.takeItem(index)
        elif type_ == "tag":
            if action == "add":
                self.tags_list.setColumnCount(self.tags_list.columnCount() + 1)
                self.tags_list.setHorizontalHeaderItem(self.tags_list.columnCount() - 1,
                                                       QTableWidgetItem(f"Group {self.tags_list.columnCount()}"))
                if self.tags_list.rowCount() == 0:
                    self.tags_table_changes()
            elif action == "remove":
                cols = set()
                for index in self.tags_list.selectedIndexes():
                    cols.add(index.column())
                for col in reversed(list(cols)):
                    self.tags_list.removeColumn(col)
            elif action == "remove_all":
                self.configs["tag"].clear()
                self.tags_list.setColumnCount(0)
                self.tags_list.setRowCount(0)
                # for col in range(self.tags_list.columnCount() - 1, -1, -1):
                #     self.tags_list.removeColumn(col)

    def radiobutton_change(self, type_):
        if type_ == "view":
            for k, v in self.view_quality_radiobuttons.items():
                if v.isChecked():
                    self.configs["view_quality"] = k
        elif type_ == "save":
            for k, v in self.save_quality_radiobuttons.items():
                if v.isChecked():
                    self.configs["save_quality"] = k
        elif type_ == "r18":
            for k, v in self.r18_radiobuttons.items():
                if v.isChecked():
                    self.configs["r18"] = k
        elif type_ == "ex_ai":
            for k, v in self.ex_ai_radiobuttons.items():
                if v.isChecked():
                    self.configs["ex_ai"] = k
        elif type_ == "suppress":
            for k, v in self.suppress_warnings_radiobuttons.items():
                if v.isChecked():
                    self.configs["suppress_warnings"] = k

    def spinbox_slider_change(self, type_, num):
        if type_ == "keep":
            self.configs["keep_num"] = num
            self.keep_spinbox.setValue(num)
            self.keep_slidebar.setValue(num)
        elif type_ == "cache":
            self.configs["cache_num"] = num
            self.cache_spinbox.setValue(num)
            self.cache_slidebar.setValue(num)

    def restore_widget_status(self):
        self.restore_status = True
        self.r18_radiobuttons[self.configs["r18"]].setChecked(True)
        self.ex_ai_radiobuttons[self.configs["ex_ai"]].setChecked(True)
        self.view_quality_radiobuttons[self.configs["view_quality"]].setChecked(True)
        self.save_quality_radiobuttons[self.configs["save_quality"]].setChecked(True)
        self.suppress_warnings_radiobuttons[self.configs["suppress_warnings"]].setChecked(True)
        self.directory_text.setText(self.configs["save_dir"])
        self.spinbox_slider_change("keep", self.configs["keep_num"])
        self.spinbox_slider_change("cache", self.configs["cache_num"])
        self.tags_list.clear()
        self.tags_list.setColumnCount(0)
        self.tags_list.setRowCount(0)
        for i, v in enumerate(self.configs["tag"]):
            self.tags_list.setColumnCount(self.tags_list.columnCount() + 1)
            self.tags_list.setHorizontalHeaderItem(i, QTableWidgetItem("Group %d" % (i + 1)))
            for j, o in enumerate(v):
                self.tags_list.setRowCount(self.tags_list.rowCount() + 1) if self.tags_list.rowCount() <= j else None
                self.tags_list.setItem(j, i, QTableWidgetItem(o))
        self.author_list.clear()
        for uid, name in self.configs["authors"]:
            if name:
                self.author_list.addItem(f"{name} - {uid}")
            else:
                self.author_list.addItem(uid)
        self.restore_status = False

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.directory_text.setText(directory)
        self.configs["save_dir"] = directory

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
        return super().closeEvent(event)

    def close(self, signal=None):
        if signal == "save":
            self.save_changes()
        elif signal == "dismiss":
            self.configs = self.mainwindow.configs.copy()
        super().close()

    def save_changes(self):
        self.mainwindow.term_signal.emit("fetch")
        self.mainwindow.images.clear()
        self.mainwindow.image_data.clear()
        self.mainwindow.configs = self.configs


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


class DetailDialog(QDialog):
    def __init__(self, parent=None, path=None, data=None):
        super().__init__(parent)
        loadUi(p_join(path, "dialog.ui"), self)
        self.data = data
        self.shortcut = QShortcut(QKeySequence("Space"), self)
        self.shortcut.activated.connect(self.close)

    def exec(self, data=None):
        if data is not None:
            self.data = data
        self.update_information()
        super().exec()

    def update_information(self):
        self.title_pid.setText(f"{self.data['title']} - {self.data['pid']}")
        self.author_uid.setText(f"{self.data['author']} - {self.data['uid']}")
        self.tags.setText(f"{', '.join(self.data['tags'])}")
        self.is_ai.setText({0: "Yes" if include_list(["AI", "AI 画作", "NovelAI"], self.data['tags']) else "Unknown",
                            1: "No", 2: "Yes"}[self.data["ai_type"]])
        self.is_r18.setText("Yes" if "R-18" in self.data["tags"] else "No")
        self.links.setText(', '.join([f'<a href={url}>{type_}</a>' for type_, url in self.data["url"].items()]))
        self.pixiv_link.setText(f"<a href=https://www.pixiv.net/artworks/{self.data['pid']}#{self.data['p']}>Open</a>")


def include_list(iter_target, iter_dest):
    include = False
    for i in iter_target:
        if i in iter_dest:
            include = True
    return include


class AddAuthorDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        loadUi(p_join(path, "add_author.ui"), self)

    def exec(self):
        self.uid.clear()
        self.name.clear()
        self.full.clear()
        self.uid.setFocus()
        return super().exec()

    def get_data(self):
        if self.full.text():
            try:
                name, uid = self.full.text().split(" - ")
                return {"uid": uid, "name": name}
            except ValueError:
                return "error"
        return {"uid": self.uid.text(), "name": self.name.text()}


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QPushButton
    app = QApplication(sys.argv)
    btn = QPushButton("push")
    dialog = AddAuthorDialog(".")
    btn.clicked.connect(lambda: (print(dialog.exec()), print(dialog.get_data())))
    btn.show()
    app.exec()

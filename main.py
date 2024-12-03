import sys
from uuid import uuid4
from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QMessageBox)
from os.path import join as p_join, dirname
from sys import platform

from widgets import PixmapLabel, TaskViewWindow, SettingsDialog, WaitForTaskDialog, DetailDialog
from configs import load_config, save_settings
from threads import GetPictureURLsWorker, DownloaderWorker


PATH = dirname(__file__)


class MainWindow(QMainWindow):  # MainWindow class definition
    term_signal = pyqtSignal(str)
    update_image_urls_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.configs = load_config(p_join(PATH), self)
        self.setWindowIcon(QIcon(p_join(PATH, 'favicon.ico')))  # Set window icon

        self.setWindowTitle('LSP Viewer')
        self.container = QWidget(self)  # Container Widget
        self.setCentralWidget(self.container)
        self.container.setLayout(QVBoxLayout())
        self.container.layout().setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignTop)

        self.menubar = self.menuBar()  # Get Menubar
        self.statusbar = self.statusBar()  # Get Statusbar

        self.resize(500, 650)

        self.thread_pool = QThreadPool()
        self.thread_pool_for_save = QThreadPool()

        self.images = []  # A List for storing QPixmap
        self.image_data = []  # A List for storing picture download URL
        self.previous_images = []
        self.previous_image_index = 0
        self.current_image = None  # Current displaying image variable
        self.getting_url = False  # A flag for checking whether the GET URL THREAD is running
        self.progresses_getimage = {}
        self.progresses_saveimage = {}

        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh_image)
        self.timer.start()

        self.task_viewer = TaskViewWindow(self)
        self.settings_dialog = SettingsDialog(self.configs, self)
        self.close_waiter = WaitForTaskDialog(self)
        self.detail_dialog = DetailDialog(self, PATH)

        self.__init_widgets()
        self.__init_menubar()

    def __init_widgets(self):
        self.image = PixmapLabel(self)
        self.image.setText("Here shows images.")
        self.image.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image.setStatusTip("Here showing the images. If no images present the only text displays.")
        self.container.layout().addWidget(self.image)

        self.button_layout = QHBoxLayout()
        self.button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.btn_prev = QPushButton('<<Previous')
        self.btn_prev.setStatusTip("Display the previous image.")
        self.btn_prev.clicked.connect(self.get_previous_image)
        self.btn_prev.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.btn_save = QPushButton('Save')
        self.btn_save.setStatusTip("Save the image into the targeted directory.")
        self.btn_save.clicked.connect(self.save_image)
        self.btn_save.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.btn_next = QPushButton('Next>>')
        self.btn_next.setStatusTip("Display the next image.")
        self.btn_next.clicked.connect(self.get_images)
        self.btn_next.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.button_layout.addWidget(self.btn_prev)
        self.button_layout.addWidget(self.btn_save)
        self.button_layout.addWidget(self.btn_next)
        self.container.layout().addLayout(self.button_layout)

    def __init_menubar(self):
        self.file_menu = self.menubar.addMenu('&File')
        self.function_menu = self.menubar.addMenu('F&unction')

        self.action_save = QAction('&Save', self)
        self.action_save.setShortcut('Ctrl+S')
        self.action_save.setStatusTip('Save the image into the targeted directory.')
        self.action_save.triggered.connect(self.save_image)
        self.file_menu.addAction(self.action_save)

        self.file_menu.addSeparator()

        self.action_previous = QAction('&Previous', self)
        self.action_previous.setShortcut(Qt.Key.Key_Left)
        self.action_previous.setStatusTip('Display the previous image.')
        self.action_previous.triggered.connect(self.get_previous_image)
        self.file_menu.addAction(self.action_previous)

        self.action_next = QAction('&Next', self)
        self.action_next.setShortcut(Qt.Key.Key_Right)
        self.action_next.setStatusTip('Display the next image.')
        self.action_next.triggered.connect(self.get_images)
        self.file_menu.addAction(self.action_next)

        self.action_detail = QAction('&Check image details', self)
        self.action_detail.setShortcut(Qt.Key.Key_Space)
        self.action_detail.setStatusTip('Display the details of the image.')
        self.action_detail.triggered.connect(self.show_detail)
        self.file_menu.addAction(self.action_detail)

        self.action_show_task_view = QAction("Show TaskViewer", self)
        self.action_show_task_view.setShortcut('Ctrl+T')
        self.action_show_task_view.triggered.connect(self.task_viewer.show)
        self.function_menu.addAction(self.action_show_task_view)

        settings_name = "Preference" if platform == "darwin" else "Settings"
        self.action_show_settings_dialog = QAction(settings_name, self)
        self.action_show_settings_dialog.triggered.connect(self.settings_dialog.exec)
        self.function_menu.addAction(self.action_show_settings_dialog)

    def closeEvent(self, a0):
        if self.progresses_saveimage:
            r = QMessageBox.warning(self, 'Warning', 'There are Saving work in the background.\n'
                                    'Are you sure to exit now?',
                                    QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes,
                                    QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.No:
                return a0.ignore()
        self.task_viewer.close()
        self.close_waiter.timer.start()
        self.close_waiter.exec()
        save_settings(PATH, self.configs)
        super().closeEvent(a0)

    def save_image(self):
        if self.current_image is not None:
            data = self.previous_images[self.previous_image_index][1]
            if self.configs["view_quality"] != self.configs["save_quality"]:
                uid = "Save:" + uuid4().hex
                worker = DownloaderWorker(data, uid, self.configs, "download")
                self.update_progress(uid, 0)
                self.term_signal.connect(worker.signals.terminate)
                worker.signals.progress.connect(self.update_progress)
                worker.signals.error.connect(self.deal_errors)
                worker.signals.stop.connect(self.cleanup_progress)
                worker.signals.finish_download.connect(self.get_image_finished)
                self.thread_pool_for_save.start(worker)
            else:
                data["download"] = True
                self.get_image_finished(self.previous_images[self.previous_image_index][0], 0, data)
            QMessageBox.information(self, "Info", "Started download in the background.\n"
                                    "Filename:\n" +
                                    p_join(self.configs["save_dir"], f'{data["pid"]}-{data["title"]} by'
                                                                     f'{data["author"]}.{data["ext"]}')
                                    )
        else:
            QMessageBox.warning(self, "Warning", "No images present now.")

    def get_images(self):
        if self.images and self.previous_image_index == 0:
            self.previous_images.insert(0, self.images.pop(0))
            self.current_image = self.previous_images[0][0]
            while len(self.previous_images) > self.configs["keep_num"] + 1:
                self.previous_images.pop()
        elif self.previous_image_index > 0:
            self.previous_image_index -= 1
            self.current_image = self.previous_images[self.previous_image_index][0]
        else:
            self.current_image = None
        if self.image_data:
            self.start_download_worker()
        if len(self.image_data) <= self.configs.get('cache_num') and not self.getting_url:
            print("Start GET URL Thread")
            self.getting_url = True
            worker = GetPictureURLsWorker(self.configs, len(self.image_data))
            self.update_image_urls_signal.connect(worker.signals.update_url_count)
            worker.signals.error.connect(self.deal_errors)
            worker.signals.return_urls.connect(self.update_image_urls)
            worker.signals.finish_geturl.connect(self.get_url_finished)
            self.thread_pool.start(worker)

    def get_previous_image(self):
        if self.current_image is None and self.previous_images:
            self.current_image = self.previous_images[self.previous_image_index][0]
        elif self.previous_image_index + 1 >= len(self.previous_images):
            return self.deal_errors("no_previous_pic")
        else:
            self.previous_image_index += 1
            self.current_image = self.previous_images[self.previous_image_index][0]

    def start_download_worker(self):
        while len(self.images) + len(self.progresses_getimage) < self.configs.get('cache_num') and self.image_data:
            uid = uuid4().hex
            worker = DownloaderWorker(self.image_data.pop(0), uid, self.configs)
            self.update_progress(uid, 0)
            self.term_signal.connect(worker.signals.terminate)
            worker.signals.progress.connect(self.update_progress)
            worker.signals.error.connect(self.deal_errors)
            worker.signals.finish_download.connect(self.get_image_finished)
            worker.signals.stop.connect(self.cleanup_progress)
            self.thread_pool.start(worker)

    def update_progress(self, uid, progress):
        if uid[:4] == "Save":
            self.progresses_saveimage[uid] = progress
        else:
            self.progresses_getimage[uid] = progress

    def refresh_image(self):
        if self.current_image:
            self.image.set_original_pixmap(self.current_image)
        elif self.current_image is None and self.images:
            self.previous_images.insert(0, self.images.pop(0))
            self.current_image = self.previous_images[0][0]
        elif self.progresses_getimage:
            self.image.set_original_pixmap(None)
            max_id, max_progress = max(self.progresses_getimage.items(), key=lambda x: x[1])
            self.image.setText("Fastest worker id: %s\nProgress: %.2f%%" % (max_id, max_progress))
        elif self.getting_url:
            self.image.setText("Fetching URLs. Please wait...")
        else:
            self.image.set_original_pixmap(None)
            self.image.setText("Here shows images.")

    def deal_errors(self, error, uid=''):
        if error == "get_url_failed":
            if not self.configs["suppress_warnings"]:
                QMessageBox.warning(self, 'Error', 'There was an error when fetching the urls of pictures.'
                                    '\nPlease check your Internet connection.'
                                    '\nPress the "Next" button to retry.')
            self.getting_url = False
        elif error == "get_pic_failed":
            if not self.configs["suppress_warnings"]:
                QMessageBox.information(self, 'Error', 'There was an error when fetching the pictures.\n'
                                        'Please check your Internet connection.')
            self.cleanup_progress(uid)
        elif error == "save_pic_failed":
            if not self.configs["suppress_warnings"]:
                QMessageBox.warning(self, 'Error', 'There was an error when saving the pictures.'
                                    '\nPlease check your Internet connection and the destination directory.')
            self.cleanup_progress(uid)
        elif error == "no_pic" and not self.configs["suppress_warnings"]:
            QMessageBox.warning(self, 'Error', "There's no picture related to the specific tag(s) or artist(s)."
                                "\nPlease change the tags filter in the settings.")
        elif error == "no_previous_pic" and not self.configs["suppress_warnings"]:
            QMessageBox.warning(self, 'Error', "No more previous picture.")

    def update_image_urls(self, urls):  # Extend the image_url list, then return the current url count to the sub-thread
        self.image_data.extend(urls)
        self.update_image_urls_signal.emit(len(self.image_data))

    def get_url_finished(self):
        self.getting_url = False
        self.start_download_worker()

    def cleanup_progress(self, uid):
        if uid in self.progresses_getimage.keys():
            self.progresses_getimage.pop(uid)
        if uid in self.progresses_saveimage.keys():
            self.progresses_saveimage.pop(uid)

    def get_image_finished(self, pixmap, uid, details):
        if details.get("download"):
            self.cleanup_progress(uid)
            pixmap.save(p_join(self.configs["save_dir"], f'{details["pid"]}-{details["title"]} by'
                                                         f'{details["author"]}.{details["ext"]}'))
        else:
            self.cleanup_progress(uid)
            self.images.append((pixmap, details))
            self.start_download_worker()

    def show_detail(self):
        if self.current_image is None:
            return QMessageBox.warning(self, 'Warning', 'No images present now.')
        self.detail_dialog.exec(self.previous_images[self.previous_image_index][1])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(p_join(PATH, "favicon.ico")))
    window = MainWindow()
    window.show()
    app.exec()

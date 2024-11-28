import sys
from uuid import uuid4
from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QMessageBox)

from widgets import PixmapLabel
from configs import load_config
from threads import GetPictureURLsWorker, DownloaderWorker


class MainWindow(QMainWindow):  # MainWindow class definition
    term_signal = pyqtSignal()
    update_image_urls_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.configs = load_config()

        self.setWindowTitle('LSP Viewer')
        self.container = QWidget(self)  # Container Widget
        self.setCentralWidget(self.container)
        self.container.setLayout(QVBoxLayout())
        self.container.layout().setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignTop)

        self.menubar = self.menuBar()  # Get Menubar
        self.statusbar = self.statusBar()  # Get Statusbar

        self.resize(500, 650)
        self.__init_widgets()

        self.thread_pool = QThreadPool()

        self.images = []  # A List for storing QPixmap
        self.image_urls = []  # A List for storing picture download URL
        self.current_image = None  # Current displaying image variable
        self.getting_url = False  # A flag for checking whether the GET URL THREAD is running
        self.progresses = {}

        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh_image)
        self.timer.start()

    def __init_widgets(self):
        self.image = PixmapLabel(self)
        self.image.setText("Here's Images")
        self.image.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image.setStatusTip("Here showing the images. If no images present the only text displays.")
        self.container.layout().addWidget(self.image)

        self.button_layout = QHBoxLayout()
        self.button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.btn_prev = QPushButton('<<Previous')
        self.btn_prev.setStatusTip("Display the previous image.")
        self.btn_prev.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.btn_save = QPushButton('Save')
        self.btn_save.setStatusTip("Save the image into the targeted directory.")
        self.btn_save.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.btn_next = QPushButton('Next>>')
        self.btn_next.setStatusTip("Display the next image.")
        self.btn_next.clicked.connect(self.get_images)
        self.btn_next.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.button_layout.addWidget(self.btn_prev)
        self.button_layout.addWidget(self.btn_save)
        self.button_layout.addWidget(self.btn_next)
        self.container.layout().addLayout(self.button_layout)

    def get_images(self):
        if self.images:
            self.current_image = self.images.pop(0)
        else:
            self.current_image = None
        if self.image_urls:
            self.start_download_worker()
        if len(self.image_urls) <= self.configs.get('cache_num') and not self.getting_url:
            print("Start GET URL Thread")
            self.getting_url = True
            worker = GetPictureURLsWorker(self.configs, len(self.image_urls))
            self.update_image_urls_signal.connect(worker.signals.update_url_count)
            worker.signals.error.connect(self.deal_errors)
            worker.signals.return_urls.connect(self.update_image_urls)
            worker.signals.finish_geturl.connect(self.get_url_finished)
            self.thread_pool.start(worker)

    def start_download_worker(self):
        while len(self.images) + len(self.progresses) < self.configs.get('cache_num') and self.image_urls:
            print("added")
            uid = uuid4().hex
            worker = DownloaderWorker(self.image_urls.pop(0), uid)
            self.update_progress(uid, 0)
            self.term_signal.connect(worker.signals.terminate)
            worker.signals.progress.connect(self.update_progress)
            worker.signals.error.connect(self.deal_errors)
            worker.signals.finish_download.connect(self.get_image_finished)
            self.thread_pool.start(worker)

    def update_progress(self, uid, progress):
        self.progresses[uid] = progress

    def refresh_image(self):
        if self.current_image:
            self.image.set_original_pixmap(self.current_image)
        elif self.current_image is None and self.images:
            self.current_image = self.images.pop(0)
        elif self.progresses:
            self.image.set_original_pixmap(None)
            max_id, max_progress = max(self.progresses.items(), key=lambda x: x[1])
            self.image.setText("Fastest worker id: %s\nProgress: %.2f%%" % (max_id, max_progress))
        elif self.getting_url:
            self.image.setText("Fetching URLs. Please wait...")
        else:
            self.image.set_original_pixmap(None)
            self.image.setText("Here's images.")

    def deal_errors(self, error):
        if error == "get_url_failed":
            QMessageBox.warning(self, 'Error', 'There was an error when fetching the urls of pictures.'
                                '\nPlease press the "Next" button to retry.')
        elif error == "get_pic_failed":
            QMessageBox.warning(self, 'Error', 'There was an error when fetching the pictures.')
        elif error == "no_pic":
            QMessageBox.warning(self, 'Error', "There's no picture related to the specific tag(s) or artist(s).")

    def update_image_urls(self, urls):  # Extend the image_url list, then return the current url count to the sub-thread
        self.image_urls.extend(urls)
        self.update_image_urls_signal.emit(len(self.image_urls))

    def get_url_finished(self):
        self.getting_url = False
        print(self.image_urls)
        print(len(self.image_urls))
        self.start_download_worker()

    def get_image_finished(self, pixmap, uid):
        if uid in self.progresses.keys():
            self.progresses.pop(uid)
        self.images.append(pixmap)
        self.start_download_worker()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

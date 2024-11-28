from PyQt6.QtCore import QRunnable, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtGui import QPixmap, QImage
from io import BytesIO
from requests import get, post
from time import sleep
from uuid import uuid4


class Signals(QObject):
    progress = pyqtSignal(str, float)
    finish_download = pyqtSignal(QPixmap, str)
    finish_geturl = pyqtSignal()
    return_urls = pyqtSignal(list)
    terminate = pyqtSignal()
    update_url_count = pyqtSignal(int)
    error = pyqtSignal(str)


class GetPictureURLsWorker(QRunnable):
    def __init__(self, configs, curr_url_count):
        super().__init__()
        self.signals = Signals()
        self.configs = configs
        self.curr_url_count = curr_url_count
        self.stop = False
        self.signals.update_url_count.connect(self.update_curr_url_count)

    def update_curr_url_count(self, curr_url_count):
        self.curr_url_count = curr_url_count

    def run(self):
        while self.curr_url_count <= self.configs.get('cache_num'):
            info = post("https://api.lolicon.app/setu/v2",
                        json={
                            'r18': self.configs.get('r18'),
                            'num': 20,
                            'tag': [['萝莉', '女孩子']],
                            'size': 'small'
                        }).json().get("data")
            if not info:
                return self.signals.error.emit("no_pic")
            urls = [{'pid': dic['pid'], 'title': dic['title'], 'uid': dic['uid'], 'author': dic['author'],
                     "tags": dic['tags'], "url": dic['urls']['small']} for dic in info]
            self.signals.return_urls.emit(urls)
            sleep(0.1)
        self.signals.finish_geturl.emit()


class DownloaderWorker(QRunnable):
    def __init__(self, url, uid):
        super().__init__()
        self.signals = Signals()
        self.url = url
        self.stop = False
        self.uuid = uid
        self.signals.terminate.connect(self.terminate)
        self.signals.progress.emit(self.uuid, 0)

    def terminate(self):
        self.stop = True

    def run(self):
        try:
            if self.stop:
                return
            resp = get(self.url['url'], stream=True)
            total = int(resp.headers.get('content-length', -1))
            current = 0
            image = BytesIO()
            if resp.status_code == 404:
                return
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    if self.stop:
                        return
                    current += len(chunk)
                    image.write(chunk)
                    if total > 0:
                        self.signals.progress.emit(self.uuid, current / total * 100)
                sleep(0.01)
        except:
            self.signals.error.emit('get_pic_failed')
            self.signals.terminate.emit()
        else:
            image_raw = image.getvalue()
            if image_raw:
                pixmap = QPixmap.fromImage(QImage.fromData(image.getvalue()))
                return self.signals.finish_download.emit(pixmap, self.uuid)
            self.signals.error.emit('get_pic_failed')
            print(self.url['url'])

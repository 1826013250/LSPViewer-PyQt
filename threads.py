from PyQt6.QtCore import QRunnable, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QImage
from io import BytesIO
from requests import get, post, ConnectionError, ConnectTimeout, exceptions
from time import sleep
from uuid import uuid4


class Signals(QObject):
    progress = pyqtSignal(str, float)
    finish_download = pyqtSignal(QPixmap, str, dict)
    finish_geturl = pyqtSignal()
    return_urls = pyqtSignal(list)
    terminate = pyqtSignal(str)
    stop = pyqtSignal(str)
    update_url_count = pyqtSignal(int)
    error = pyqtSignal(str, str)


class GetPictureURLsWorker(QRunnable):
    def __init__(self, configs, curr_url_count):
        super().__init__()
        self.signals = Signals()
        self.configs = configs
        self.curr_url_count = curr_url_count
        self.stop = False
        self.signals.update_url_count.connect(self.update_curr_url_count)
        self.uuid = uuid4().hex

    def update_curr_url_count(self, curr_url_count):
        self.curr_url_count = curr_url_count

    def run(self):
        while self.curr_url_count <= self.configs.get('cache_num'):
            try:
                info = post("https://api.lolicon.app/setu/v2",
                            json={
                                'r18': self.configs.get('r18'),
                                'num': 20,
                                'tag': self.configs['tag'],
                                'size': ['original', 'regular', 'small', 'thumb', 'mini']
                            }, timeout=5).json().get("data")
            except (ConnectionError, exceptions.ReadTimeout, exceptions.SSLError, exceptions.ChunkedEncodingError):
                return self.signals.error.emit('get_url_failed', self.uuid)
            if not info:
                return self.signals.error.emit("no_pic", self.uuid)
            data = [{'pid': dic['pid'], 'title': dic['title'], 'uid': dic['uid'], 'author': dic['author'],
                     "tags": dic['tags'], "url": dic['urls'], "ext": dic['ext'], "ai_type": dic['aiType'],
                     } for dic in info]
            self.signals.return_urls.emit(data)
            sleep(0.1)
        self.signals.finish_geturl.emit()


class DownloaderWorker(QRunnable):
    def __init__(self, data, uid, configs, type_="fetch"):
        super().__init__()
        self.signals = Signals()
        self.data = data
        self.type = type_
        self.configs = configs
        self.stop = False
        self.uuid = uid
        self.signals.terminate.connect(self.terminate)
        self.signals.progress.emit(self.uuid, 0)

    def terminate(self, type_):
        if type_ == self.type or type_ == "all":
            self.stop = True

    def run(self):
        try:
            if self.stop:
                return self.signals.stop.emit(self.uuid)
            if self.type == 'fetch':
                url = self.data['url'][self.configs["view_quality"]]
            else:
                url = self.data['url'][self.configs["save_quality"]]
            resp = get(url, stream=True, timeout=5)
            total = int(resp.headers.get('content-length', -1))
            current = 0
            image = BytesIO()
            if resp.status_code == 404:
                return self.signals.stop.emit(self.uuid)
            for chunk in resp.iter_content(chunk_size=10240):
                if chunk:
                    if self.stop:
                        return self.signals.stop.emit(self.uuid)
                    current += len(chunk)
                    image.write(chunk)
                    if total > 0:
                        self.signals.progress.emit(self.uuid, current / total * 100)
                sleep(0.01)
        except (ConnectionError, exceptions.SSLError, exceptions.ChunkedEncodingError, exceptions.ReadTimeout):
            if self.type == 'fetch':
                self.signals.error.emit('get_pic_failed', self.uuid)
            elif self.type == 'download':
                self.signals.error.emit('save_pic_failed', self.uuid)
        else:
            image_raw = image.getvalue()
            if image_raw:
                if self.type == 'download':
                    self.data["download"] = True
                pixmap = QPixmap.fromImage(QImage.fromData(image.getvalue()))
                return self.signals.finish_download.emit(pixmap, self.uuid, self.data)
            if self.type == "fetch":
                self.signals.error.emit('get_pic_failed', self.uuid)
            elif self.type == "download":
                self.signals.error.emit('save_pic_failed', self.uuid)
            print(self.data['url'])

from json import load as j_load, dump as j_dump, JSONDecodeError
from os.path import exists, join as p_join
from os import remove
from sys import exit

from PyQt6.QtWidgets import QMessageBox


class DecodeError(Exception):
    ...


def load_config(path, mainwindow):
    if exists(p_join(path, 'settings.json')):
        try:
            with open(p_join(path, "settings.json"), 'r') as f:
                j = j_load(f)
            if verify_settings(j):
                return j
            raise DecodeError
        except (JSONDecodeError, UnicodeDecodeError, DecodeError):
            r = QMessageBox.warning(mainwindow, "Warning", "Settings file is corrupted.\nDelete and re-generate?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.No:
                exit(-1)
            else:
                remove(p_join(path, 'settings.json'))
                return load_config(path, mainwindow)
    else:
        configs = {
            "cache_num": 5,
            "keep_num": 5,
            "view_quality": "small",
            "save_quality": "original",
            "save_dir": p_join(path, "out"),
            "tag": [],
            "r18": 0,
            "ex_ai": 0,
            "suppress_warnings": 0
        }
        with open(p_join(path, "settings.json"), 'w') as f:
            j_dump(configs, f, indent=4)
        return configs


def verify_settings(c):
    if all([x in c.keys() for x in ["cache_num", "keep_num", "view_quality", "save_quality", "save_dir", "tag",
                                    "r18", "ex_ai", "suppress_warnings"]]):
        status = True
        if c["cache_num"] not in range(20):
            status = False
        if c["keep_num"] not in range(20):
            status = False
        if c["view_quality"] not in ["thumb", "mini", "small", "regular", "original"]:
            status = False
        if c["save_quality"] not in ["thumb", "mini", "small", "regular", "original"]:
            status = False
        if c["r18"] not in [0, 1, 2]:
            status = False
        if c["ex_ai"] not in [0, 1]:
            status = False
        if c["suppress_warnings"] not in [0, 1]:
            status = False
        if not exists(c["save_dir"]):
            status = False
        return status
    return False


def save_settings(path, c):
    with open(p_join(path, "settings.json"), 'w') as f:
        j_dump(c, f, indent=4, ensure_ascii=False)

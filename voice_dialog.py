"""Окно каталога и загрузки всех RVC-моделей репозитория niobures/RVC-Models."""
import json
import os
import threading
import urllib.parse
import urllib.request
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QProgressBar, QPushButton, QVBoxLayout)

from entries_dialog import STYLE

BASE_HF_URL = "https://huggingface.co/niobures/RVC-Models/resolve/main/"
CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "rvc_catalog.json")


def safe_folder_name(raw_key):
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in raw_key).strip("_")


def get_character_image(char_key, rvc_dir=None):
    if not char_key or char_key == "default":
        return None
    if rvc_dir is None:
        rvc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "rvc")
    if not os.path.isfile(CATALOG_PATH):
        return None
    try:
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception:
        return None
    item = catalog.get(char_key)
    if not item or not item.get("img"):
        return None
    key = safe_folder_name(f"{item['cat']}_{item['name']}")
    path = os.path.join(rvc_dir, key, os.path.basename(item["img"]))
    return path if os.path.isfile(path) else None


class VoiceDialog(QDialog):
    def __init__(self, capri):
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.capri = capri
        self.setWindowTitle("Капри — полный каталог RVC-голосов")
        self.setStyleSheet(STYLE)

        self.rvc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "rvc")
        os.makedirs(self.rvc_dir, exist_ok=True)

        self.catalog = self._load_catalog()

        lay = QVBoxLayout(self)
        title = QLabel(f"Каталог RVC-голосов ({len(self.catalog)} персонажей)")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 14px;")
        lay.addWidget(title)

        hint = QLabel("Полный каталог из репозитория Hugging Face (rvc-big-ru-voice-pack).\n"
                      "При выборе персонажа можно также сменить внешность Капри на его портрет.")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # Фильтр по категории и поиск
        filter_row = QHBoxLayout()
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("Все категории", "all")
        cats = sorted(list(set(v["cat"] for v in self.catalog.values())))
        for c in cats:
            self.cat_combo.addItem(c, c)
        self.cat_combo.currentIndexChanged.connect(self._populate_characters)
        filter_row.addWidget(self.cat_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск персонажа...")
        self.search_input.textChanged.connect(self._populate_characters)
        filter_row.addWidget(self.search_input)
        lay.addLayout(filter_row)

        # Выбор персонажа
        self.char_combo = QComboBox()
        self.char_combo.currentIndexChanged.connect(self._update_status)
        lay.addWidget(self.char_combo)

        # Блок с информацией о персонаже и предпросмотром портрета
        char_info_row = QHBoxLayout()

        info_col = QVBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #28ff96;")
        self.status_label.setWordWrap(True)
        info_col.addWidget(self.status_label)

        self.avatar_sync_cb = QCheckBox("Менять внешность на картинку персонажа")
        self.avatar_sync_cb.setChecked(bool(self.capri.cfg.get("rvc_change_avatar", True)))
        self.avatar_sync_cb.toggled.connect(self._on_avatar_toggle)
        info_col.addWidget(self.avatar_sync_cb)

        self.reset_avatar_btn = QPushButton("Вернуть внешность Капри (по умолчанию)")
        self.reset_avatar_btn.clicked.connect(self._reset_to_default_capri)
        info_col.addWidget(self.reset_avatar_btn)
        char_info_row.addLayout(info_col, stretch=1)

        # Рамка превью аватарки
        self.preview_frame = QFrame()
        self.preview_frame.setFixedSize(100, 120)
        self.preview_frame.setStyleSheet("background: #0a0612; border: 1px solid #ff2260; border-radius: 6px;")
        preview_lay = QVBoxLayout(self.preview_frame)
        preview_lay.setContentsMargins(2, 2, 2, 2)
        self.preview_lbl = QLabel()
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.preview_lbl.setWordWrap(True)
        preview_lay.addWidget(self.preview_lbl)
        char_info_row.addWidget(self.preview_frame)

        lay.addLayout(char_info_row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        preview_label = QLabel("Тестовая фраза для проверки:")
        lay.addWidget(preview_label)

        self.preview_text = QLineEdit("Привет, чумба! Как звучит этот голос?")
        lay.addWidget(self.preview_text)

        btns = QHBoxLayout()
        self.download_btn = QPushButton("Скачать модель")
        self.download_btn.clicked.connect(self._start_download)
        btns.addWidget(self.download_btn)

        self.listen_btn = QPushButton("Прослушать")
        self.listen_btn.clicked.connect(self._test_voice)
        btns.addWidget(self.listen_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)

        cancel_btn = QPushButton("Закрыть")
        cancel_btn.clicked.connect(self.close)
        btns.addWidget(cancel_btn)

        lay.addLayout(btns)
        self.resize(600, 0)

        self._populate_characters()

    def _load_catalog(self):
        if os.path.isfile(CATALOG_PATH):
            try:
                with open(CATALOG_PATH, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _local_folder(self, item):
        return safe_folder_name(f"{item['cat']}_{item['name']}")

    def _get_local_img(self, item):
        if not item or not item.get("img"):
            return None
        folder = self._local_folder(item)
        local_path = os.path.join(self.rvc_dir, folder, os.path.basename(item["img"]))
        return local_path if os.path.isfile(local_path) else None

    def _is_downloaded(self, item):
        pth_rel = item.get("pth")
        if not pth_rel:
            return True
        folder = self._local_folder(item)
        local_path = os.path.join(self.rvc_dir, folder, os.path.basename(pth_rel))
        return os.path.isfile(local_path)

    def _populate_characters(self):
        self.char_combo.blockSignals(True)
        self.char_combo.clear()

        self.char_combo.addItem("Стандартный голос Капри (без RVC)", "default")

        selected_cat = self.cat_combo.currentData()
        search_query = self.search_input.text().strip().lower()
        cur_model = self.capri.cfg.get("rvc_model", "default")
        active_idx = 0

        for key, item in sorted(self.catalog.items(), key=lambda x: x[0]):
            cat, name = item["cat"], item["name"]
            if selected_cat != "all" and cat != selected_cat:
                continue
            if search_query and search_query not in name.lower() and search_query not in cat.lower():
                continue

            is_down = self._is_downloaded(item)
            has_img = bool(item.get("img"))
            icon_mark = " 🖼" if has_img else ""
            status_mark = " (скачано)" if is_down else ""
            label = f"[{cat}] {name}{icon_mark}{status_mark}"
            self.char_combo.addItem(label, key)
            if key == cur_model:
                active_idx = self.char_combo.count() - 1

        self.char_combo.setCurrentIndex(active_idx)
        self.char_combo.blockSignals(False)
        self._update_status()

    def _update_status(self):
        key = self.char_combo.currentData()
        if not key or key == "default":
            self.status_label.setText("Выбран стандартный синтезатор речи Капри.")
            self.download_btn.setEnabled(False)
            self._set_preview_image(None, label_text="Стандартная\nКапри")
            return

        item = self.catalog.get(key)
        if not item:
            return

        local_img = self._get_local_img(item)
        if self._is_downloaded(item):
            has_pic = "картинка есть" if local_img else ("нет картинки в паке" if not item.get("img") else "картинка не скачана")
            self.status_label.setText(f"Модель скачана ({has_pic}). Готова к работе.")
            self.download_btn.setEnabled(False)
        else:
            self.status_label.setText("Модель ещё не скачана с Hugging Face. Нажми «Скачать модель».")
            self.download_btn.setEnabled(True)

        if local_img:
            self._set_preview_image(local_img)
        elif item.get("img"):
            self._set_preview_image(None, label_text="Портрет в паке\n(скачается)")
        else:
            self._set_preview_image(None, label_text="Нет картинки\nв паке")

    def _set_preview_image(self, img_path, label_text=""):
        if img_path and os.path.isfile(img_path):
            pix = QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(96, 116, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_lbl.setPixmap(scaled)
                self.preview_lbl.setText("")
                return
        self.preview_lbl.setPixmap(QPixmap())
        self.preview_lbl.setText(label_text)

    def _on_avatar_toggle(self, checked):
        self.capri.cfg["rvc_change_avatar"] = bool(checked)
        if hasattr(self.capri, "save_setting"):
            self.capri.save_setting("rvc_change_avatar", bool(checked))

    def _reset_to_default_capri(self):
        self.avatar_sync_cb.setChecked(False)
        self.capri.set_avatar(None)
        QMessageBox.information(self, "Капри", "Внешность возвращена к стандартной Капри.")

    def _download_file(self, rel_path, dest_dir, on_progress=None):
        dest = os.path.join(dest_dir, os.path.basename(rel_path))
        url = BASE_HF_URL + urllib.parse.quote(rel_path)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while chunk := r.read(1 << 16):
                f.write(chunk)
                done += len(chunk)
                if total and on_progress:
                    on_progress(int(done / total * 100))
        return dest

    def _start_download(self):
        key = self.char_combo.currentData()
        item = self.catalog.get(key)
        if not item or not item.get("pth"):
            return

        dest_dir = os.path.join(self.rvc_dir, self._local_folder(item))
        os.makedirs(dest_dir, exist_ok=True)

        self.download_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText(f"Скачиваю: {item['name']}...")

        def run():
            files_to_dl = [item["pth"]]
            if item.get("index"):
                files_to_dl.append(item["index"])
            if item.get("img"):
                files_to_dl.append(item["img"])

            total_files = len(files_to_dl)
            for idx, rel in enumerate(files_to_dl):
                def prog(pct):
                    overall = int(((idx * 100) + pct) / total_files)
                    self.progress.setValue(overall)
                try:
                    self._download_file(rel, dest_dir, on_progress=prog)
                except Exception as e:
                    self.status_label.setText(f"Ошибка загрузки: {e}")
                    self.download_btn.setEnabled(True)
                    self.progress.setVisible(False)
                    return

            self.progress.setVisible(False)
            self.status_label.setText("Модель и картинка успешно загружены!")
            self._populate_characters()

        threading.Thread(target=run, daemon=True).start()

    def _test_voice(self):
        phrase = self.preview_text.text().strip() or "Привет!"
        if hasattr(self.capri, "speaker") and self.capri.speaker:
            threading.Thread(target=lambda: self.capri.speaker.say(phrase), daemon=True).start()

    def _save(self):
        key = self.char_combo.currentData()
        change_avatar = self.avatar_sync_cb.isChecked()
        self.capri.cfg["rvc_change_avatar"] = change_avatar
        if hasattr(self.capri, "save_setting"):
            self.capri.save_setting("rvc_change_avatar", change_avatar)

        if not key or key == "default":
            self.capri.cfg["rvc_model"] = "default"
            if hasattr(self.capri, "save_setting"):
                self.capri.save_setting("rvc_model", "default")
            self.capri.set_avatar(None)
            QMessageBox.information(self, "Капри", "Сохранён стандартный голос и внешность Капри.")
            self.close()
            return

        item = self.catalog.get(key)
        if item and not self._is_downloaded(item):
            QMessageBox.warning(self, "Капри", "Сначала скачай модель кнопкой «Скачать модель».")
            return

        self.capri.cfg["rvc_model"] = key
        if hasattr(self.capri, "save_setting"):
            self.capri.save_setting("rvc_model", key)

        if change_avatar and item and item.get("img"):
            local_img = self._get_local_img(item)
            if not local_img:
                dest_dir = os.path.join(self.rvc_dir, self._local_folder(item))
                os.makedirs(dest_dir, exist_ok=True)
                try:
                    local_img = self._download_file(item["img"], dest_dir)
                except Exception:
                    local_img = None
            if local_img:
                self.capri.set_avatar(local_img)
            else:
                self.capri.set_avatar(None)
        elif not change_avatar:
            self.capri.set_avatar(None)

        QMessageBox.information(self, "Капри", f"Сохранён голос: {self.char_combo.currentText()}")
        self.close()

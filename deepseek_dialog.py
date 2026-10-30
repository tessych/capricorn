"""Окно управления ключом DeepSeek API (меню в трее)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QVBoxLayout)

from entries_dialog import STYLE


class DeepSeekDialog(QDialog):
    def __init__(self, capri):
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.capri = capri
        self.setWindowTitle("Капри — ключ DeepSeek API")
        self.setStyleSheet(STYLE)

        lay = QVBoxLayout(self)
        title = QLabel("Ключ DeepSeek API")
        title.setStyleSheet("color: #28ff96; font-weight: bold;")
        lay.addWidget(title)

        hint = QLabel("Введи ключ API от DeepSeek (начинается с sk-...). Модель: deepseek-chat.\n"
                      "Если ключ задан, Капри будет отвечать через него без необходимости включать Ollama.")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.key_input = QLineEdit(capri.cfg.get("deepseek_api_key", ""))
        self.key_input.setPlaceholderText("sk-...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        lay.addWidget(self.key_input)

        row = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        delete_btn = QPushButton("Удалить ключ")
        cancel_btn = QPushButton("Отмена")

        save_btn.clicked.connect(self._save)
        delete_btn.clicked.connect(self._delete)
        cancel_btn.clicked.connect(self.close)

        row.addWidget(save_btn)
        row.addWidget(delete_btn)
        row.addStretch()
        row.addWidget(cancel_btn)
        lay.addLayout(row)
        self.resize(520, 0)

    def _save(self):
        key = self.key_input.text().strip()
        self.capri.set_deepseek_key(key)
        QMessageBox.information(self, "Капри", "Ключ DeepSeek сохранён." if key else "Ключ DeepSeek очищен.")
        self.close()

    def _delete(self):
        self.capri.set_deepseek_key("")
        self.key_input.setText("")
        QMessageBox.information(self, "Капри", "Ключ DeepSeek удалён.")
        self.close()

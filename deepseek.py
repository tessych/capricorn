"""Ответы на вопросы через DeepSeek API."""
import datetime
import json
import logging
import os
import re
import urllib.error
import urllib.request

from persona import CHARACTER, SPEECH_RULES, user_context

log = logging.getLogger("capri")
API_URL = "https://api.deepseek.com/chat/completions"

SYSTEM = f"""{CHARACTER}

{SPEECH_RULES}
Командами ПК занимается отдельный модуль; если просят то, чего ты сделать не можешь,
скажи, какую команду произнести, например «Капри, открой ютуб»."""


def strip_think(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return re.sub(r"<think>.*", "", text, flags=re.S).strip()


class DeepSeekAI:
    def __init__(self, cfg):
        self.cfg = cfg
        # Fix: support deepseek-chat (1017 snapshot / V3)
        self.model = cfg.get("deepseek_model", "deepseek-chat")
        self.api_key = (cfg.get("deepseek_api_key") or os.environ.get("DEEPSEEK_API_KEY", "")).strip()
        self.history = []

    @property
    def available(self):
        return bool(self.api_key)

    def set_key(self, key):
        self.api_key = (key or "").strip()
        self.cfg["deepseek_api_key"] = self.api_key

    def ask(self, question):
        if not self.available:
            return "Ключ DeepSeek API не задан. Введи его в меню трея или в config.json."
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        self.history.append({"role": "user", "content": question})
        self.history = self.history[-10:]
        messages = [{"role": "system", "content": SYSTEM + "\n" + user_context() + f"\nСейчас {now}."}] + self.history

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
            "stream": False,
        }

        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "CapriAssistant/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            answer = data["choices"][0]["message"]["content"]
            answer = strip_think(answer)
            answer = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", answer)
            answer = re.sub(r"\s+", " ", answer).strip()
        except urllib.error.HTTPError as e:
            self.history.pop()
            if e.code == 401:
                return "Ключ DeepSeek API не подходит. Проверь или замени ключ в настройках."
            if e.code == 402:
                return "На балансе DeepSeek закончились средства."
            if e.code == 429:
                return "Слишком много запросов к DeepSeek, подожди немного."
            log.error("DeepSeek HTTP %d: %s", e.code, e.read().decode("utf-8", "ignore"))
            return "Сервер DeepSeek вернул ошибку, попробуй позже."
        except Exception as e:
            self.history.pop()
            log.exception("DeepSeek error: %s", e)
            return "Не удалось связаться с DeepSeek. Проверь интернет."

        if not answer:
            self.history.pop()
            return "Хм, пустой ответ от DeepSeek. Спроси ещё раз."

        self.history.append({"role": "assistant", "content": answer})
        return answer

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
У тебя есть инструменты для выполнения действий на ПК:
- запуск приложений и браузера (open_app);
- запуск музыки, плейлистов и радио на Spotify, SoundCloud и YouTube (play_music);
- поиск фильмов, сериалов и аниме (open_movie);
- открытие сайтов и ссылок (open_url);
- управление воспроизведением (media_control).
Если пользователь просит открыть программу, включить музыку/плейлист, запустить фильм или открыть сайт — ОБЯЗАТЕЛЬНО вызывай нужный инструмент.
Если просят расслабляющий плейлист, фон или музыку на твой вкус — сама подбери конкретный атмосферный запрос (lofi, synthwave, phonk, chill, ambient) и вызови инструмент.
Когда вызываешь инструмент, в сообщении сразу коротко скажи об этом в своём характере (например: «Запускаю стим», «Врубила синтвейв на спотике, кайфуй»)."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Запустить приложение или программу на компьютере (например: Steam, Telegram, Discord, браузер, Spotify, калькулятор, игры).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название приложения или программы, например 'steam', 'browser', 'telegram', 'spotify'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Включить музыку, плейлист или трек на Spotify, SoundCloud или YouTube. Сама выбери подходящий атмосферный запрос под настроение пользователя на свой вкус!",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["spotify", "soundcloud", "youtube"],
                        "description": "Сервис: spotify, soundcloud или youtube."
                    },
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос для музыки на твой вкус."
                    }
                },
                "required": ["service", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_movie",
            "description": "Найти и открыть фильм, сериал или аниме для просмотра в браузере.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Название фильма, сериала или аниме."
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Открыть любую веб-страницу или ссылку в браузере.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL-адрес сайта или ссылки."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_control",
            "description": "Управление воспроизведением мультимедиа.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "pause", "next", "prev"],
                        "description": "Действие: play, pause, next или prev."
                    }
                },
                "required": ["action"]
            }
        }
    }
]


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

    def _execute_tool(self, name, args, actions):
        try:
            if name == "open_app":
                actions.launch_app(args.get("name", ""))
            elif name == "play_music":
                actions.play_music(args.get("service", "youtube"), args.get("query", ""))
            elif name == "open_movie":
                actions.open_movie(args.get("title", ""))
            elif name == "open_url":
                actions.open_url(args.get("url", ""))
            elif name == "media_control":
                act = args.get("action")
                if act == "play":
                    actions.media_play(None, None)
                elif act == "pause":
                    actions.media_pause(None, None)
                elif act == "next":
                    actions.media_next(None, None)
                elif act == "prev":
                    actions.media_prev(None, None)
        except Exception as e:
            log.exception("Tool %s execution error: %s", name, e)

    def ask(self, question, actions=None):
        if not self.available:
            return "Ключ DeepSeek API не задан. Введи его в меню трея или в config.json."
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        self.history.append({"role": "user", "content": question})
        self.history = self.history[-10:]
        messages = [{"role": "system", "content": SYSTEM + "\n" + user_context() + f"\nСейчас {now}."}] + self.history

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
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
            msg = data["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            answer = msg.get("content") or ""
            if tool_calls and actions:
                for call in tool_calls:
                    fn = call.get("function", {})
                    fn_name = fn.get("name")
                    try:
                        args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        args = {}
                    self._execute_tool(fn_name, args, actions)
                    if not answer:
                        if fn_name == "open_app":
                            answer = f"Запускаю {args.get('name', 'приложение')}."
                        elif fn_name == "play_music":
                            answer = f"Врубила {args.get('query', 'музыку')}."
                        elif fn_name == "open_movie":
                            answer = f"Открываю {args.get('title', 'фильм')}."
                        elif fn_name == "open_url":
                            answer = "Открываю ссылку."
                        elif fn_name == "media_control":
                            answer = "Сделано."
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

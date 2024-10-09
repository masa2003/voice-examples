""" Тесты
Компьютер, включи музыку
Компьютер, сделай громче
Компьютер, сделай тише
Еще
Компьютер, следующий трек
Еще
Повтори
Компьютер, как включить следущий трек
Компьютер, покажи сколько времени
Компьютер, покажи плеер
Компьютер, какая погода
Компьютер, открой лор
Компьютер, как зовут Пушкина?
Компьютер, теперь тебя зовут Алиса
Алиса, расскажи в каком году была октябрьская революция
"""

import inspect
import logging
import os
import string
import subprocess
import sys
import urllib.parse
from datetime import datetime

import pymorphy3


class Settings:
    computer_name = "компьютер".lower()
    browser = "xdg-open"
    calendar = "gnome-calendar"


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger("computer")
morph = pymorphy3.MorphAnalyzer()


class Context:
    last_action_dt = datetime.now()
    last_action = None
    last_detail = None


def do(text):
    logger.debug(f'Текст: "{text}"')
    parts = text.split()
    norm_parts = norm_text(text)
    logger.debug(f"Нормализованный текст: {norm_parts}")

    if (
        norm_parts[0] != Settings.computer_name
        and (datetime.now() - Context.last_action_dt).seconds > 4
    ):
        logger.debug(f'Запрос не мне: "{text}"')
        return

    if norm_parts[0] == Settings.computer_name:
        query = norm_parts[1:]
    else:
        query = norm_parts.copy()

    procs = []
    for p in processors:
        for w in query:
            if w in p.triggers and p not in procs:
                remaining_parts = query.copy()
                remaining_parts.remove(w)
                procs.append((p, filtered_text(parts, norm_parts, remaining_parts)))
            elif hasattr(p, "query_triggers") and w in p.query_triggers:
                procs.append((p, filtered_text(parts, norm_parts, query)))

    logger.debug(f"triggered processors: {procs}")

    acts = []
    for p, detail in procs:
        if not p.actions:
            acts.append((p.default, detail))
            continue
        for a, attr in p.actions.items():
            if a in query:
                acts.append((getattr(p, attr), detail))

    for p in processors:
        for a, attr in p.actions.items():
            if a in query:
                acts.append((getattr(p, attr), filtered_text(parts, norm_parts, query)))

    if not acts:
        logger.warning(f"Запрос не распознан: \"{' '.join(parts)}\"")

    logger.debug(
        "matched actions: %s",
        [
            f"{method.__self__.__class__.__name__}().{method.__name__}('{detail}')"
            for method, detail in acts
        ],
    )

    for method, detail in acts:
        if len(inspect.signature(method).parameters) > 0:
            method(detail)
        else:
            method()
        Context.last_action_dt = datetime.now()
        if method.__self__.repeatable:
            Context.last_action = method
            Context.last_detail = detail
        return


def norm_text(text):
    parts = text.split()
    norm_parts = []
    for word in parts:
        norm_parts.append(
            "".join([s.lower() for s in word if s not in string.punctuation])
        )

    norm_parts = [morph.parse(x)[0].normal_form for x in norm_parts]
    return norm_parts


def filtered_text(parts, norm_parts, remaining_parts):
    shift = 0
    detail_parts = []

    for x, w in enumerate(norm_parts):
        if x - shift < len(remaining_parts):
            if w == remaining_parts[x - shift]:
                detail_parts.append(parts[x])
            else:
                shift += 1

    return " ".join(detail_parts)


class Audacious:
    def __init__(self):
        self.repeatable = True
        self.triggers = {"музыка", "песня", "трек", "плеер"}
        self.actions = {
            "убрать": "stop",
            "выключить": "pause",
            "остановить": "pause",
            "пауза": "pause",
            "играть": "play",
            "продолжить": "play",
            "следующий": "next",
            "предыдущий": "prev",
            "включить": "play",
            "показать": "show",
        }

    def play(self):
        execute(["audacious", "--play"])

    def pause(self):
        execute(["audacious", "--pause"])

    def stop(self):
        execute(["audacious", "--stop"])

    def prev(self):
        execute(["audacious", "--rew"])

    def next(self):
        execute(["audacious", "--fwd"])

    def show(self):
        execute(["audacious", "--show-main-window"])

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class PipewireVolume:
    def __init__(self):
        self.repeatable = True
        self.triggers = {
            "музыка",
            "песня",
            "трек",
            "громкость",
            "звук",
            "фильм",
            "плеер",
        }
        self.actions = {
            "включить": "unmute",
            "убрать": "mute",
            "выключить": "mute",
            "увеличить": "inc",
            "прибавить": "inc",
            "добавить": "inc",
            "громкий": "inc",
            "большой": "inc",
            "уменьшить": "dec",
            "убавить": "dec",
            "прибрать": "dec",
            "тихий": "dec",
            "маленький": "dec",
        }

    def inc(self, detail):
        value = text_to_number(detail) / 100 or 0.1
        execute(f"wpctl set-volume @DEFAULT_AUDIO_SINK@ {value}+")

    def dec(self, detail):
        value = text_to_number(detail) / 100 or 0.1
        execute(f"wpctl set-volume @DEFAULT_AUDIO_SINK@ {value}-")

    def mute(self):
        execute("wpctl set-mute @DEFAULT_AUDIO_SINK@ 1")

    def unmute(self):
        execute("wpctl set-mute @DEFAULT_AUDIO_SINK@ 0")

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class Search:
    def __init__(self):
        self.repeatable = False
        self.triggers = {
            "найти",
            "поиск",
            "гуглить",
            "рассказать",
            "объяснить",
            "перевести",
            "сказать",
        }
        self.actions = {}
        self.query_triggers = {
            "что",
            "кто",
            "зачем",
            "почему",
            "сколько",
            "какой",
            "как",
            "когда",
        }

    def default(self, text):
        query = urllib.parse.quote(text)
        execute(f"{Settings.browser} https://google.com/search?q={query}")

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class PipewireMic:
    def __init__(self):
        self.repeatable = True
        self.triggers = {"микрофон"}
        self.actions = {
            "починить": "fix",
            "исправить": "fix",
            "громкий": "inc",
            "тихий": "dec",
            "прибавить": "inc",
            "убавить": "dec",
        }

    def fix(self):
        execute("wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 0.3")

    def inc(self, detail):
        value = text_to_number(detail) / 100 or 0.1
        execute(f"wpctl set-volume @DEFAULT_AUDIO_SOURCE@ {value}+")

    def dec(self, detail):
        value = text_to_number(detail) / 100 or 0.1
        execute(f"wpctl set-volume @DEFAULT_AUDIO_SOURCE@ {value}+")

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class Launcher:
    def __init__(self):
        self.repeatable = True
        self.triggers = {"открыть", "запустить", "зайти"}
        self.query_triggers = set()
        self.actions = {"лор": "lor", "кгб": "gpt", "календарь": "calendar"}

    def lor(self):
        execute(f"{Settings.browser} https://linux.org.ru/")

    def gpt(self):
        execute(f"{Settings.browser} https://chatgpt.com/")

    def calendar(self):
        execute(Settings.calendar)

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class Rename:
    def __init__(self):
        self.repeatable = False
        self.triggers = set()
        self.query_triggers = {"звать"}
        self.actions = {}

    def default(self, detail):
        if not detail:
            return

        Settings.computer_name = norm_text(detail)[-1]
        logger.info(f"Новое имя {Settings.computer_name}")

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class Repeat:
    def __init__(self):
        self.repeatable = False
        self.triggers = {"ещё", "повторить"}
        self.actions = {}

    def default(self):
        if not Context.last_action:
            return

        if len(inspect.signature(Context.last_action).parameters) > 0:
            Context.last_action(Context.last_detail)
        else:
            Context.last_action()

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


processors = [
    Search(),
    Launcher(),
    Audacious(),
    PipewireVolume(),
    PipewireMic(),
    Repeat(),
    Rename(),
]


def execute(cmd):
    if isinstance(cmd, str):
        cmd = cmd.split()

    logger.debug(f"Запускаю: `{' '.join(cmd)}`")
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )


number_words = {
    "ноль": 0,
    "один": 1,
    "два": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
    "сто": 100,
}


def text_to_number(text):
    words = norm_text(text)
    for word in words:
        if word.isnumeric():
            return int(word)

    result = 0
    for word in words:
        if word in number_words:
            result += number_words[word]
    return result


if __name__ == "__main__":
    listen = None

    for arg in sys.argv:
        if arg == "--whisper":
            from whisper_listener import whisper_listen

            listen = whisper_listen

    if not listen:
        from vosk_listener import vosk_listen

        listen = vosk_listen

    while True:
        try:
            listen(do)
        except KeyboardInterrupt:
            exit()
        except Exception:
            logger.exception("Ошибка")

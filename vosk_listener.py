import json
import logging
import subprocess

from vosk import KaldiRecognizer, Model

logger = logging.getLogger("vosk_listener")

SAMPLE_RATE = 16000
MODEL_NAME = "vosk-model-small-ru-0.22"  # https://alphacephei.com/vosk/models


def vosk_listen(callback):
    listen_cmd = f"ffmpeg -loglevel quiet -f pulse -ar {SAMPLE_RATE} -i default -f s16le -ch_layout mono -"

    logger.debug(f'Загрузка модели "{MODEL_NAME}"')
    model = Model(model_name=MODEL_NAME)
    rec = KaldiRecognizer(model, SAMPLE_RATE)

    logger.debug("Слушаю")
    with subprocess.Popen(listen_cmd.split(), stdout=subprocess.PIPE) as process:
        while data := process.stdout.read(4000):
            if rec.AcceptWaveform(data):
                if text := json.loads(rec.FinalResult())["text"]:
                    callback(text)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )
    try:
        vosk_listen(logger.info)
    except KeyboardInterrupt:
        pass

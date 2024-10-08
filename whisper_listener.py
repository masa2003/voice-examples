import logging
import subprocess
import warnings

import numpy as np
import torch
import whisper

warnings.simplefilter(action="ignore", category=FutureWarning)
logger = logging.getLogger("whisper_listener")

SAMPLE_RATE = 16000
MODEL_NAME = "medium"  # https://github.com/openai/whisper?tab=readme-ov-file#available-models-and-languages

buffer = []


def whisper_listen(callback):
    silence_sec = 1.0
    silence_threshold = 0.03  # 0..1
    listen_cmd = f"ffmpeg -loglevel quiet -f pulse -ar {SAMPLE_RATE} -i default -f s16le -ch_layout mono -"
    sample_size = int(SAMPLE_RATE * 2 * silence_sec)

    logger.debug(f"Используется CUDA: {torch.cuda.is_available()}")
    logger.debug(f'Загрузка модели whisper "{MODEL_NAME}"')
    model = whisper.load_model(MODEL_NAME)
    logger.debug("Слушаю")

    with subprocess.Popen(listen_cmd.split(), stdout=subprocess.PIPE) as process:
        while data := process.stdout.read(sample_size):
            waveform = (
                np.frombuffer(data, np.int16).flatten().astype(np.float32) / 32768.0
            )
            if is_silence(waveform, threshold=silence_threshold):
                if buffer:
                    result = model.transcribe(np.concatenate(buffer), language="ru")
                    if result["text"].strip():
                        callback(result["text"].strip())
                    buffer.clear()
            else:
                buffer.append(waveform)


def is_silence(waveform, threshold):
    rms_amplitude = np.sqrt(np.mean(waveform**2))
    # logger.debug(f"{rms_amplitude = }")
    # logger.debug(f"is silence: {rms_amplitude < threshold}")
    return rms_amplitude < threshold


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )
    try:
        whisper_listen(logger.info)
    except KeyboardInterrupt:
        pass

"""Fast local French speech synthesis backed by Piper."""
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path
from threading import Lock
import wave

from config import settings


_load_lock = Lock()
_generation_lock = Lock()
_voice = None


def status() -> dict:
    model_path = Path(settings.PIPER_MODEL_PATH)
    config_path = Path(settings.PIPER_CONFIG_PATH)
    dependencies_installed = find_spec("piper") is not None
    model_installed = model_path.is_file() and config_path.is_file()
    return {
        "available": dependencies_installed and model_installed,
        "dependencies_installed": dependencies_installed,
        "model_installed": model_installed,
        "voice": model_path.stem,
    }


def _get_voice():
    global _voice
    if _voice is not None:
        return _voice

    with _load_lock:
        if _voice is None:
            from piper import PiperVoice

            model_path = Path(settings.PIPER_MODEL_PATH)
            config_path = Path(settings.PIPER_CONFIG_PATH)
            if not model_path.is_file() or not config_path.is_file():
                raise FileNotFoundError("Les fichiers du modèle Piper sont absents")

            _voice = PiperVoice.load(
                str(model_path),
                config_path=str(config_path),
                use_cuda=settings.PIPER_USE_CUDA,
            )
    return _voice


def warm_up() -> None:
    """Load the voice before the first synthesis request."""
    _get_voice()


def synthesize(text: str, speed: float) -> bytes:
    from piper import SynthesisConfig

    voice = _get_voice()
    synthesis_config = SynthesisConfig(length_scale=1 / speed)
    output = BytesIO()
    with _generation_lock:
        with wave.open(output, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=synthesis_config)
    return output.getvalue()

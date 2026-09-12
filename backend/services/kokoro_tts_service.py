"""Local French speech synthesis backed by Kokoro ONNX."""
from io import BytesIO
from importlib.util import find_spec
from pathlib import Path
from threading import Lock

from config import settings


_load_lock = Lock()
_generation_lock = Lock()
_engine = None


def status() -> dict:
    model_path = Path(settings.KOKORO_MODEL_PATH)
    voices_path = Path(settings.KOKORO_VOICES_PATH)
    dependencies_installed = all(
        find_spec(module) is not None for module in ("kokoro_onnx", "soundfile")
    )
    model_installed = model_path.is_file() and voices_path.is_file()
    provider = None
    if dependencies_installed:
        import onnxruntime as ort

        available_providers = ort.get_available_providers()
        provider = (
            "CUDAExecutionProvider"
            if "CUDAExecutionProvider" in available_providers
            else "CPUExecutionProvider"
        )
    return {
        "available": dependencies_installed and model_installed,
        "dependencies_installed": dependencies_installed,
        "model_installed": model_installed,
        "voice": settings.KOKORO_VOICE,
        "provider": provider,
    }


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine

    with _load_lock:
        if _engine is None:
            import onnxruntime as ort
            from kokoro_onnx import Kokoro

            model_path = Path(settings.KOKORO_MODEL_PATH)
            voices_path = Path(settings.KOKORO_VOICES_PATH)
            if not model_path.is_file() or not voices_path.is_file():
                raise FileNotFoundError("Les fichiers du modèle Kokoro sont absents")

            available_providers = ort.get_available_providers()
            if "CUDAExecutionProvider" in available_providers:
                ort.preload_dlls()
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                providers = ["CPUExecutionProvider"]
            session = ort.InferenceSession(str(model_path), providers=providers)
            _engine = Kokoro.from_session(session, str(voices_path))
    return _engine


def warm_up() -> None:
    """Load the model before the first synthesis request."""
    _get_engine()


def synthesize(text: str, speed: float) -> bytes:
    import soundfile as sf

    engine = _get_engine()
    with _generation_lock:
        samples, sample_rate = engine.create(
            text,
            settings.KOKORO_VOICE,
            speed=speed,
            lang="fr-fr",
        )

    output = BytesIO()
    sf.write(output, samples, sample_rate, format="WAV")
    return output.getvalue()

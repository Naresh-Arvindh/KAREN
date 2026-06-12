import os
import subprocess
import tempfile
import time
import numpy as np
import pyaudio
import whisper
from playsound import playsound
from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import (
    PIPER_EXE, PIPER_MODEL,
    WHISPER_MODEL, AUDIO_RATE, AUDIO_CHUNK, MIC_TIMEOUT, WAKE_WORD
)


class TTSWorker(QObject):
    started  = pyqtSignal()
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, text: str):
        super().__init__()
        self._text = text.replace("**", "").replace("*", "").replace("`", "").replace("#", "")

    def run(self):
        try:
            self.started.emit()
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            subprocess.run(
                [PIPER_EXE, "--model", PIPER_MODEL, "--output_file", tmp.name],
                input=self._text.encode("utf-8"),
                capture_output=True, timeout=30
            )
            if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 0:
                playsound(tmp.name)
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


class MicWorker(QObject):
    audio_ready = pyqtSignal(bytes)
    error       = pyqtSignal(str)

    def __init__(self, duration: int = MIC_TIMEOUT):
        super().__init__()
        self._duration = duration
        self._active   = True

    def stop(self):
        self._active = False

    def run(self):
        try:
            pa     = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16, channels=1,
                rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK
            )
            frames = []
            for _ in range(int(AUDIO_RATE / AUDIO_CHUNK * self._duration)):
                if not self._active:
                    break
                frames.append(stream.read(AUDIO_CHUNK, exception_on_overflow=False))
            stream.stop_stream()
            stream.close()
            pa.terminate()
            self.audio_ready.emit(b"".join(frames))
        except Exception as e:
            self.error.emit(str(e))


class STTWorker(QObject):
    text_ready = pyqtSignal(str)
    error      = pyqtSignal(str)
    _model     = None

    def __init__(self, audio_bytes: bytes):
        super().__init__()
        self._audio = audio_bytes

    @classmethod
    def load_model(cls):
        if cls._model is None:
            cls._model = whisper.load_model(WHISPER_MODEL)

    def run(self):
        try:
            STTWorker.load_model()
            audio_np = np.frombuffer(self._audio, dtype=np.int16).astype(np.float32) / 32768.0
            result   = STTWorker._model.transcribe(audio_np, language="en", fp16=False)
            self.text_ready.emit(result.get("text", "").strip())
        except Exception as e:
            self.error.emit(str(e))


class WakeWordListener(QObject):
    wake_detected = pyqtSignal()
    _running      = True

    def stop(self):
        self._running = False

    def run(self):
        pa = None
        try:
            STTWorker.load_model()
            pa = pyaudio.PyAudio()
            while self._running:
                stream = pa.open(
                    format=pyaudio.paInt16, channels=1,
                    rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK
                )
                frames = []
                for _ in range(int(AUDIO_RATE / AUDIO_CHUNK * 2)):
                    if not self._running:
                        break
                    frames.append(stream.read(AUDIO_CHUNK, exception_on_overflow=False))
                stream.stop_stream()
                stream.close()
                if not frames:
                    continue
                audio_np = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32) / 32768.0
                result   = STTWorker._model.transcribe(audio_np, language="en", fp16=False)
                if WAKE_WORD in result.get("text", "").lower().strip():
                    self.wake_detected.emit()
                    time.sleep(2)
        except Exception:
            pass
        finally:
            if pa:
                try:
                    pa.terminate()
                except Exception:
                    pass

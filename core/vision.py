import base64
import datetime
import time
import httpx
import mss
from PIL import Image
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config.settings import (
    OLLAMA_VISION, VISION_MODEL, VISION_PROMPT,
    SCREENSHOT_DIR, SCREENSHOT_RETAIN_HOURS, SUMMARY_DIR
)


class VisionWorker(QObject):
    summary_ready = pyqtSignal(str, str)
    error         = pyqtSignal(str)

    def __init__(self, img_path: str):
        super().__init__()
        self._img_path = img_path

    def run(self):
        try:
            with open(self._img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            payload = {
                "model":  VISION_MODEL,
                "prompt": VISION_PROMPT,
                "images": [b64],
                "stream": False
            }
            r       = httpx.post(OLLAMA_VISION, json=payload, timeout=120)
            summary = r.json().get("response", "").strip()
            self.summary_ready.emit(summary, self._img_path)
        except Exception as e:
            self.error.emit(str(e))


class ScreenMonitor(QObject):
    screenshot_taken = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._passive_capture)
        self._timer.start(5 * 60 * 1000)
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_old)
        self._cleanup_timer.start(60 * 60 * 1000)

    def capture_now(self, reason: str = "manual") -> str:
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(SCREENSHOT_DIR / f"screen_{ts}_{reason}.jpg")
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img     = sct.grab(monitor)
            pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            pil = pil.resize((1280, int(1280 * pil.height / pil.width)), Image.LANCZOS)
            pil.save(path, "JPEG", quality=70)
        self.screenshot_taken.emit(path)
        return path

    def _passive_capture(self):
        self.capture_now("passive")

    def _cleanup_old(self):
        cutoff = time.time() - (SCREENSHOT_RETAIN_HOURS * 3600)
        for f in SCREENSHOT_DIR.glob("*.jpg"):
            if f.stat().st_mtime < cutoff:
                try:
                    f.unlink()
                except Exception:
                    pass

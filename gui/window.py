import sys
import os
import re as _re
import json
import datetime
import random
import webbrowser
import shutil
import glob as _glob
import subprocess

import httpx
from jinja2 import Template

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSystemTrayIcon, QMenu, QLineEdit,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QObject, QRectF, pyqtSignal, QThread
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QIcon,
    QPixmap, QRadialGradient
)

from config.settings import (
    OLLAMA_URL, MODEL, KAREN_SYSTEM, REPORT_TEMPLATE,
    USER_NAME, CORNER_M, WIDGET_W, WIDGET_H,
    DATA_DIR, SUMMARY_DIR,
    APP_REGISTRY, APP_ALIASES, MIC_TIMEOUT
)
from core.memory import KarenMemory
from core.vision import VisionWorker, ScreenMonitor
from core.speech import TTSWorker, MicWorker, STTWorker, WakeWordListener
from gui.orb import OrbWidget

C_BG     = QColor(10, 12, 18, 220)
C_BORDER = QColor(0, 220, 200, 55)


def _resolve_app_name(raw: str) -> str:
    raw = raw.strip().lower()
    return APP_ALIASES.get(raw, raw)

def _find_executable(candidates: list):
    for c in candidates:
        c = os.path.expandvars(c)
        if "*" in c:
            matches = _glob.glob(c)
            if matches:
                return matches[0]
        if os.path.isabs(c) or (os.sep in c):
            if os.path.exists(c):
                return c
        else:
            found = shutil.which(c)
            if found:
                return found
    return None

_OPEN_PATTERNS = [
    _re.compile(r"^(?:open|launch|start|run|execute|fire up|boot up|bring up|pull up)\s+(.+)$", _re.I),
    _re.compile(r"^can you (?:open|launch|start|run)\s+(.+?)\??$", _re.I),
    _re.compile(r"^(?:open|launch|start)\s+(?:up\s+)?(.+?)\s+(?:for me|please)$", _re.I),
    _re.compile(r"^(.+?)\s+(?:please open|please launch|please start)$", _re.I),
]

def detect_open_app_intent(text: str):
    for pat in _OPEN_PATTERNS:
        m = pat.match(text.strip())
        if m:
            app_name = m.group(1).strip().rstrip("?!. ").lower()
            if len(app_name.split()) <= 4:
                return app_name
    return None


class AppLauncherWorker(QObject):
    launched = pyqtSignal(str)
    failed   = pyqtSignal(str)

    def __init__(self, app_name: str):
        super().__init__()
        self._app_name = app_name

    def run(self):
        try:
            key = _resolve_app_name(self._app_name)
            candidates = APP_REGISTRY.get(key)
            if not candidates:
                for reg_key in APP_REGISTRY:
                    if reg_key in key or key in reg_key:
                        candidates = APP_REGISTRY[reg_key]
                        key = reg_key
                        break
            if not candidates:
                self.failed.emit(f"I don't have '{self._app_name}' in my registry.")
                return
            if len(candidates) == 1 and candidates[0].endswith(":"):
                if sys.platform == "win32":
                    import ctypes
                    ctypes.windll.shell32.ShellExecuteW(None, "open", candidates[0], None, None, 1)
                    self.launched.emit(key)
                else:
                    self.failed.emit(f"{key} is a Windows-only feature.")
                return
            exe = _find_executable(candidates)
            if exe:
                flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
                self.launched.emit(key)
            else:
                if sys.platform == "win32":
                    try:
                        os.startfile(candidates[0])
                        self.launched.emit(key)
                    except Exception:
                        self.failed.emit(f"Couldn't find {key}. Is it installed?")
                else:
                    self.failed.emit(f"Couldn't find {key}. Is it installed?")
        except Exception as e:
            self.failed.emit(str(e))


class OllamaWorker(QObject):
    token_received = pyqtSignal(str)
    done           = pyqtSignal(str)
    error          = pyqtSignal(str)

    def __init__(self, history: list):
        super().__init__()
        self._history = history

    def run(self):
        try:
            payload = {
                "model":    MODEL,
                "messages": [{"role": "system", "content": KAREN_SYSTEM}] + self._history,
                "stream":   True
            }
            full = ""
            with httpx.stream("POST", OLLAMA_URL, json=payload, timeout=120) as r:
                for line in r.iter_lines():
                    if not line.strip():
                        continue
                    try:
                        data  = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            full += token
                            self.token_received.emit(token)
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
            self.done.emit(full)
        except Exception as e:
            self.error.emit(str(e))


class SessionSummaryWorker(QObject):
    done  = pyqtSignal(str, list, list)
    error = pyqtSignal(str)

    def __init__(self, history: list):
        super().__init__()
        self._history = history

    def run(self):
        try:
            if not self._history:
                self.done.emit("", [], [])
                return
            convo_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}"
                for m in self._history
                if not m["content"].startswith("[System:")
                and not m["content"].startswith("[Context:")
            )
            prompt = f"""Analyze this conversation and return a JSON object with exactly these keys:
"summary": one paragraph summary of what was discussed,
"topics": list of up to 5 specific topics or subjects mentioned,
"patterns": list of up to 3 behavioral patterns you notice about the user.

Conversation:
{convo_text[:3000]}

Return only valid JSON, nothing else."""
            payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False}
            r    = httpx.post(OLLAMA_URL, json=payload, timeout=60)
            text = r.json().get("message", {}).get("content", "").strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            self.done.emit(data.get("summary", ""), data.get("topics", []), data.get("patterns", []))
        except Exception as e:
            self.error.emit(str(e))


class WeeklyReportGenerator:
    def __init__(self, memory: KarenMemory):
        self._memory     = memory
        self._report_dir = DATA_DIR / "reports"
        self._report_dir.mkdir(parents=True, exist_ok=True)

    def generate(self) -> str:
        now       = datetime.datetime.now()
        week_str  = now.strftime("Week of %B %d, %Y")
        generated = now.strftime("%Y-%m-%d %H:%M")
        topics    = self._memory.get_all_topics()
        patterns  = self._memory.get_recent_patterns(10)
        screen_summaries = []
        for f in sorted(SUMMARY_DIR.glob("*.txt"), reverse=True)[:20]:
            try:
                lines = f.read_text().strip().split("\n", 1)
                ts    = lines[0].strip("[]") if lines else ""
                text  = lines[1].strip() if len(lines) > 1 else ""
                screen_summaries.append({"timestamp": ts, "text": text})
            except Exception:
                continue
        sessions = []
        try:
            r     = self._memory._convos.get()
            docs  = r.get("documents", [])
            metas = r.get("metadatas", [])
            for doc, meta in zip(docs, metas):
                ts = meta.get("timestamp", "")[:16].replace("T", " ") if meta else ""
                sessions.append({"timestamp": ts, "text": doc})
            sessions = sessions[-20:]
        except Exception:
            pass
        html = Template(REPORT_TEMPLATE).render(
            week=week_str, generated=generated,
            session_count=len(sessions), topic_count=len(topics),
            pattern_count=len(patterns), summary_count=len(screen_summaries),
            topics=topics[:30], patterns=patterns,
            sessions=sessions, screen_summaries=screen_summaries,
        )
        path = self._report_dir / f"report_{now.strftime('%Y_%m_%d')}.html"
        path.write_text(html, encoding="utf-8")
        return str(path)


class BubbleLabel(QLabel):
    def __init__(self, text: str, is_user: bool = False):
        super().__init__(text)
        self.setWordWrap(True)
        self.setFont(QFont("Consolas", 8))
        self.setContentsMargins(10, 6, 10, 6)
        self.setMaximumWidth(240)
        color  = "rgba(0,180,160,40)"    if is_user else "rgba(25,30,45,180)"
        border = "rgba(0,180,160,80)"    if is_user else "rgba(0,220,200,25)"
        tcolor = "rgba(180,220,215,230)" if is_user else "rgba(200,210,220,200)"
        self.setStyleSheet(f"""QLabel {{
            background:{color}; border:1px solid {border}; border-radius:8px;
            color:{tcolor}; font-family:Consolas; font-size:8pt; padding:6px 10px;}}""")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


class KarenWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._drag_pos          = None
        self._state             = "idle"
        self._history           = []
        self._worker            = None
        self._thread            = None
        self._vision_worker     = None
        self._vision_thread     = None
        self._streaming_label   = None
        self._streaming_text    = ""
        self._screen_context    = ""
        self._memory            = KarenMemory()
        self._session_id        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._sum_thread        = None
        self._sum_worker        = None
        self._report            = WeeklyReportGenerator(self._memory)
        self._tts_thread        = None
        self._tts_worker        = None
        self._app_launch_thread = None
        self._app_launch_worker = None
        self._mic_thread        = None
        self._mic_worker        = None
        self._stt_thread        = None
        self._stt_worker        = None
        self._mic_active        = False
        self._wake_thread       = None
        self._wake_listener     = None
        self._setup_window()
        self._build_ui()
        self._position_corner()
        self._monitor = ScreenMonitor()
        self._monitor.screenshot_taken.connect(self._on_screenshot)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WIDGET_W, WIDGET_H)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)
        self._orb = OrbWidget()
        name_lbl  = QLabel("KAREN")
        name_lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color:rgba(0,220,200,255);letter-spacing:3px;")
        self._status_lbl = QLabel("online  ·  idle")
        self._status_lbl.setFont(QFont("Consolas", 8))
        self._status_lbl.setStyleSheet("color:rgba(180,200,210,150);")
        close_btn = QPushButton("×")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("""QPushButton{background:rgba(255,80,80,35);color:rgba(255,120,120,200);
            border:1px solid rgba(255,80,80,55);border-radius:9px;font-size:13px;font-family:Consolas;}
            QPushButton:hover{background:rgba(255,80,80,110);color:white;}""")
        close_btn.clicked.connect(self._on_close)
        info_col = QVBoxLayout()
        info_col.setSpacing(2); info_col.setContentsMargins(0, 0, 0, 0)
        info_col.addWidget(name_lbl); info_col.addWidget(self._status_lbl)
        header = QHBoxLayout(); header.setSpacing(8)
        header.addWidget(self._orb); header.addLayout(info_col)
        header.addStretch()
        header.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color:rgba(0,220,200,30);"); root.addWidget(line)
        self._chat_widget = QWidget()
        self._chat_widget.setStyleSheet("background:transparent;")
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setSpacing(6); self._chat_layout.setContentsMargins(4, 4, 4, 4)
        self._chat_layout.addStretch()
        self._scroll = QScrollArea()
        self._scroll.setWidget(self._chat_widget); self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""QScrollArea{background:transparent;border:none;}
            QScrollBar:vertical{background:rgba(0,0,0,0);width:4px;}
            QScrollBar::handle:vertical{background:rgba(0,220,200,60);border-radius:2px;}""")
        root.addWidget(self._scroll, stretch=1)
        self._input = QLineEdit()
        self._input.setPlaceholderText("say something...")
        self._input.setFont(QFont("Consolas", 8)); self._input.setFixedHeight(30)
        self._input.setStyleSheet("""QLineEdit{background:rgba(0,220,200,15);
            border:1px solid rgba(0,220,200,50);border-radius:6px;
            color:rgba(200,215,220,230);padding:0 8px;font-family:Consolas;font-size:8pt;}
            QLineEdit:focus{border:1px solid rgba(0,220,200,120);}""")
        self._input.returnPressed.connect(self._send)
        send_btn = QPushButton("↑"); send_btn.setFixedSize(30, 30)
        send_btn.setStyleSheet("""QPushButton{background:rgba(0,220,200,40);color:rgba(0,220,200,230);
            border:1px solid rgba(0,220,200,70);border-radius:6px;font-size:14px;}
            QPushButton:hover{background:rgba(0,220,200,90);}""")
        send_btn.clicked.connect(self._send)
        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(30, 30)
        self._mic_btn.setCheckable(True)
        self._mic_btn.setStyleSheet("""QPushButton{background:rgba(255,80,80,30);color:rgba(255,120,120,200);
            border:1px solid rgba(255,80,80,55);border-radius:6px;font-size:14px;}
            QPushButton:checked{background:rgba(255,80,80,140);color:white;}
            QPushButton:hover{background:rgba(255,80,80,80);}""")
        self._mic_btn.pressed.connect(self._mic_start)
        self._mic_btn.released.connect(self._mic_stop)
        input_row = QHBoxLayout(); input_row.setSpacing(6)
        input_row.addWidget(self._mic_btn)
        input_row.addWidget(self._input); input_row.addWidget(send_btn)
        root.addLayout(input_row)

    def _position_corner(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - WIDGET_W - CORNER_M, screen.bottom() - WIDGET_H - CORNER_M)

    def open_application(self, app_name: str):
        self._app_launch_thread = QThread()
        self._app_launch_worker = AppLauncherWorker(app_name)
        self._app_launch_worker.moveToThread(self._app_launch_thread)
        self._app_launch_thread.started.connect(self._app_launch_worker.run)
        self._app_launch_worker.launched.connect(self._on_app_launched)
        self._app_launch_worker.failed.connect(self._on_app_failed)
        self._app_launch_worker.launched.connect(lambda _: self._app_launch_thread.quit())
        self._app_launch_worker.failed.connect(lambda _: self._app_launch_thread.quit())
        self._app_launch_thread.finished.connect(self._cleanup_app_launch_thread)
        self._app_launch_thread.start()

    def _on_app_launched(self, app_name: str):
        msg = random.choice([
            f"Opening {app_name}.",
            f"{app_name.capitalize()} is on its way.",
            f"Launching {app_name} now.",
            f"Done. {app_name.capitalize()} should be up in a moment.",
        ])
        self._add_bubble(msg, is_user=False)
        self.speak(msg)
        self._history.append({"role": "assistant", "content": msg})

    def _on_app_failed(self, error: str):
        self._add_bubble(error, is_user=False)
        self.speak(error)
        self._history.append({"role": "assistant", "content": error})
        self.set_state("warning")
        QTimer.singleShot(3000, lambda: self.set_state("idle"))

    def _cleanup_app_launch_thread(self):
        if self._app_launch_thread:
            self._app_launch_thread.wait()
        self._app_launch_worker = None
        self._app_launch_thread = None

    def _on_screenshot(self, path: str):
        if self._vision_thread and self._vision_thread.isRunning():
            return
        self._vision_thread = QThread()
        self._vision_worker = VisionWorker(path)
        self._vision_worker.moveToThread(self._vision_thread)
        self._vision_thread.started.connect(self._vision_worker.run)
        self._vision_worker.summary_ready.connect(self._on_vision_summary)
        self._vision_worker.error.connect(self._on_vision_error)
        self._vision_thread.start()

    def _on_vision_summary(self, summary: str, img_path: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sf = SUMMARY_DIR / f"summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        sf.write_text(f"[{ts}]\n{summary}\n")
        self._screen_context = f"[Screen at {ts}]: {summary}"
        self._cleanup_vision_thread()

    def _on_vision_error(self, _):
        self._cleanup_vision_thread()

    def _cleanup_vision_thread(self):
        if self._vision_thread:
            self._vision_thread.quit(); self._vision_thread.wait()
        self._vision_worker = None; self._vision_thread = None

    def _add_bubble(self, text: str, is_user: bool = False):
        row = QHBoxLayout(); row.setContentsMargins(0, 0, 0, 0)
        bubble = BubbleLabel(text, is_user)
        if is_user: row.addStretch(); row.addWidget(bubble)
        else:       row.addWidget(bubble); row.addStretch()
        self._chat_layout.insertLayout(self._chat_layout.count() - 1, row)
        QTimer.singleShot(50, self._scroll_bottom)
        return bubble

    def _scroll_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _send(self):
        text = self._input.text().strip()
        if not text or self._worker:
            return
        self._input.clear()
        self._add_bubble(text, is_user=True)
        app_intent = detect_open_app_intent(text)
        if app_intent:
            self.open_application(app_intent)
            return
        content = text
        if self._screen_context:
            content = f"{text}\n\n[Context: {self._screen_context}]"
        mem = self._memory.get_relevant_context(text)
        if mem:
            content = f"{content}\n\n[Memory: {mem}]"
        self._history.append({"role": "user", "content": content})
        self._start_response()

    def _start_response(self):
        self.set_state("talking")
        self._streaming_text  = ""
        self._streaming_label = self._add_bubble("▋", is_user=False)
        self._thread = QThread()
        self._worker = OllamaWorker(list(self._history))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.token_received.connect(self._on_token)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._thread.start()

    def _on_token(self, token: str):
        self._streaming_text += token
        self._streaming_label.setText(self._streaming_text + "▋")
        QTimer.singleShot(20, self._scroll_bottom)

    def _on_done(self, full: str):
        self._streaming_label.setText(full)
        self._history.append({"role": "assistant", "content": full})
        self._cleanup_thread()
        self.set_state("idle")
        self._scroll_bottom()
        self.speak(full)

    def _on_error(self, err: str):
        self._streaming_label.setText(f"[offline — {err}]")
        self._cleanup_thread(); self.set_state("warning")
        QTimer.singleShot(3000, lambda: self.set_state("idle"))

    def _cleanup_thread(self):
        if self._thread: self._thread.quit(); self._thread.wait()
        self._worker = None; self._thread = None

    def speak(self, text: str):
        if self._tts_thread and self._tts_thread.isRunning():
            return
        self._tts_thread = QThread()
        self._tts_worker = TTSWorker(text)
        self._tts_worker.moveToThread(self._tts_thread)
        self._tts_thread.started.connect(self._tts_worker.run)
        self._tts_worker.finished.connect(self._tts_thread.quit)
        self._tts_worker.finished.connect(self._tts_worker.deleteLater)
        self._tts_thread.finished.connect(self._tts_thread.deleteLater)
        self._tts_thread.finished.connect(self._tts_cleanup)
        self._tts_thread.start()

    def _tts_cleanup(self):
        self._tts_worker = None; self._tts_thread = None

    def _mic_start(self):
        if self._mic_active: return
        self._mic_active = True
        self._status_lbl.setText("online  ·  listening...")
        self._orb.set_state("warning")
        self._mic_thread = QThread()
        self._mic_worker = MicWorker(duration=MIC_TIMEOUT)
        self._mic_worker.moveToThread(self._mic_thread)
        self._mic_thread.started.connect(self._mic_worker.run)
        self._mic_worker.audio_ready.connect(self._on_audio)
        self._mic_thread.start()

    def _mic_stop(self):
        if self._mic_worker: self._mic_worker.stop()
        self._mic_active = False
        self._status_lbl.setText("online  ·  idle")
        self._orb.set_state("idle")

    def _on_audio(self, audio_bytes: bytes):
        if self._mic_thread:
            self._mic_thread.quit(); self._mic_thread.wait()
        self._mic_worker = None; self._mic_thread = None
        if not audio_bytes: return
        self._status_lbl.setText("online  ·  processing...")
        self._stt_thread = QThread()
        self._stt_worker = STTWorker(audio_bytes)
        self._stt_worker.moveToThread(self._stt_thread)
        self._stt_thread.started.connect(self._stt_worker.run)
        self._stt_worker.text_ready.connect(self._on_stt_text)
        self._stt_worker.error.connect(self._on_stt_error)
        self._stt_thread.start()

    def _on_stt_text(self, text: str):
        if self._stt_thread: self._stt_thread.quit(); self._stt_thread.wait()
        self._stt_worker = None; self._stt_thread = None
        if not text: self.set_state("idle"); return
        app_intent = detect_open_app_intent(text)
        if app_intent:
            self._add_bubble(text, is_user=True)
            self.open_application(app_intent)
            return
        self._input.setText(text)
        self._send()

    def _on_stt_error(self, _):
        if self._stt_thread: self._stt_thread.quit(); self._stt_thread.wait()
        self._stt_worker = None; self._stt_thread = None
        self.set_state("warning")
        QTimer.singleShot(3000, lambda: self.set_state("idle"))

    def _start_wake_listener(self):
        self._wake_thread   = QThread()
        self._wake_listener = WakeWordListener()
        self._wake_listener.moveToThread(self._wake_thread)
        self._wake_thread.started.connect(self._wake_listener.run)
        self._wake_listener.wake_detected.connect(self._on_wake)
        self._wake_thread.start()

    def _on_wake(self):
        self._mic_btn.setChecked(True)
        self._mic_start()
        QTimer.singleShot(MIC_TIMEOUT * 1000, self._mic_stop)

    def set_state(self, s: str):
        self._state = s
        self._orb.set_state(s)
        labels = {"idle": "online  ·  idle", "talking": "online  ·  thinking...", "warning": "online  ·  error"}
        self._status_lbl.setText(labels.get(s, "online"))

    def generate_report(self):
        path = self._report.generate()
        webbrowser.open(f"file:///{path}")
        self._add_bubble("Weekly report generated.", is_user=False)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(C_BG))
        p.setPen(QPen(C_BORDER, 1))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 14, 14)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _on_close(self):
        self._save_session()
        if self._wake_listener: self._wake_listener.stop()
        self.hide(); self.closed.emit()

    def _save_session(self):
        if not self._history: return
        self._sum_thread = QThread()
        self._sum_worker = SessionSummaryWorker(list(self._history))
        self._sum_worker.moveToThread(self._sum_thread)
        self._sum_thread.started.connect(self._sum_worker.run)
        self._sum_worker.done.connect(self._on_summary_done)
        self._sum_worker.error.connect(lambda _: self._sum_thread.quit())
        self._sum_thread.start()

    def _on_summary_done(self, summary: str, topics: list, patterns: list):
        if summary: self._memory.store_conversation(summary, self._session_id)
        for t in topics:     self._memory.store_topic(t)
        for pat in patterns: self._memory.store_pattern(pat)
        if self._sum_thread: self._sum_thread.quit(); self._sum_thread.wait()
        self._sum_worker = None; self._sum_thread = None


class KarenApp:
    def __init__(self):
        self._app    = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        self._widget = KarenWidget()
        self._tray   = QSystemTrayIcon()
        self._setup_tray()
        self._widget.show()
        self._widget._start_wake_listener()

    def _setup_tray(self):
        widget = self._widget
        px = QPixmap(16, 16)
        px.fill(QColor(0, 220, 200))
        self._tray.setIcon(QIcon(px))
        self._tray.setToolTip("KAREN")
        m = QMenu()
        m.setStyleSheet("""QMenu{background:#0e1118;color:#c8d2dc;border:1px solid rgba(0,220,200,40);
            border-radius:6px;padding:4px;}
            QMenu::item{padding:6px 16px;border-radius:4px;}
            QMenu::item:selected{background:rgba(0,220,200,25);}""")
        m.addAction("Show Karen").triggered.connect(widget.show)
        m.addSeparator()
        m.addAction("Generate weekly report").triggered.connect(widget.generate_report)
        m.addAction("Capture screen now").triggered.connect(lambda: widget._monitor.capture_now("manual"))
        m.addSeparator()
        launch_menu = m.addMenu("Launch app...")
        launch_menu.setStyleSheet(m.styleSheet())
        for _aname in ["chrome", "vscode", "terminal", "discord", "spotify",
                        "notepad", "calculator", "file explorer", "task manager", "powershell"]:
            _action = launch_menu.addAction(_aname.replace("-", " ").title())
            _action.triggered.connect((lambda name: lambda: widget.open_application(name))(_aname))
        m.addSeparator()
        m.addAction("Quit").triggered.connect(self._quit)
        self._tray.setContextMenu(m)
        self._tray.activated.connect(
            lambda r: widget.show() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self._tray.show()

    def _quit(self):
        self._widget._save_session()
        QTimer.singleShot(1500, self._app.quit)

    def run(self):
        sys.exit(self._app.exec())

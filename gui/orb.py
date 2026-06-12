import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient

from config.settings import FPS

C_IDLE = QColor(0, 200, 180)
C_TALK = QColor(255, 200, 60)
C_WARN = QColor(255, 80, 80)


class Particle:
    def __init__(self, cx: float, cy: float, state: str = "idle"):
        angle  = random.uniform(0, 2 * math.pi)
        speeds = {"idle": (0.3, 0.8), "talking": (1.2, 3.2), "warning": (1.8, 4.0)}
        radii  = {"idle": (1.0, 2.2), "talking": (1.5, 3.5), "warning": (2.0, 4.0)}
        colors = {"idle": C_IDLE, "talking": C_TALK, "warning": C_WARN}
        lo, hi = speeds.get(state, (0.3, 0.8))
        rl, rh = radii.get(state, (1.0, 2.2))
        speed  = random.uniform(lo, hi)
        self.r     = random.uniform(rl, rh)
        self.life  = random.uniform(0.4, 1.0)
        self.color = colors.get(state, C_IDLE)
        orbit  = random.uniform(8, 36)
        self.x = cx + math.cos(angle) * orbit * random.uniform(0.2, 1.0)
        self.y = cy + math.sin(angle) * orbit * random.uniform(0.2, 1.0)
        self.vx = math.cos(angle) * speed * random.uniform(-1, 1)
        self.vy = math.sin(angle) * speed - random.uniform(0.2, 1.0)
        self.max_life = self.life

    def update(self) -> bool:
        self.x  += self.vx
        self.y  += self.vy
        self.vy -= 0.04
        self.vx *= 0.98
        self.life -= 0.018
        return self.life > 0

    @property
    def alpha(self) -> float:
        return max(0.0, self.life / self.max_life)


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._state     = "idle"
        self._particles = []
        self._angle     = 0.0
        self._pulse     = 0.0
        self._pulse_d   = 0.02
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000 // FPS)

    def set_state(self, s: str):
        self._state = s

    def _tick(self):
        cx, cy = self.width() / 2, self.height() / 2
        for _ in range({"idle": 1, "talking": 4, "warning": 5}.get(self._state, 1)):
            self._particles.append(Particle(cx, cy, self._state))
        self._particles = [p for p in self._particles if p.update()]
        self._angle = (self._angle + 1.4) % 360
        self._pulse += self._pulse_d
        if self._pulse > 1 or self._pulse < 0:
            self._pulse_d *= -1
        self.update()

    def paintEvent(self, _):
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        cc = {"idle": C_IDLE, "talking": C_TALK, "warning": C_WARN}.get(self._state, C_IDLE)
        gr = 26 + self._pulse * 5
        g  = QRadialGradient(cx, cy, gr)
        go = QColor(cc); go.setAlpha(0)
        gi = QColor(cc); gi.setAlpha(35)
        g.setColorAt(0, gi); g.setColorAt(1, go)
        p.setBrush(QBrush(g))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - gr, cy - gr, gr * 2, gr * 2))
        cr = 13 + self._pulse * 2
        cg = QRadialGradient(cx - 2, cy - 2, cr)
        b  = QColor(cc); b.setAlpha(255)
        d  = QColor(cc); d.setAlpha(110)
        cg.setColorAt(0, b); cg.setColorAt(1, d)
        p.setBrush(QBrush(cg))
        p.drawEllipse(QRectF(cx - cr, cy - cr, cr * 2, cr * 2))
        if self._state == "talking":
            p.setPen(QPen(QColor(255, 200, 60, 55), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - 20, cy - 20, 40, 40))
            ox = cx + math.cos(math.radians(self._angle)) * 20
            oy = cy + math.sin(math.radians(self._angle)) * 20
            p.setBrush(QBrush(QColor(255, 200, 60, 180)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(ox - 2.5, oy - 2.5, 5, 5))
        for pt in self._particles:
            c = QColor(pt.color)
            c.setAlphaF(pt.alpha * 0.85)
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(pt.x - pt.r, pt.y - pt.r, pt.r * 2, pt.r * 2))
        p.end()

import os
from pathlib import Path

OLLAMA_URL    = "http://localhost:11434/api/chat"
OLLAMA_VISION = "http://localhost:11434/api/generate"
MODEL         = "gemma2:9b"
VISION_MODEL  = "llava:7b"

USER_NAME = "Arvindh"

CORNER_M = 18
WIDGET_W = 320
WIDGET_H = 420
FPS      = 60

SCREENSHOT_RETAIN_HOURS = 12

PIPER_EXE   = r"C:\piper\piper\piper.exe"
PIPER_MODEL = r"C:\piper\en_US-lessac-high.onnx"

WHISPER_MODEL = "base"

MIC_HOLD_KEY = 0x20
WAKE_WORD    = "karen"
MIC_TIMEOUT  = 10
AUDIO_RATE   = 16000
AUDIO_CHUNK  = 1024

DATA_DIR       = Path(os.path.expanduser("~")) / ".karen"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
SUMMARY_DIR    = DATA_DIR / "summaries"

for d in [DATA_DIR, SCREENSHOT_DIR, SUMMARY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

APP_REGISTRY: dict = {
    "chrome":        [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                      r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                      "google-chrome", "chromium-browser"],
    "firefox":       [r"C:\Program Files\Mozilla Firefox\firefox.exe",
                      r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
                      "firefox"],
    "edge":          [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                      r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                      "msedge"],
    "brave":         [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                      "brave-browser"],
    "opera":         ["opera"],
    "vscode":        ["code"],
    "pycharm":       ["pycharm"],
    "notepad":       ["notepad.exe"],
    "notepad++":     [r"C:\Program Files\Notepad++\notepad++.exe",
                      r"C:\Program Files (x86)\Notepad++\notepad++.exe"],
    "sublime":       [r"C:\Program Files\Sublime Text\sublime_text.exe", "subl"],
    "atom":          ["atom"],
    "vim":           ["vim", "gvim"],
    "terminal":      ["wt.exe", "cmd.exe"],
    "cmd":           ["cmd.exe"],
    "powershell":    ["powershell.exe"],
    "discord":       [r"C:\Users\%USERNAME%\AppData\Local\Discord\Update.exe", "discord"],
    "slack":         [r"C:\Users\%USERNAME%\AppData\Local\slack\slack.exe", "slack"],
    "telegram":      [r"C:\Users\%USERNAME%\AppData\Roaming\Telegram Desktop\Telegram.exe",
                      "telegram-desktop"],
    "whatsapp":      [r"C:\Users\%USERNAME%\AppData\Local\WhatsApp\WhatsApp.exe"],
    "zoom":          [r"C:\Users\%USERNAME%\AppData\Roaming\Zoom\bin\Zoom.exe", "zoom"],
    "teams":         [r"C:\Users\%USERNAME%\AppData\Local\Microsoft\Teams\current\Teams.exe", "teams"],
    "spotify":       [r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe", "spotify"],
    "vlc":           [r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                      r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe", "vlc"],
    "media player":  ["wmplayer.exe"],
    "word":          [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                      r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE"],
    "excel":         [r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
                      r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE"],
    "powerpoint":    [r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"],
    "outlook":       [r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE"],
    "obsidian":      [r"C:\Users\%USERNAME%\AppData\Local\Obsidian\Obsidian.exe", "obsidian"],
    "notion":        [r"C:\Users\%USERNAME%\AppData\Local\Programs\Notion\Notion.exe", "notion"],
    "task manager":  ["taskmgr.exe"],
    "explorer":      ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "settings":      ["ms-settings:"],
    "paint":         ["mspaint.exe"],
    "calculator":    ["calc.exe"],
    "snipping tool": ["SnippingTool.exe"],
    "postman":       [r"C:\Users\%USERNAME%\AppData\Local\Postman\Postman.exe", "postman"],
    "docker":        [r"C:\Program Files\Docker\Docker\Docker Desktop.exe", "docker"],
    "wsl":           ["wsl.exe"],
    "steam":         [r"C:\Program Files (x86)\Steam\steam.exe", "steam"],
    "git bash":      [r"C:\Program Files\Git\git-bash.exe"],
}

APP_ALIASES: dict = {
    "google chrome":        "chrome",
    "google":               "chrome",
    "microsoft edge":       "edge",
    "ms edge":              "edge",
    "vs code":              "vscode",
    "visual studio code":   "vscode",
    "code editor":          "vscode",
    "command prompt":       "cmd",
    "file manager":         "file explorer",
    "files":                "file explorer",
    "settings app":         "settings",
    "system settings":      "settings",
    "calc":                 "calculator",
    "ms paint":             "paint",
    "mspaint":              "paint",
    "windows media player": "media player",
    "task mgr":             "task manager",
    "taskmgr":              "task manager",
    "git-bash":             "git bash",
}

KAREN_SYSTEM = f"""You are KAREN, a desktop AI companion for {USER_NAME}.

Personality:
- You are like Karen from Spider-Man — warm, dry wit, genuinely invested in {USER_NAME}'s wellbeing
- General companion first. Talk about anything — tech, life, curiosity, jokes, ideas.
- Call him by name occasionally, not every message
- Direct. No fluff, no "Certainly!", no "Great question!", no emojis, no markdown
- Short responses unless he asks for detail. 2-4 sentences usually
- Occasionally dry humor — rarely, never forced

Rules:
- You know nothing about his life unless he tells you in this conversation
- If he says ignore a topic — drop it, zero nudging
- Only monitor productivity if he explicitly asks
- You run locally. Everything stays private.

Screen awareness:
- You periodically see summaries of what is on his screen
- Use this context naturally if relevant — don't announce it every message
- If you notice he has been on something unproductive for a while, you may mention it once, lightly"""

VISION_PROMPT = """Describe what is on this screen in 2-3 short sentences.
Focus on: what app is open, what content is visible, what the user appears to be doing.
Be factual and brief. No opinions."""

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>KAREN Weekly Report — {{ week }}</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0a0c12; color:#c8d2dc; font-family:'Consolas',monospace; padding:40px; }
  h1 { color:#00dcc8; letter-spacing:4px; font-size:1.4em; margin-bottom:4px; }
  .sub { color:#88a0a8; font-size:0.8em; margin-bottom:40px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px; }
  .card { background:#111520; border:1px solid rgba(0,220,200,0.15); border-radius:10px; padding:20px; }
  .card h2 { color:#00dcc8; font-size:0.85em; letter-spacing:2px; margin-bottom:14px; border-bottom:1px solid rgba(0,220,200,0.15); padding-bottom:8px; }
  .card.full { grid-column:1/-1; }
  .stat { display:flex; justify-content:space-between; margin-bottom:8px; font-size:0.82em; }
  .stat .val { color:#00dcc8; }
  .tag { display:inline-block; background:rgba(0,220,200,0.1); border:1px solid rgba(0,220,200,0.25); color:#00dcc8; border-radius:4px; padding:2px 8px; margin:3px; font-size:0.75em; }
  .pattern { background:rgba(255,200,60,0.06); border-left:2px solid rgba(255,200,60,0.4); padding:8px 12px; margin-bottom:8px; font-size:0.8em; color:#c8c080; border-radius:0 4px 4px 0; }
  .session { border-bottom:1px solid rgba(0,220,200,0.08); padding:10px 0; font-size:0.8em; }
  .session:last-child { border:none; }
  .session .ts { color:#88a0a8; font-size:0.75em; margin-bottom:4px; }
  .footer { text-align:center; color:#445566; font-size:0.72em; margin-top:40px; }
</style>
</head>
<body>
<h1>KAREN // WEEKLY REPORT</h1>
<div class="sub">{{ week }}  ·  generated {{ generated }}</div>
<div class="grid">
  <div class="card">
    <h2>SESSIONS</h2>
    <div class="stat"><span>Total sessions</span><span class="val">{{ session_count }}</span></div>
    <div class="stat"><span>Topics discussed</span><span class="val">{{ topic_count }}</span></div>
    <div class="stat"><span>Patterns observed</span><span class="val">{{ pattern_count }}</span></div>
    <div class="stat"><span>Screen summaries</span><span class="val">{{ summary_count }}</span></div>
  </div>
  <div class="card">
    <h2>TOPICS THIS WEEK</h2>
    {% for t in topics %}<span class="tag">{{ t }}</span>{% endfor %}
    {% if not topics %}<span style="color:#445566;font-size:0.8em;">No topics recorded yet.</span>{% endif %}
  </div>
  <div class="card full">
    <h2>OBSERVED PATTERNS</h2>
    {% for p in patterns %}<div class="pattern">{{ p }}</div>{% endfor %}
    {% if not patterns %}<span style="color:#445566;font-size:0.8em;">No patterns recorded yet.</span>{% endif %}
  </div>
  <div class="card full">
    <h2>SESSION SUMMARIES</h2>
    {% for s in sessions %}
    <div class="session"><div class="ts">{{ s.timestamp }}</div><div>{{ s.text }}</div></div>
    {% endfor %}
    {% if not sessions %}<span style="color:#445566;font-size:0.8em;">No sessions recorded yet.</span>{% endif %}
  </div>
  <div class="card full">
    <h2>SCREEN ACTIVITY SUMMARIES (LAST 20)</h2>
    {% for s in screen_summaries %}
    <div class="session"><div class="ts">{{ s.timestamp }}</div><div>{{ s.text }}</div></div>
    {% endfor %}
    {% if not screen_summaries %}<span style="color:#445566;font-size:0.8em;">No screen activity recorded yet.</span>{% endif %}
  </div>
</div>
<div class="footer">KAREN · local AI companion · all data private · {{ generated }}</div>
</body>
</html>"""

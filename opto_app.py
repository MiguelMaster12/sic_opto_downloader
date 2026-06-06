#!/usr/bin/env python3
"""
Opto Downloader by MiguelMaster12
===============

Interface Qt para o fluxo API-only:
  - scrape de séries via /content/item/{uuid}/list
  - resolução de MPD/license/PSSH via Kaltura multirequest
  - download final com pywidevine + yt-dlp + mp4decrypt + ffmpeg
"""

import os
import json
import queue
import re
import subprocess
import sys
import threading
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QEvent, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPen, QPixmap, QTextCharFormat, QTextCursor
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAS_QT_MULTIMEDIA = True
except Exception:
    QAudioOutput = None
    QMediaPlayer = None
    QVideoWidget = None
    HAS_QT_MULTIMEDIA = False

import opto_api_media_resolver as media
import opto_api_scraper as series_api


SUBPROCESS_KW = {}
if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
    SUBPROCESS_KW["creationflags"] = subprocess.CREATE_NO_WINDOW

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "downloads"
CONFIG_DIR = SCRIPT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "sic_opto_config.json"
SECRETS_DIR = SCRIPT_DIR / "secrets"
STATE_DIR = SCRIPT_DIR / "state"


def _detect_version() -> str:
    # 1. Explicit version file next to script
    for name in ("VERSION", "version.txt", "version"):
        vf = SCRIPT_DIR / name
        if vf.exists():
            v = vf.read_text(encoding="utf-8").strip().lstrip("v")
            if v:
                return v
    # 2. Git tag
    try:
        import subprocess as _sp
        out = _sp.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=SCRIPT_DIR, stderr=_sp.DEVNULL, text=True, **SUBPROCESS_KW,
        ).strip().lstrip("v")
        if out:
            return out
    except Exception:
        pass
    return "1.0.0"


APP_VERSION = _detect_version()


def load_config():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_config(data):
    try:
        existing = load_config()
        existing.update(data)
        CONFIG_DIR.mkdir(exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


I18N = {
    "pt": {
        "episode": "Episódio",
        "series": "Série",
        "downloads": "Downloads",
        "player": "Player",
        "log": "Log",
        "preferences": "Preferências",
        "status": "Estado",
        "ready": "Pronto",
        "episode_title": "Download de Episódio",
        "episode_subtitle": "Analisa por API, escolhe qualidade e gera MP4 final.",
        "series_title": "Série",
        "series_subtitle": "Lista episódios pela API, seleciona e descarrega em lote.",
        "downloads_title": "Downloads",
        "downloads_subtitle": "Fila, progresso e estado dos ficheiros em curso.",
        "player_title": "Player",
        "player_subtitle": "Reproduz o episódio preparado em temporário, sem guardar MP4 final.",
        "log_title": "Log",
        "log_subtitle": "Saída dos processos e progresso.",
        "preferences_title": "Preferências",
        "preferences_subtitle": "Defaults da app e idioma.",
        "status_title": "Estado",
        "status_subtitle": "Ferramentas externas e Widevine.",
        "choose_language": "Escolhe o idioma da app",
        "choose_language_sub": "Podes alterar isto depois em Preferências.",
        "analyze": "Analisar",
        "load_episodes": "Carregar episódios",
        "select_all": "Selecionar tudo",
        "clear": "Limpar",
        "download_selected": "Download selecionados",
        "quality": "Qualidade",
        "batch_quality": "Qualidade do lote",
        "batch_quality_hint": "Aplicada a todos os episódios selecionados.",
        "choose_folder": " ... ",
        "download_mp4": "Download MP4",
        "play": "Play",
        "play_selected": "Play selecionados",
        "player_empty": "Ainda nada carregado para reprodução.",
        "player_preparing": "A preparar reprodução...",
        "player_ready": "Pronto para reproduzir.",
        "player_next": "Próximo",
        "player_open_external": "Abrir no player do sistema",
        "no_episode": "Ainda sem episódio analisado.",
        "no_downloads": "Ainda não há downloads nesta sessão.",
        "defaults": "Defaults",
        "default_folder": "Pasta de download predefinida",
        "default_quality": "Qualidade predefinida",
        "quality_fallback": "Se a qualidade escolhida não existir, usa automaticamente a inferior mais próxima.",
        "language": "Idioma da app",
        "save_preferences": "Guardar preferências",
        "tools": "Ferramentas",
        "verify": "Verificar",
        "not_checked": "Ainda não verificado.",
        "widevine": "Widevine .wvd",
        "refresh": "Atualizar",
        "show_wvd": "Mostrar geração .wvd",
        "hide_wvd": "Ocultar geração .wvd",
        "generate_wvd": "Gerar .wvd",
        "private_key": "Private key (.pem)",
        "client_id": "Client ID (.bin)",
        "wvd_output_fixed": "Saída fixa:",
        "choose_file": " ... ",
        "queue": "Fila ativa",
        "workers": "Workers simultâneos",
        "history": "Histórico",
        "pause": "Pausar",
        "resume": "Retomar",
        "cancel_all": "Cancelar downloads",
        "open": "Abrir",
        "cancel": "Cancelar",
        "pending": "Em espera",
        "paused": "Pausado",
        "cancelled": "Cancelado",
        "failed": "Falhado",
        "skipped": "Ignorado",
        "completed": "Concluído",
        "open_folder": "Abrir pasta",
        "open_downloads_folder": "Abrir pasta de downloads",
        "developed_by": "Desenvolvido por MiguelMaster12",
        "support": "Buy Me a Coffee",
    },
    "en": {
        "episode": "Episode",
        "series": "Series",
        "downloads": "Downloads",
        "player": "Player",
        "log": "Log",
        "preferences": "Preferences",
        "status": "Status",
        "ready": "Ready",
        "episode_title": "Episode Download",
        "episode_subtitle": "Analyze via API, choose quality and generate the final MP4.",
        "series_title": "Series",
        "series_subtitle": "List episodes via API, select and batch download.",
        "downloads_title": "Downloads",
        "downloads_subtitle": "Queue, progress and current file state.",
        "player_title": "Player",
        "player_subtitle": "Play a temporary prepared episode without saving a final MP4.",
        "log_title": "Log",
        "log_subtitle": "Process output and progress.",
        "preferences_title": "Preferences",
        "preferences_subtitle": "App defaults and language.",
        "status_title": "Status",
        "status_subtitle": "External tools and Widevine.",
        "choose_language": "Choose the app language",
        "choose_language_sub": "You can change this later in Preferences.",
        "analyze": "Analyze",
        "load_episodes": "Load episodes",
        "select_all": "Select all",
        "clear": "Clear",
        "download_selected": "Download selected",
        "quality": "Quality",
        "batch_quality": "Batch quality",
        "batch_quality_hint": "Applied to every selected episode.",
        "choose_folder": " ... ",
        "download_mp4": "Download MP4",
        "play": "Play",
        "play_selected": "Play selected",
        "player_empty": "Nothing loaded for playback yet.",
        "player_preparing": "Preparing playback...",
        "player_ready": "Ready to play.",
        "player_next": "Next",
        "player_open_external": "Open in system player",
        "no_episode": "No episode analyzed yet.",
        "no_downloads": "No downloads in this session yet.",
        "defaults": "Defaults",
        "default_folder": "Default download folder",
        "default_quality": "Default quality",
        "quality_fallback": "If the selected quality is unavailable, the closest lower quality is used automatically.",
        "language": "App language",
        "save_preferences": "Save preferences",
        "tools": "Tools",
        "verify": "Verify",
        "not_checked": "Not checked yet.",
        "widevine": "Widevine .wvd",
        "refresh": "Refresh",
        "show_wvd": "Show .wvd generation",
        "hide_wvd": "Hide .wvd generation",
        "generate_wvd": "Generate .wvd",
        "private_key": "Private key (.pem)",
        "client_id": "Client ID (.bin)",
        "wvd_output_fixed": "Fixed output:",
        "choose_file": " ... ",
        "queue": "Active queue",
        "workers": "Concurrent workers",
        "history": "History",
        "pause": "Pause",
        "resume": "Resume",
        "cancel_all": "Cancel downloads",
        "open": "Open",
        "cancel": "Cancel",
        "pending": "Queued",
        "paused": "Paused",
        "cancelled": "Cancelled",
        "failed": "Failed",
        "skipped": "Skipped",
        "completed": "Completed",
        "open_folder": "Open folder",
        "open_downloads_folder": "Open downloads folder",
        "developed_by": "Developed by MiguelMaster12",
        "support": "Buy Me a Coffee",
    },
}


def text_for(lang, key):
    return I18N.get(lang, I18N["pt"]).get(key, I18N["pt"].get(key, key))


def safe_folder_name(value):
    text = re.sub(r"[^\w\-_. ]", "_", value or "SIC_OPTO")
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "SIC_OPTO"

P = {
    "bg": "#F6F4EF",
    "surface": "#FFFFFF",
    "surface2": "#F0EDE7",
    "sidebar": "#ECE8DF",
    "line": "#DDD7CC",
    "line2": "#C9C0B4",
    "text": "#1F1D1A",
    "muted": "#756E66",
    "soft": "#9B9288",
    "accent": "#181613",
    "accent2": "#A36A2D",
    "ok": "#2D7A46",
    "warn": "#A36A2D",
    "err": "#B23B3B",
}


STYLE = f"""
QWidget {{
    background: {P["bg"]};
    color: {P["text"]};
    font-family: "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}
QLineEdit {{
    background: {P["surface"]};
    border: 1px solid {P["line"]};
    border-radius: 10px;
    min-height: 18px;
    padding: 10px 12px;
    selection-background-color: {P["accent"]};
    selection-color: white;
}}
QLineEdit:focus {{
    border-color: {P["accent2"]};
}}
QPushButton {{
    background: {P["surface"]};
    border: 1px solid {P["line"]};
    border-radius: 10px;
    min-height: 38px;
    padding: 0 14px;
    font-weight: 600;
}}

QPushButton:hover {{
    background: {P["surface2"]};
    border-color: {P["line2"]};
}}

QPushButton:disabled {{
    color: {P["soft"]};
    background: {P["surface2"]};
}}

QProgressBar {{
    background: {P["surface2"]};
    border: 1px solid {P["line"]};
    border-radius: 7px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {P["accent"]};
    border-radius: 6px;
}}
QTreeWidget {{
    background: {P["surface"]};
    border: 1px solid {P["line"]};
    border-radius: 12px;
    padding: 8px;
}}
QTreeWidget::item {{
    min-height: 28px;
}}
QTextEdit {{
    background: {P["surface"]};
    color: {P["text"]};
    border: 1px solid {P["line"]};
    border-radius: 12px;
    padding: 12px;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    selection-background-color: #E5D8C8;
    selection-color: {P["text"]};
}}
"""


def make_nav_icon(svg_path: Path, size: int = 18) -> "QIcon":
    """Return a QIcon with a normal (dark) and active/selected (white) pixmap."""
    icon = QIcon()
    if not svg_path.exists():
        return icon
    # Normal mode — let Qt render SVG at requested size (dark on transparent)
    normal_pix = QPixmap(str(svg_path)).scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    icon.addPixmap(normal_pix, QIcon.Mode.Normal, QIcon.State.Off)
    # Active/selected mode — recolour every opaque pixel to white
    white_pix = QPixmap(normal_pix.size())
    white_pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(white_pix)
    painter.drawPixmap(0, 0, normal_pix)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(white_pix.rect(), QColor("white"))
    painter.end()
    icon.addPixmap(white_pix, QIcon.Mode.Active,   QIcon.State.Off)
    icon.addPixmap(white_pix, QIcon.Mode.Selected, QIcon.State.Off)
    return icon



def set_primary(btn):
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {P["accent"]};
            color: white;
            border: 1px solid {P["accent"]};
            border-radius: 10px;
            min-height: 18px;
            padding: 10px 16px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: #2C2925;
        }}
        QPushButton:disabled {{
            background: {P["line2"]};
            border-color: {P["line2"]};
            color: #F7F3EC;
        }}
    """)


def set_secondary(btn):
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


def hline():
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {P['line']};")
    return line


def title(text, subtitle=""):
    box = QWidget()
    box.setStyleSheet("background: transparent;")
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(3)
    h = QLabel(text)
    h.setFont(QFont("", 24, QFont.Weight.Bold))
    h.setStyleSheet("background: transparent;")
    v.addWidget(h)
    if subtitle:
        s = QLabel(subtitle)
        s.setStyleSheet(f"background: transparent; color: {P['muted']};")
        v.addWidget(s)
    return box


class QualityPicker(QWidget):
    changed = Signal(str)

    _BTN_H = 42
    _PICKER_H = 48

    def __init__(self):
        super().__init__()
        self._value = "best"
        self._buttons = {}

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setFixedHeight(self._PICKER_H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(8)

        for label, value in (
            ("Best", "best"),
            ("1080p", "1080"),
            ("720p", "720"),
            ("540p", "540"),
            ("480p", "480"),
            ("360p", "360"),
        ):
            btn = QPushButton(label)
            btn.setFixedHeight(self._BTN_H)
            btn.setMinimumWidth(64)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked=False, v=value: self.set_value(v))
            layout.addWidget(btn)
            self._buttons[value] = btn

        layout.addStretch()
        self.set_value("best")

    def value(self):
        return self._value

    def _style_active(self):
        return f"""
            QPushButton {{
                background: {P["accent"]};
                color: white;
                border: 1px solid {P["accent"]};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background: #2C2925;
            }}
        """

    def _style_inactive(self):
        return f"""
            QPushButton {{
                background: {P["surface"]};
                color: {P["text"]};
                border: 1px solid {P["line"]};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background: {P["surface2"]};
                border-color: {P["line2"]};
            }}
        """

    def set_value(self, value):
        self._value = value
        for val, btn in self._buttons.items():
            btn.setStyleSheet(
                self._style_active() if val == value else self._style_inactive()
            )
            btn.setFixedHeight(self._BTN_H)
        self.changed.emit(value)


class LanguagePicker(QualityPicker):
    def __init__(self):
        QWidget.__init__(self)
        self._value = "pt"
        self._buttons = {}

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setFixedHeight(self._PICKER_H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(8)

        for label, value in (("Português", "pt"), ("English", "en")):
            btn = QPushButton(label)
            btn.setFixedHeight(self._BTN_H)
            btn.setMinimumWidth(88)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked=False, v=value: self.set_value(v))
            layout.addWidget(btn)
            self._buttons[value] = btn

        layout.addStretch()
        self.set_value("pt")

class LanguageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = "pt"
        self.setModal(True)
        self.setWindowTitle("Opto Downloader")
        self.setFixedSize(460, 260)
        self.setStyleSheet(STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(6)

        title_lbl = QLabel(text_for("pt", "choose_language"))
        title_lbl.setFont(QFont("", 17, QFont.Weight.Bold))
        title_lbl.setStyleSheet("background: transparent;")
        subtitle = QLabel(text_for("pt", "choose_language_sub"))
        subtitle.setStyleSheet(f"color: {P['muted']}; background: transparent;")
        root.addWidget(title_lbl)
        root.addWidget(subtitle)
        root.addSpacing(16)

        row = QHBoxLayout()
        row.setSpacing(12)
        for flag, label, value in (("🇵🇹", "Português", "pt"), ("🇬🇧", "English", "en")):
            btn = QPushButton(f"{flag}  {label}")
            btn.setFixedHeight(52)
            btn.setFont(QFont("", 14, QFont.Weight.Bold))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {P["surface"]};
                    border: 1px solid {P["line"]};
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {P["accent"]};
                    color: white;
                    border-color: {P["accent"]};
                }}
            """)
            btn.clicked.connect(lambda checked=False, v=value: self._choose(v))
            row.addWidget(btn)
        root.addLayout(row)

    def _choose(self, value):
        self.selected = value
        self.accept()


class Spinner(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(44, 44)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(45)

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._angle = (self._angle - 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(P["accent"]))
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(6, 6, 32, 32, self._angle * 16, 285 * 16)


class LoadingOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: {P["surface"]};
                border: 1px solid {P["line"]};
            }}
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background: rgba(246, 244, 239, 205);")
        self.spinner = Spinner()
        self.label = QLabel("A carregar...")
        self.label.setFont(QFont("", 13, QFont.Weight.Bold))
        self.label.setStyleSheet("background: transparent; border: none;")
        holder = QFrame(self)
        holder.setStyleSheet(f"""
            QFrame {{
                background: {P["surface"]};
                border: 1px solid {P["line"]};
                border-radius: 18px;
            }}
        """)
        self.holder = holder
        v = QVBoxLayout(holder)
        v.setContentsMargins(34, 28, 34, 28)
        v.setSpacing(12)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def attach(self, parent):
        self.setParent(parent)
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.raise_()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(watched.rect())
            self._position_holder()
        return super().eventFilter(watched, event)

    def _position_holder(self):
        w, h = 330, 150
        self.holder.setGeometry((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    def start(self, text):
        self.label.setText(text)
        self.setGeometry(self.parentWidget().rect())
        self._position_holder()
        self.show()
        self.raise_()
        self.spinner.start()

    def stop(self):
        self.spinner.stop()
        self.hide()


class VideoLoadingOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(5, 5, 5, 170); border-radius: 14px;")
        self.spinner = Spinner()
        self.label = QLabel("A preparar...")
        self.label.setFont(QFont("", 13, QFont.Weight.Bold))
        self.label.setStyleSheet("background: transparent; color: white; border: none;")
        holder = QWidget(self)
        holder.setStyleSheet("background: transparent; border: none;")
        self.holder = holder
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def attach(self, parent):
        self.setParent(parent)
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.raise_()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(watched.rect())
            self._position_holder()
        return super().eventFilter(watched, event)

    def _position_holder(self):
        w, h = 280, 110
        self.holder.setGeometry((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    def start(self, text):
        self.label.setText(text)
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self._position_holder()
        self.show()
        self.raise_()
        self.spinner.start()

    def stop(self):
        self.spinner.stop()
        self.hide()


class BusyBar(QFrame):
    def __init__(self):
        super().__init__()
        self.hide()
        row = QHBoxLayout(self)
        self.label = QLabel("A trabalhar...")
        self.bar = QProgressBar()

    def start(self, text):
        pass

    def stop(self):
        pass


class DownloadRow(QFrame):
    open_requested = Signal(int)
    cancel_requested = Signal(int)

    def __init__(self, label, row_index, lang="pt"):
        super().__init__()
        self.row_index = row_index
        self.lang = lang
        self.path = ""
        self.setStyleSheet(f"""
            QFrame {{
                background: {P["surface"]};
                border: none;
                border-bottom: 1px solid {P["line"]};
                border-radius: 0;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QProgressBar {{
                background: {P["surface2"]};
                border: 1px solid {P["line"]};
                border-radius: 7px;
            }}
            QProgressBar::chunk {{
                background: {P["accent"]};
                border-radius: 6px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.title = QLabel(label)
        self.title.setFont(QFont("", 12, QFont.Weight.Bold))
        self.title.setMinimumWidth(240)
        layout.addWidget(self.title, 2)

        mid = QVBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(4)
        self.status = QLabel("Em espera")
        self.status.setStyleSheet(f"color: {P['muted']};")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        mid.addWidget(self.status)
        mid.addWidget(self.progress)
        layout.addLayout(mid, 3)

        meta_box = QVBoxLayout()
        meta_box.setContentsMargins(0, 0, 0, 0)
        meta_box.setSpacing(2)
        self.percent = QLabel("0%")
        self.meta = QLabel("Velocidade: --  ·  ETA: --")
        self.percent.setStyleSheet(f"color: {P['muted']};")
        self.meta.setStyleSheet(f"color: {P['muted']};")
        self.percent.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.meta.setAlignment(Qt.AlignmentFlag.AlignRight)
        meta_box.addWidget(self.percent)
        meta_box.addWidget(self.meta)
        layout.addLayout(meta_box, 2)

        self.btn_cancel = QPushButton("×")
        self.btn_cancel.setToolTip(text_for(lang, "cancel"))
        self.btn_open = QPushButton(text_for(lang, "open"))
        self.btn_open.hide()
        for btn in (self.btn_cancel, self.btn_open):
            btn.setFixedHeight(32)
            set_secondary(btn)
            layout.addWidget(btn)
        self.btn_cancel.setFixedWidth(34)
        self.btn_cancel.clicked.connect(lambda: self.cancel_requested.emit(self.row_index))
        self.btn_open.clicked.connect(lambda: self.open_requested.emit(self.row_index))

    def update_state(self, status=None, percent=None, speed="", eta=""):
        if status is not None:
            self.status.setText(status)
        if percent is not None:
            pct = max(0, min(100, int(percent)))
            self.progress.setValue(pct)
            self.percent.setText(f"{pct}%")
            if pct >= 100:
                self.meta.setText("")
                return
        if speed or eta:
            self.meta.setText(f"Velocidade: {speed or '--'}  ·  ETA: {eta or '--'}")

    def mark_done(self, path):
        self.path = path
        self.update_state(text_for(self.lang, "completed"), 100)
        self.btn_open.show()
        self.btn_cancel.hide()

    def mark_cancelled(self):
        self.update_state(text_for(self.lang, "cancelled"), self.progress.value())
        self.meta.setText("")
        self.btn_cancel.hide()

    def mark_failed(self, message):
        self.update_state(text_for(self.lang, "failed"), self.progress.value())
        self.meta.setText(message[:120] if message else "")
        self.btn_cancel.hide()

    def mark_skipped(self, path):
        self.path = path
        self.update_state(text_for(self.lang, "skipped"), 100)
        self.meta.setText("")
        self.btn_open.show()
        self.btn_cancel.hide()


class DownloadGroup(QFrame):
    def __init__(self, label):
        super().__init__()
        self.expanded = True
        self.setStyleSheet(f"""
            QFrame {{
                background: {P["surface"]};
                border: 1px solid {P["line"]};
                border-radius: 14px;
            }}
            QPushButton {{
                background: transparent;
                color: {P["text"]};
                border: none;
                text-align: left;
                padding: 10px 12px;
                font-weight: 700;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QPushButton()
        self.header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header.clicked.connect(self.toggle)
        layout.addWidget(self.header)

        self.body = QWidget()
        self.body.setStyleSheet("background: transparent; border: none;")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        layout.addWidget(self.body)
        self.set_label(label)

    def set_label(self, label):
        arrow = "▾" if self.expanded else "▸"
        self.header.setText(f"{arrow}  {label}")

    def toggle(self):
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)
        text = self.header.text().split("  ", 1)[-1]
        self.set_label(text)

    def add_row(self, row):
        self.body_layout.addWidget(row)


class LogBox(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

    def append_line(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        lowered = text.lower()
        if "erro" in lowered or "falhou" in lowered:
            fmt.setForeground(QColor(P["err"]))
        elif "concluído" in lowered or "ok" in lowered or "obtidos" in lowered:
            fmt.setForeground(QColor(P["ok"]))
        elif "download" in lowered or "série" in lowered:
            fmt.setForeground(QColor(P["accent2"]))
        else:
            fmt.setForeground(QColor(P["text"]))
        cursor.insertText(text.rstrip() + "\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class AnalyzeEpisodeThread(QThread):
    done = Signal(dict)
    log_signal = Signal(str)
    error = Signal(str)

    def __init__(self, episode):
        super().__init__()
        self.episode = episode

    def run(self):
        try:
            self.log_signal.emit("A analisar episódio via API...")
            data = media.resolve_episode_media(self.episode)
            self.log_signal.emit(f"MPD e license resolvidos: {data.get('title')}")
            self.done.emit(data)
        except Exception as exc:
            self.error.emit(str(exc))


class AnalyzeSeriesThread(QThread):
    done = Signal(dict)
    log_signal = Signal(str)
    error = Signal(str)

    def __init__(self, series_url):
        super().__init__()
        self.series_url = series_url

    def run(self):
        previous = series_api.log
        series_api.log = lambda msg: self.log_signal.emit(str(msg).strip())
        try:
            data = series_api.scrape_series(self.series_url)
            self.done.emit(data)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            series_api.log = previous


class DownloadThread(QThread):
    done = Signal(list)
    log_signal = Signal(str)
    progress_signal = Signal(int, str, float, str, str)
    row_done = Signal(int, str)
    row_cancelled = Signal(int)
    row_failed = Signal(int, str)
    row_skipped = Signal(int, str)
    error = Signal(str)

    def __init__(self, episodes, output_dir, quality, worker_count=2):
        super().__init__()
        self.episodes = list(episodes)
        self.output_dir = output_dir
        self.quality = quality
        self.worker_count = max(1, min(int(worker_count or 1), 6))
        self.max_attempts = 6
        self.cancel_requested = False
        self.paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._ready_work = None
        self.cancelled_rows = set()
        self._cancel_lock = threading.Lock()

    def cancel(self):
        self.cancel_requested = True
        self._pause_event.set()
        if self._ready_work is not None:
            for _ in range(self.worker_count):
                self._ready_work.put(None)

    def pause(self):
        self.paused = True
        self._pause_event.clear()

    def resume(self):
        self.paused = False
        self._pause_event.set()

    def cancel_row(self, row_index):
        with self._cancel_lock:
            self.cancelled_rows.add(row_index)

    def _is_row_cancelled(self, row_index):
        with self._cancel_lock:
            return row_index in self.cancelled_rows

    def _keys_for(self, data):
        wvds = media.find_wvd_files()
        if not wvds:
            raise RuntimeError(".wvd não encontrado.")
        keys = media.get_keys_with_pywidevine(data["pssh"], data["license_url"], str(wvds[0]))
        if not keys:
            raise RuntimeError("Não foi possível obter keys.")
        return keys

    def _wait_if_paused(self):
        while self.paused and not self.cancel_requested:
            self._pause_event.wait(0.2)

    def _retry_wait(self, attempt):
        end_at = time.time() + min(0.5 * attempt, 2.0)
        while not self.cancel_requested and time.time() < end_at:
            self._pause_event.wait(0.1)

    def _episode_output_dir(self, ep):
        return ep.get("output_dir") or self.output_dir

    def _existing_output_path(self, ep, output_name):
        path = media.final_output_path(self._episode_output_dir(ep), output_name)
        return path if path.exists() and path.is_file() else None

    def run(self):
        previous = media.log
        previous_progress = media.PROGRESS_CALLBACK
        previous_cancel = media.CANCEL_CALLBACK
        media.log = lambda msg: self.log_signal.emit(str(msg).strip())
        outputs = []
        outputs_lock = threading.Lock()
        prepare_work = queue.Queue()
        ready_work = queue.Queue()
        self._ready_work = ready_work
        for ep in self.episodes:
            prepare_work.put(ep)

        def prepare_episode(ep):
            label = ep.get("label") or ep.get("url") or ep.get("episode") or "episódio"
            row_index = ep.get("_row_index", 0)
            if self._is_row_cancelled(row_index):
                self.row_cancelled.emit(row_index)
                return None
            initial_output_name = ep.get("output_name")
            if initial_output_name:
                existing = self._existing_output_path(ep, initial_output_name)
                if existing:
                    self.progress_signal.emit(row_index, "Já existe, ignorado", 100, "", "")
                    self.row_skipped.emit(row_index, str(existing))
                    return None
            last_error = None
            for attempt in range(1, self.max_attempts + 1):
                if self.cancel_requested:
                    return None
                if self._is_row_cancelled(row_index):
                    self.row_cancelled.emit(row_index)
                    return None
                try:
                    self.log_signal.emit(f"A preparar keys em background: {label} (tentativa {attempt}/{self.max_attempts})")
                    self.progress_signal.emit(row_index, f"A resolver MPD/license ({attempt}/{self.max_attempts})", 0, "", "")
                    data = ep.get("resolved") or media.resolve_episode_media(ep["url"])
                    if self.cancel_requested or self._is_row_cancelled(row_index):
                        self.row_cancelled.emit(row_index)
                        return None
                    self.progress_signal.emit(row_index, f"A obter keys ({attempt}/{self.max_attempts})", 3, "", "")
                    keys = self._keys_for(data)
                    output_name = ep.get("output_name") or media.default_output_name(data)
                    existing = self._existing_output_path(ep, output_name)
                    if existing:
                        self.progress_signal.emit(row_index, "Já existe, ignorado", 100, "", "")
                        self.row_skipped.emit(row_index, str(existing))
                        return None
                    self.progress_signal.emit(row_index, "Pronto para download", 5, "", "")
                    return ep, data, keys, output_name
                except Exception as exc:
                    last_error = exc
                    self.log_signal.emit(f"Falhou preparação de {label} ({attempt}/{self.max_attempts}): {exc}")
                    if attempt < self.max_attempts:
                        self._retry_wait(attempt)
            self.row_failed.emit(row_index, str(last_error or "Falha ao preparar episódio."))
            return None

        def process_download(prepared):
            ep, data, keys, output_name = prepared
            label = ep.get("label") or ep.get("url") or ep.get("episode") or "episódio"
            row_index = ep.get("_row_index", 0)
            if self._is_row_cancelled(row_index):
                self.row_cancelled.emit(row_index)
                return

            stream_progress = {"vídeo": 0.0, "áudio": 0.0}

            def progress_callback(event, data, row_index=row_index, stream_progress=stream_progress):
                if event == "stage":
                    self.progress_signal.emit(
                        row_index,
                        data.get("status", "A processar"),
                        float(data.get("percent") or 0),
                        "",
                        "",
                    )
                    return
                if event != "download":
                    return
                stream = data.get("stream", "")
                pct = float(data.get("percent") or 0)
                if stream in stream_progress:
                    stream_progress[stream] = pct
                combined = 5 + (sum(stream_progress.values()) / len(stream_progress)) * 0.65
                self.progress_signal.emit(
                    row_index,
                    f"Download {stream}".strip(),
                    combined,
                    data.get("speed", ""),
                    data.get("eta", ""),
                )

            media.set_thread_progress_callback(progress_callback)
            media.set_thread_cancel_callback(lambda row_index=row_index: self.cancel_requested or self._is_row_cancelled(row_index))
            try:
                last_error = None
                for attempt in range(1, self.max_attempts + 1):
                    if self.cancel_requested:
                        return
                    if self._is_row_cancelled(row_index):
                        self.row_cancelled.emit(row_index)
                        return
                    try:
                        self.log_signal.emit(f"A descarregar {label} (tentativa {attempt}/{self.max_attempts})")
                        path = media.download_decrypt_mux(
                            data["mpd_url"],
                            keys,
                            self._episode_output_dir(ep),
                            output_name,
                            self.quality,
                        )
                        if self._is_row_cancelled(row_index):
                            self.row_cancelled.emit(row_index)
                            return
                        self.progress_signal.emit(row_index, "Concluído", 100, "", "")
                        self.row_done.emit(row_index, path)
                        with outputs_lock:
                            outputs.append(path)
                        return
                    except Exception as exc:
                        last_error = exc
                        if self._is_row_cancelled(row_index) and not self.cancel_requested:
                            self.row_cancelled.emit(row_index)
                            return
                        self.log_signal.emit(f"Falhou download de {label} ({attempt}/{self.max_attempts}): {exc}")
                        if attempt < self.max_attempts:
                            self.progress_signal.emit(row_index, f"A tentar novamente ({attempt + 1}/{self.max_attempts})", 5, "", "")
                            self._retry_wait(attempt)
                self.row_failed.emit(row_index, str(last_error or "Falha no download."))
            except Exception:
                if self._is_row_cancelled(row_index) and not self.cancel_requested:
                    self.row_cancelled.emit(row_index)
                    return
                raise
            finally:
                media.set_thread_progress_callback(None)
                media.set_thread_cancel_callback(None)

        def prepare_worker():
            while not self.cancel_requested:
                self._wait_if_paused()
                if self.cancel_requested:
                    return
                try:
                    ep = prepare_work.get_nowait()
                except queue.Empty:
                    return
                try:
                    prepared = prepare_episode(ep)
                    if prepared is not None:
                        ready_work.put(prepared)
                except Exception as exc:
                    row_index = ep.get("_row_index", 0)
                    self.row_failed.emit(row_index, str(exc))
                finally:
                    prepare_work.task_done()

        def download_worker():
            while True:
                self._wait_if_paused()
                if self.cancel_requested:
                    return
                try:
                    prepared = ready_work.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    if prepared is None:
                        return
                    process_download(prepared)
                except Exception as exc:
                    ep = prepared[0] if prepared else {}
                    row_index = ep.get("_row_index", 0)
                    self.row_failed.emit(row_index, str(exc))
                finally:
                    ready_work.task_done()

        try:
            count = min(self.worker_count, len(self.episodes))
            prefetch_count = min(max(1, count), 2)
            self.log_signal.emit(f"Fila iniciada: {len(self.episodes)} episódio(s)")
            self.log_signal.emit(f"Workers ativos: {count} · prefetch keys: {prefetch_count}")

            preparers = []
            for _ in range(prefetch_count):
                thread = threading.Thread(target=prepare_worker, daemon=True)
                preparers.append(thread)
                thread.start()

            downloaders = []
            for _ in range(count):
                thread = threading.Thread(target=download_worker, daemon=True)
                downloaders.append(thread)
                thread.start()

            for thread in preparers:
                thread.join()

            for _ in downloaders:
                ready_work.put(None)
            for thread in downloaders:
                thread.join()

            self.done.emit(outputs)
        except Exception as exc:
            if self.cancel_requested:
                self.done.emit(outputs)
            else:
                self.error.emit(str(exc))
        finally:
            media.log = previous
            media.set_progress_callback(previous_progress)
            media.set_cancel_callback(previous_cancel)
            self._ready_work = None


class PlayerPrepareThread(QThread):
    ready = Signal(int, str, str, str)
    log_signal = Signal(str)
    progress_signal = Signal(int, str)
    error = Signal(int, str)

    def __init__(self, episode, quality, index):
        super().__init__()
        self.episode = episode
        self.quality = quality
        self.index = index
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def _keys_for(self, data):
        wvds = media.find_wvd_files()
        if not wvds:
            raise RuntimeError(".wvd não encontrado.")
        keys = media.get_keys_with_pywidevine(data["pssh"], data["license_url"], str(wvds[0]))
        if not keys:
            raise RuntimeError("Não foi possível obter keys.")
        return keys

    def run(self):
        previous = media.log
        previous_progress = media.PROGRESS_CALLBACK
        previous_cancel = media.CANCEL_CALLBACK
        temp_dir = tempfile.mkdtemp(prefix="sic_opto_player_")
        media.log = lambda msg: self.log_signal.emit(str(msg).strip())
        media.set_cancel_callback(lambda: self.cancel_requested)

        def progress_callback(event, data):
            if event == "stage":
                self.progress_signal.emit(self.index, data.get("status", "A preparar"))
            elif event == "download":
                stream = data.get("stream", "")
                pct = data.get("percent", 0)
                self.progress_signal.emit(self.index, f"Download {stream}: {pct:.0f}%".strip())

        media.set_progress_callback(progress_callback)
        try:
            self.progress_signal.emit(self.index, "A resolver MPD/license")
            data = self.episode.get("resolved") or media.resolve_episode_media(self.episode["url"])
            if self.cancel_requested:
                raise RuntimeError("Preparação cancelada.")
            self.progress_signal.emit(self.index, "A obter keys")
            keys = self._keys_for(data)
            output_name = self.episode.get("output_name") or media.default_output_name(data)
            path = media.download_decrypt_mux(
                data["mpd_url"],
                keys,
                temp_dir,
                output_name,
                self.quality,
            )
            title_text = self.episode.get("label") or data.get("title") or Path(path).name
            self.ready.emit(self.index, path, title_text, temp_dir)
        except Exception as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if not self.cancel_requested:
                self.error.emit(self.index, str(exc))
        finally:
            media.log = previous
            media.set_progress_callback(previous_progress)
            media.set_cancel_callback(previous_cancel)


class GenerateWvdThread(QThread):
    done = Signal(str)
    log_signal = Signal(str)
    error = Signal(str)

    def __init__(self, private_key, client_id, output_dir):
        super().__init__()
        self.private_key = private_key
        self.client_id = client_id
        self.output_dir = output_dir

    def run(self):
        try:
            output_dir = Path(self.output_dir).expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            before = {p.resolve() for p in output_dir.glob("*.wvd")}
            pywidevine_bin = media.resolve_tool("pywidevine")
            if pywidevine_bin:
                cmd = [
                    pywidevine_bin, "create-device",
                    "-k", self.private_key,
                    "-c", self.client_id,
                    "-t", "ANDROID",
                    "-l", "3",
                    "-o", str(output_dir),
                ]
            else:
                cmd = [
                    sys.executable,
                    "-c",
                    "from pywidevine.main import main; main()",
                    "create-device",
                    "-k", self.private_key,
                    "-c", self.client_id,
                    "-t", "ANDROID",
                    "-l", "3",
                    "-o", str(output_dir),
                ]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                **SUBPROCESS_KW,
            )
            for line in proc.stdout or []:
                self.log_signal.emit(line.rstrip())
            code = proc.wait()
            if code != 0:
                raise RuntimeError(f"pywidevine terminou com código {code}.")
            after = {p.resolve() for p in output_dir.glob("*.wvd")}
            created = sorted(after - before)
            if created:
                self.done.emit(str(created[-1]))
                return
            wvds = sorted(output_dir.glob("*.wvd"), key=lambda p: p.stat().st_mtime)
            self.done.emit(str(wvds[-1]) if wvds else "")
        except Exception as exc:
            self.error.emit(str(exc))


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Opto Downloader")
        self.resize(1120, 760)
        self.setMinimumSize(980, 640)
        self.setStyleSheet(STYLE)
        # Window icon
        for _name in ("app-icon.png", "app-icon.ico"):
            _p = SCRIPT_DIR / "assets" / _name
            if _p.exists():
                self.setWindowIcon(QIcon(str(_p)))
                break
        self.config = load_config()
        if not self.config.get("language"):
            dlg = LanguageDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.config["language"] = dlg.selected
                save_config({"language": dlg.selected})
        self.lang = self.config.get("language", "pt")
        self._episode_data = None
        self._series_data = None
        self._threads = []
        self.download_rows = []
        self.current_download_thread = None
        self.current_player_thread = None
        self.player_queue = []
        self.player_playlist = []
        self.player_index = -1
        self.player_cache = {}
        self.player_prefetch_threads = {}
        self.player_temp_dirs = []
        self.player_current_path = ""
        self.player_loaded_path = ""
        self.player_quality = "best"
        self.player_duration = 0
        self.player_seeking = False
        self.downloads_cancelled_by_user = False
        self.media_player = None
        self.audio_output = None
        self._build()

    def t(self, key):
        return text_for(self.lang, key)

    def closeEvent(self, event):
        if self.current_player_thread and self.current_player_thread.isRunning():
            self.current_player_thread.cancel()
        for thread in list(self.player_prefetch_threads.values()):
            if thread.isRunning():
                thread.cancel()
        if self.current_download_thread and self.current_download_thread.isRunning():
            self.current_download_thread.cancel()
        if self.media_player:
            self.media_player.stop()
        for temp_dir in list(self.player_temp_dirs):
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.player_temp_dirs.clear()
        event.accept()

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._sidebar()
        layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.episode_page_widget = self._episode_page()
        self.series_page_widget = self._series_page()
        self.downloads_page_widget = self._downloads_page()
        self.player_page_widget = self._player_page()
        self.log_page_widget = self._log_page()
        self.preferences_page_widget = self._preferences_page()
        self.status_page_widget = self._status_page()
        self.stack.addWidget(self.episode_page_widget)
        self.stack.addWidget(self.series_page_widget)
        self.stack.addWidget(self.downloads_page_widget)
        self.stack.addWidget(self.player_page_widget)
        self.stack.addWidget(self.log_page_widget)
        self.stack.addWidget(self.preferences_page_widget)
        self.stack.addWidget(self.status_page_widget)
        layout.addWidget(self.stack, 1)
        self.overlay_episode = LoadingOverlay()
        self.overlay_episode.attach(self.episode_page_widget)
        self.overlay_series = LoadingOverlay()
        self.overlay_series.attach(self.series_page_widget)
        self.overlay_downloads = LoadingOverlay()
        self.overlay_downloads.attach(self.downloads_page_widget)
        self.overlay_player = LoadingOverlay()
        self.overlay_player.attach(self.player_page_widget)
        self.overlay_preferences = LoadingOverlay()
        self.overlay_preferences.attach(self.preferences_page_widget)
        self.overlay_status = LoadingOverlay()
        self.overlay_status.attach(self.status_page_widget)
        self._nav(0)

    def _sidebar(self):
        side = QFrame()
        side.setFixedWidth(220)
        side.setStyleSheet(f"QFrame {{ background: {P['sidebar']}; border-right: 1px solid {P['line']}; }}")
        v = QVBoxLayout(side)
        v.setContentsMargins(18, 22, 18, 18)
        v.setSpacing(8)

        # ── Logo + brand ──────────────────────────────────────────────
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(10)

        logo = QLabel()
        logo.setFixedSize(38, 38)
        logo.setStyleSheet("background: transparent;")
        _icon_path = SCRIPT_DIR / "assets" / "app-icon.png"
        if not _icon_path.exists():
            _icon_path = SCRIPT_DIR / "assets" / "app-icon.ico"
        if _icon_path.exists():
            _pix = QPixmap(str(_icon_path)).scaled(
                38, 38,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo.setPixmap(_pix)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo.setStyleSheet(f"""
                background: {P["accent"]};
                border-radius: 10px;
                color: white;
                font-size: 18px;
                font-weight: 800;
            """)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setText("▶")
        brand_row.addWidget(logo)

        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(0)
        brand_name = QLabel("Opto")
        brand_name.setFont(QFont("", 16, QFont.Weight.Bold))
        brand_name.setStyleSheet("background: transparent;")
        brand_sub = QLabel("Downloader")
        brand_sub.setStyleSheet(f"background: transparent; color: {P['muted']}; font-size: 11px;")
        brand_text.addWidget(brand_name)
        brand_text.addWidget(brand_sub)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        v.addLayout(brand_row)

        v.addSpacing(16)

        self.nav_buttons = []
        self._nav_icons = []
        nav_svg_names = ("episode", "series", "downloads", "player", "log", "preferences", "status")
        nav_labels = (
            self.t('episode'),
            self.t('series'),
            self.t('downloads'),
            self.t('player'),
            self.t('log'),
            self.t('preferences'),
            self.t('status'),
        )
        for idx, (svg_name, label) in enumerate(zip(nav_svg_names, nav_labels)):
            btn = QPushButton(f"  {label}")
            btn.setFixedHeight(42)
            btn.setStyleSheet("text-align: left; padding-left: 10px;")
            svg_path = SCRIPT_DIR / "assets" / "icons" / f"{svg_name}.svg"
            nav_icon = make_nav_icon(svg_path)
            self._nav_icons.append(nav_icon)
            if not nav_icon.isNull():
                btn.setIcon(nav_icon)
                btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda checked=False, i=idx: self._nav(i))
            set_secondary(btn)
            v.addWidget(btn)
            self.nav_buttons.append(btn)

        v.addStretch()

        self.status = QLabel(self.t("ready"))
        self.status.setStyleSheet(f"background: transparent; color: {P['muted']}; font-size: 11px;")
        v.addWidget(self.status)
        return side

    def _nav(self, index):
        self.stack.setCurrentIndex(index)
        nav_icons = getattr(self, "_nav_icons", [])
        for i, btn in enumerate(getattr(self, "nav_buttons", [])):
            icon = nav_icons[i] if i < len(nav_icons) else QIcon()
            if i == index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        padding-left: 10px;
                        background: {P["accent"]};
                        color: white;
                        border-color: {P["accent"]};
                    }}
                """)
                # Force white pixmap by setting the Active pixmap as Normal for this button
                if not icon.isNull():
                    white_pix = icon.pixmap(QSize(18, 18), QIcon.Mode.Active)
                    btn.setIcon(QIcon(white_pix))
            else:
                btn.setStyleSheet("text-align: left; padding-left: 10px;")
                if not icon.isNull():
                    btn.setIcon(icon)

    def _page(self):
        page = QWidget()
        page.setStyleSheet(f"background: {P['bg']};")
        v = QVBoxLayout(page)
        v.setContentsMargins(34, 28, 34, 28)
        v.setSpacing(16)
        return page, v

    def _episode_page(self):
        page, v = self._page()
        v.addWidget(title(self.t("episode_title"), self.t("episode_subtitle")))
        self.busy_episode = BusyBar()
        v.addWidget(self.busy_episode)

        card = self._card()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 18, 18, 18)
        cv.setSpacing(12)
        self.episode_input = QLineEdit()
        self.episode_input.setPlaceholderText("URL ou UUID do episódio" if self.lang == "pt" else "Episode URL or UUID")
        cv.addWidget(self.episode_input)

        row = QHBoxLayout()
        self.btn_episode_analyze = QPushButton(self.t("analyze"))
        set_primary(self.btn_episode_analyze)
        self.btn_episode_analyze.clicked.connect(self._analyze_episode)
        row.addWidget(self.btn_episode_analyze)
        row.addStretch()
        cv.addLayout(row)

        self.episode_summary = QLabel(self.t("no_episode"))
        self.episode_summary.setWordWrap(True)
        self.episode_summary.setStyleSheet(
            f"color: {P['muted']}; background: transparent; border: none; padding: 0;"
        )
        cv.addWidget(self.episode_summary)
        v.addWidget(card)

        v.addWidget(self._download_controls(single=True))
        v.addStretch()
        self.episode_controls.hide()
        self.btn_episode_download.hide()
        self.btn_episode_play.hide()
        return page

    def _series_page(self):
        page, v = self._page()
        v.addWidget(title(self.t("series_title"), self.t("series_subtitle")))
        self.busy_series = BusyBar()
        v.addWidget(self.busy_series)

        top = self._card()
        tv = QVBoxLayout(top)
        tv.setContentsMargins(18, 18, 18, 18)
        tv.setSpacing(12)
        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("URL da série" if self.lang == "pt" else "Series URL")
        tv.addWidget(self.series_input)
        row = QHBoxLayout()
        self.btn_series_analyze = QPushButton(self.t("load_episodes"))
        set_primary(self.btn_series_analyze)
        self.btn_series_analyze.clicked.connect(self._analyze_series)
        row.addWidget(self.btn_series_analyze)
        row.addStretch()
        tv.addLayout(row)
        v.addWidget(top)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([self.t("episode"), "Duração" if self.lang == "pt" else "Duration", "URL"])
        self.tree.setColumnWidth(0, 360)
        self.tree.setColumnWidth(1, 80)
        self._syncing_tree_checks = False
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        v.addWidget(self.tree, 1)

        actions = QHBoxLayout()
        self.btn_select_all = QPushButton(self.t("select_all"))
        self.btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        self.btn_clear = QPushButton(self.t("clear"))
        self.btn_clear.clicked.connect(lambda: self._set_all_checked(False))
        self.btn_series_play = QPushButton(self.t("play_selected"))
        self.btn_series_play.clicked.connect(self._play_series)
        self.btn_series_download = QPushButton(self.t("download_selected"))
        set_primary(self.btn_series_download)
        self.btn_series_download.clicked.connect(self._download_series)
        for btn in (self.btn_select_all, self.btn_clear, self.btn_series_play, self.btn_series_download):
            set_secondary(btn)
            actions.addWidget(btn)
        actions.addStretch()
        v.addLayout(actions)
        v.addWidget(self._download_controls(single=False))
        self.series_controls.hide()
        self.btn_series_download.hide()
        self.btn_series_play.hide()
        return page

    def _download_controls(self, single):
        card = self._card()
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(12)

        qlabel = QLabel(self.t("quality") if single else self.t("batch_quality"))
        qlabel.setFont(QFont("", 12, QFont.Weight.Bold))
        qlabel.setStyleSheet("background: transparent; border: none; padding: 0;")
        v.addWidget(qlabel)
        if not single:
            hint = QLabel(self.t("batch_quality_hint"))
            hint.setStyleSheet(
                f"background: transparent; color: {P['muted']}; border: none; padding: 0;"
            )
            v.addWidget(hint)
        self.quality_episode = getattr(self, "quality_episode", None) or QualityPicker()
        self.quality_series = getattr(self, "quality_series", None) or QualityPicker()
        default_quality = self.config.get("quality", "best")
        if single:
            self.quality_episode.set_value(default_quality)
        else:
            self.quality_series.set_value(default_quality)
        v.addWidget(self.quality_episode if single else self.quality_series)

        out_row = QHBoxLayout()
        edit = QLineEdit()
        edit.setText(self.config.get("output_dir") or str(DEFAULT_OUTPUT_DIR))
        browse = QPushButton(self.t("choose_folder"))
        browse.clicked.connect(lambda: self._pick_output(edit))
        set_secondary(browse)
        out_row.addWidget(edit, 1)
        out_row.addWidget(browse)
        v.addLayout(out_row)
        if single:
            self.output_episode = edit
            self.btn_episode_play = QPushButton(self.t("play"))
            set_secondary(self.btn_episode_play)
            self.btn_episode_play.clicked.connect(self._play_episode)
            v.addWidget(self.btn_episode_play)
            self.btn_episode_download = QPushButton(self.t("download_mp4"))
            set_primary(self.btn_episode_download)
            self.btn_episode_download.clicked.connect(self._download_episode)
            v.addWidget(self.btn_episode_download)
            self.episode_controls = card
        else:
            self.output_series = edit
            self.series_controls = card
        return card

    def _downloads_page(self):
        page, v = self._page()
        v.addWidget(title(self.t("downloads_title"), self.t("downloads_subtitle")))

        controls = self._card()
        controls_v = QVBoxLayout(controls)
        controls_v.setContentsMargins(18, 14, 18, 14)
        controls_v.setSpacing(10)
        header = QHBoxLayout()
        queue_title = QLabel(self.t("queue"))
        queue_title.setFont(QFont("", 13, QFont.Weight.Bold))
        queue_title.setStyleSheet("background: transparent; border: none;")
        header.addWidget(queue_title)
        header.addStretch()
        self.btn_pause_downloads = QPushButton(self.t("pause"))
        self.btn_cancel_downloads = QPushButton(self.t("cancel_all"))
        self.btn_open_downloads_folder = QPushButton(self.t("open_downloads_folder"))
        for btn in (self.btn_pause_downloads, self.btn_cancel_downloads, self.btn_open_downloads_folder):
            set_secondary(btn)
            header.addWidget(btn)
        self.btn_pause_downloads.clicked.connect(self._toggle_pause_downloads)
        self.btn_cancel_downloads.clicked.connect(self._cancel_downloads)
        self.btn_open_downloads_folder.clicked.connect(lambda: self._open_path(self.output_episode.text() if hasattr(self, "output_episode") else str(DEFAULT_OUTPUT_DIR)))
        controls_v.addLayout(header)
        self.download_status_label = QLabel(self.t("no_downloads"))
        self.download_status_label.setStyleSheet(f"background: transparent; color: {P['muted']}; border: none;")
        controls_v.addWidget(self.download_status_label)
        self.download_controls_card = controls
        self.download_controls_card.hide()
        v.addWidget(controls)

        self.downloads_empty = QLabel(self.t("no_downloads"))
        self.downloads_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.downloads_empty.setStyleSheet(
            f"color: {P['muted']}; background: transparent; border: none; padding: 0; font-size: 14px;"
        )
        v.addWidget(self.downloads_empty, 1)

        self.download_busy = BusyBar()
        v.addWidget(self.download_busy)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.downloads_layout = QVBoxLayout(content)
        self.downloads_layout.setContentsMargins(0, 0, 0, 0)
        self.downloads_layout.setSpacing(10)
        self.downloads_layout.addStretch()
        scroll.setWidget(content)
        self.downloads_scroll = scroll
        self.downloads_scroll.hide()
        v.addWidget(scroll, 1)
        return page

    def _player_page(self):
        page, v = self._page()
        v.addWidget(title(self.t("player_title"), self.t("player_subtitle")))

        card = self._card()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 18, 18, 18)
        cv.setSpacing(10)

        self.player_title_label = QLabel(self.t("player_empty"))
        self.player_title_label.setFont(QFont("", 13, QFont.Weight.Bold))
        self.player_title_label.setStyleSheet("background: transparent; border: none;")
        cv.addWidget(self.player_title_label)

        self.player_status = QLabel(self.t("player_empty"))
        self.player_status.setStyleSheet(f"background: transparent; color: {P['muted']}; border: none;")
        cv.addWidget(self.player_status)

        CTRL_STYLE = """
            QFrame#PlayerControls {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(10,10,10,220), stop:1 rgba(5,5,5,240));
                border: none;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                border-radius: 8px;
                min-height: 36px;
                min-width: 36px;
                padding: 0 6px;
                font-size: 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255,255,255,18);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,30);
            }
            QPushButton:disabled {
                color: rgba(255,255,255,80);
            }
            QLabel {
                color: rgba(255,255,255,200);
                background: transparent;
                border: none;
                font-size: 12px;
                font-family: "SF Mono", Menlo, Consolas, monospace;
            }
            QSlider::groove:horizontal {
                background: rgba(255,255,255,55);
                height: 5px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: white;
                height: 5px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
        """

        if HAS_QT_MULTIMEDIA:
            # ── Clickable video widget that pauses/resumes on click ──
            class ClickableVideo(QVideoWidget):
                clicked = Signal()
                def mousePressEvent(self, event):
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.clicked.emit()
                    super().mousePressEvent(event)

            # ── Seekable progress slider (click anywhere to seek) ──
            class SeekSlider(QSlider):
                seek_requested = Signal(int)
                def mousePressEvent(self, event):
                    if event.button() == Qt.MouseButton.LeftButton:
                        ratio = event.position().x() / max(self.width(), 1)
                        value = int(ratio * (self.maximum() - self.minimum()) + self.minimum())
                        self.setValue(value)
                        self.seek_requested.emit(value)
                    super().mousePressEvent(event)

            video_shell = QFrame()
            video_shell.setMinimumHeight(400)
            video_shell.setStyleSheet("background: #0a0a0a; border-radius: 14px;")
            self.player_video_shell = video_shell
            shell = QVBoxLayout(video_shell)
            shell.setContentsMargins(10, 10, 10, 10)
            shell.setSpacing(8)

            video_stage = QFrame()
            video_stage.setMinimumHeight(320)
            video_stage.setStyleSheet("background: #0a0a0a; border-radius: 10px;")
            self.player_video_stage = video_stage
            stage = QGridLayout(video_stage)
            stage.setContentsMargins(0, 0, 0, 0)
            stage.setSpacing(0)

            self.video_widget = ClickableVideo()
            self.video_widget.setMinimumHeight(320)
            self.video_widget.setStyleSheet(
                "background: #0a0a0a; border-radius: 10px;"
            )
            self.video_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            stage.addWidget(self.video_widget, 0, 0)
            shell.addWidget(video_stage, 1)

            # ── Controls bar ──────────────────────────────────────────
            controls = QFrame()
            controls.setObjectName("PlayerControls")
            controls.setStyleSheet(CTRL_STYLE)
            ctrl_v = QVBoxLayout(controls)
            ctrl_v.setContentsMargins(16, 8, 16, 12)
            ctrl_v.setSpacing(6)

            # Progress row
            progress_row = QHBoxLayout()
            progress_row.setContentsMargins(0, 0, 0, 0)
            progress_row.setSpacing(10)
            self.player_slider = SeekSlider(Qt.Orientation.Horizontal)
            self.player_slider.setRange(0, 0)
            self.player_slider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.player_time = QLabel("00:00 / 00:00")
            self.player_time.setMinimumWidth(100)
            self.player_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            progress_row.addWidget(self.player_slider, 1)
            progress_row.addWidget(self.player_time)
            ctrl_v.addLayout(progress_row)

            # Buttons row
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 0, 0, 0)
            btn_row.setSpacing(2)

            self.btn_player_prev = QPushButton("⏮")
            self.btn_player_play = QPushButton("▶")
            self.btn_player_next = QPushButton("⏭")
            self.btn_player_prev.setToolTip("Anterior")
            self.btn_player_play.setToolTip("Play / Pausa")
            self.btn_player_next.setToolTip("Próximo")
            self.btn_player_play.setFixedWidth(48)

            # Volume controls
            vol_icon = QLabel("🔊")
            vol_icon.setStyleSheet("color: rgba(255,255,255,180); background: transparent; border: none; font-size: 14px;")
            self.player_volume_slider = SeekSlider(Qt.Orientation.Horizontal)
            self.player_volume_slider.setRange(0, 100)
            self.player_volume_slider.setValue(85)
            self.player_volume_slider.setFixedWidth(80)
            self.player_volume_slider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.player_volume_slider.setToolTip("Volume")

            for btn in (self.btn_player_prev, self.btn_player_play, self.btn_player_next):
                btn.setFixedHeight(38)
                btn_row.addWidget(btn)

            btn_row.addStretch()
            btn_row.addWidget(vol_icon)
            btn_row.addWidget(self.player_volume_slider)

            ctrl_v.addLayout(btn_row)
            shell.addWidget(controls)
            cv.addWidget(video_shell, 1)
            self.player_video_overlay = VideoLoadingOverlay()
            self.player_video_overlay.attach(video_stage)

            # ── Media player setup ────────────────────────────────────
            self.media_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.audio_output.setVolume(0.85)
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.setVideoOutput(self.video_widget)
            self.media_player.mediaStatusChanged.connect(self._on_player_media_status)
            self.media_player.positionChanged.connect(self._on_player_position)
            self.media_player.durationChanged.connect(self._on_player_duration)
            self.media_player.playbackStateChanged.connect(self._on_player_state)

            # Click-to-seek (both drag and click)
            self.player_slider.sliderMoved.connect(self._seek_player)
            self.player_slider.seek_requested.connect(self._seek_player)

            # Click video to pause/play
            self.video_widget.clicked.connect(self._player_toggle_play)

            # Volume slider
            self.player_volume_slider.sliderMoved.connect(self._set_volume)
            self.player_volume_slider.seek_requested.connect(self._set_volume)

        else:
            fallback = QLabel(
                "QtMultimedia não está disponível. O temporário será aberto no player do sistema."
                if self.lang == "pt"
                else "QtMultimedia is unavailable. The temporary file will open in the system player."
            )
            fallback.setWordWrap(True)
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setMinimumHeight(360)
            fallback.setStyleSheet(f"background: {P['surface2']}; color: {P['muted']}; border-radius: 14px;")
            cv.addWidget(fallback, 1)

            row = QHBoxLayout()
            self.btn_player_prev = QPushButton("⏮")
            self.btn_player_play = QPushButton(self.t("play"))
            self.btn_player_next = QPushButton("⏭")
            for btn in (self.btn_player_prev, self.btn_player_play, self.btn_player_next):
                set_secondary(btn)
                row.addWidget(btn)
            row.addStretch()
            cv.addLayout(row)

        row = QHBoxLayout()
        self.btn_player_open = QPushButton(self.t("player_open_external"))
        set_secondary(self.btn_player_open)
        row.addWidget(self.btn_player_open)
        row.addStretch()
        self.btn_player_prev.clicked.connect(self._play_previous_from_playlist)
        self.btn_player_play.clicked.connect(self._player_toggle_play)
        self.btn_player_next.clicked.connect(self._play_next_from_queue)
        self.btn_player_open.clicked.connect(lambda: self._open_path(self.player_current_path))
        self.btn_player_prev.setEnabled(False)
        self.btn_player_next.setEnabled(False)
        self.btn_player_play.setEnabled(False)
        self.btn_player_open.setEnabled(False)
        cv.addLayout(row)

        v.addWidget(card, 1)
        return page

    def _preferences_page(self):
        page, v = self._page()
        v.addWidget(title(self.t("preferences_title"), self.t("preferences_subtitle")))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")

        pv = QVBoxLayout(inner)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(16)

        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

        general = self._card()

        gv = QVBoxLayout(general)
        gv.setContentsMargins(24, 24, 24, 24)
        gv.setSpacing(14)

        lbl = QLabel(self.t("defaults"))
        lbl.setFont(QFont("", 13, QFont.Weight.Bold))
        lbl.setStyleSheet("background: transparent; border: none;")
        gv.addWidget(lbl)

        folder_lbl = QLabel(self.t("default_folder"))
        folder_lbl.setStyleSheet("background: transparent; border: none;")
        gv.addWidget(folder_lbl)

        out_row = QHBoxLayout()
        out_row.setContentsMargins(0, 0, 0, 0)
        out_row.setSpacing(14)

        self.pref_output_dir = QLineEdit()
        self.pref_output_dir.setText(
            self.config.get("output_dir") or str(DEFAULT_OUTPUT_DIR)
        )
        self.pref_output_dir.setMinimumHeight(44)

        btn_output = QPushButton(self.t("choose_folder"))
        btn_output.setMinimumHeight(44)
        btn_output.setMinimumWidth(150)
        btn_output.clicked.connect(lambda: self._pick_output(self.pref_output_dir))
        set_secondary(btn_output)

        out_row.addWidget(self.pref_output_dir, 1)
        out_row.addWidget(btn_output)
        gv.addLayout(out_row)

        gv.addSpacing(6)

        q_hint = QLabel(self.t("default_quality"))
        q_hint.setStyleSheet("background: transparent; border: none;")
        gv.addWidget(q_hint)

        self.pref_quality = QualityPicker()
        self.pref_quality.set_value(self.config.get("quality", "best"))
        gv.addWidget(self.pref_quality)

        fallback = QLabel(self.t("quality_fallback"))
        fallback.setWordWrap(True)
        fallback.setStyleSheet(
            f"background: transparent; color: {P['muted']}; border: none;"
        )
        gv.addWidget(fallback)

        gv.addSpacing(6)

        workers_lbl = QLabel(self.t("workers"))
        workers_lbl.setStyleSheet("background: transparent; border: none;")
        gv.addWidget(workers_lbl)

        self.pref_download_workers = QSpinBox()
        self.pref_download_workers.setRange(1, 6)
        self.pref_download_workers.setValue(int(self.config.get("download_workers", 2) or 2))
        self.pref_download_workers.setMinimumHeight(44)
        self.pref_download_workers.setFixedWidth(96)
        self.pref_download_workers.setToolTip(self.t("workers"))
        gv.addWidget(self.pref_download_workers)

        gv.addSpacing(6)

        lang_lbl = QLabel(self.t("language"))
        lang_lbl.setStyleSheet("background: transparent; border: none;")
        gv.addWidget(lang_lbl)

        self.pref_language = LanguagePicker()
        self.pref_language.set_value(self.lang)
        gv.addWidget(self.pref_language)

        gv.addSpacing(16)

        btn_save = QPushButton(self.t("save_preferences"))
        btn_save.setMinimumHeight(52)
        set_primary(btn_save)
        btn_save.clicked.connect(self._save_preferences)
        gv.addWidget(btn_save)

        pv.addWidget(general)
        pv.addStretch()

        return page

    def _status_page(self):
        page, v = self._page()
        v.addWidget(title(self.t("status_title"), self.t("status_subtitle")))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        sv = QVBoxLayout(inner)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(16)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

        tools = self._card()
        tv = QVBoxLayout(tools)
        tv.setContentsMargins(18, 18, 18, 18)
        tv.setSpacing(12)
        th = QHBoxLayout()
        tlabel = QLabel(self.t("tools"))
        tlabel.setFont(QFont("", 13, QFont.Weight.Bold))
        tlabel.setStyleSheet("background: transparent; border: none;")
        th.addWidget(tlabel)
        th.addStretch()
        btn_check = QPushButton(self.t("verify"))
        btn_check.clicked.connect(self._check_tools)
        set_secondary(btn_check)
        th.addWidget(btn_check)
        tv.addLayout(th)
        self.tools_status = QLabel(self.t("not_checked"))
        self.tools_status.setWordWrap(True)
        self.tools_status.setStyleSheet(f"background: transparent; color: {P['muted']}; border: none;")
        tv.addWidget(self.tools_status)
        sv.addWidget(tools)

        wvd = self._card()
        wv = QVBoxLayout(wvd)
        wv.setContentsMargins(18, 18, 18, 18)
        wv.setSpacing(12)
        wh = QHBoxLayout()
        wlabel = QLabel(self.t("widevine"))
        wlabel.setFont(QFont("", 13, QFont.Weight.Bold))
        wlabel.setStyleSheet("background: transparent; border: none;")
        wh.addWidget(wlabel)
        wh.addStretch()
        btn_refresh = QPushButton(self.t("refresh"))
        btn_refresh.clicked.connect(self._refresh_wvd_status)
        set_secondary(btn_refresh)
        wh.addWidget(btn_refresh)
        wv.addLayout(wh)

        self.wvd_status = QLabel("")
        self.wvd_status.setWordWrap(True)
        self.wvd_status.setStyleSheet(f"background: transparent; color: {P['muted']}; border: none;")
        wv.addWidget(self.wvd_status)

        self.btn_toggle_wvd = QPushButton(self.t("show_wvd"))
        self.btn_toggle_wvd.clicked.connect(self._toggle_wvd_form)
        set_secondary(self.btn_toggle_wvd)
        wv.addWidget(self.btn_toggle_wvd)

        self.wvd_form = QWidget()
        self.wvd_form.setStyleSheet("background: transparent;")
        form = QVBoxLayout(self.wvd_form)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        self.wvd_form.hide()

        fixed_output = QLabel(f"{self.t('wvd_output_fixed')} {SECRETS_DIR}")
        fixed_output.setWordWrap(True)
        fixed_output.setStyleSheet(f"background: transparent; color: {P['muted']}; border: none;")
        form.addWidget(fixed_output)

        self.pref_private_key = QLineEdit()
        self.pref_private_key.setPlaceholderText("private_key.pem")
        self.pref_client_id = QLineEdit()
        self.pref_client_id.setPlaceholderText("client_id.bin")
        for edit, label_text in (
            (self.pref_private_key, self.t("private_key")),
            (self.pref_client_id, self.t("client_id")),
        ):
            row = QHBoxLayout()
            row.addWidget(edit, 1)
            btn = QPushButton(self.t("choose_file"))
            btn.clicked.connect(lambda checked=False, e=edit: self._pick_file(e))
            set_secondary(btn)
            row.addWidget(btn)
            form.addWidget(QLabel(label_text))
            form.addLayout(row)

        self.btn_generate_wvd = QPushButton(self.t("generate_wvd"))
        set_primary(self.btn_generate_wvd)
        self.btn_generate_wvd.clicked.connect(self._generate_wvd)
        form.addWidget(self.btn_generate_wvd)
        wv.addWidget(self.wvd_form)
        sv.addWidget(wvd)

        # ── About / links ─────────────────────────────────────────────
        about = self._card()
        av = QVBoxLayout(about)
        av.setContentsMargins(20, 18, 20, 18)
        av.setSpacing(12)
        top = QHBoxLayout()
        made = QLabel(self.t("developed_by"))
        made.setFont(QFont("", 13, QFont.Weight.Bold))
        made.setStyleSheet("background: transparent; border: none;")
        #version_lbl = QLabel(f"v{APP_VERSION}")
        #version_lbl.setStyleSheet(f"background: transparent; color: {P['muted']}; border: none;")
        top.addWidget(made)
        top.addStretch()
        #top.addWidget(version_lbl)
        av.addLayout(top)

        links = QHBoxLayout()
        for label, url in (
            ("GitHub", "https://github.com/MiguelMaster12/sic_opto_downloader"),
            (self.t("support"), "https://buymeacoffee.com/miguelmaster12"),
        ):
            link = QPushButton(label)
            link.setFixedHeight(42)
            link.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            link.clicked.connect(lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            link.setStyleSheet(f"""
                QPushButton {{
                    background: {P["surface2"]};
                    color: {P["text"]};
                    border: 1px solid {P["line"]};
                    border-radius: 10px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {P["accent"]};
                    color: white;
                    border-color: {P["accent"]};
                }}
            """)
            links.addWidget(link)
        av.addLayout(links)
        sv.addWidget(about)

        sv.addStretch()
        self._refresh_wvd_status()
        return page

    def _log_page(self):
        page, v = self._page()
        header = QHBoxLayout()
        header.addWidget(title(self.t("log_title"), self.t("log_subtitle")))
        header.addStretch()
        clear = QPushButton(self.t("clear"))
        clear.clicked.connect(lambda: self.log_box.clear())
        set_secondary(clear)
        header.addWidget(clear)
        v.addLayout(header)
        self.log_box = LogBox()
        v.addWidget(self.log_box, 1)
        return page

    def _card(self):
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(f"""
            QFrame#Card {{
                background: {P["surface"]};
                border: 1px solid {P["line"]};
                border-radius: 16px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        return card

    def _pick_output(self, edit):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta", edit.text())
        if folder:
            edit.setText(folder)

    def _pick_file(self, edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar ficheiro", str(SCRIPT_DIR))
        if file_path:
            edit.setText(file_path)

    def _log(self, text):
        if text:
            self.log_box.append_line(text)

    def _busy(self, text):
        self.status.setText(text)

    def _idle(self):
        self.status.setText(self.t("ready"))
        for name in (
            "busy_episode", "busy_series", "download_busy",
            "overlay_episode", "overlay_series", "overlay_downloads", "overlay_player", "overlay_preferences", "overlay_status",
            "player_video_overlay",
        ):
            widget = getattr(self, name, None)
            if widget:
                widget.stop()

    def _save_preferences(self):
        old_lang = self.lang
        data = {
            "output_dir": self.pref_output_dir.text().strip() or str(DEFAULT_OUTPUT_DIR),
            "quality": self.pref_quality.value(),
            "download_workers": self.pref_download_workers.value(),
            "language": self.pref_language.value(),
        }
        save_config(data)
        self.config.update(data)
        self.output_episode.setText(data["output_dir"])
        self.output_series.setText(data["output_dir"])
        self.quality_episode.set_value(data["quality"])
        self.quality_series.set_value(data["quality"])
        self.lang = data["language"]
        QMessageBox.information(
            self,
            self.t("preferences"),
            "Preferências guardadas." if self.lang == "pt" else "Preferences saved.",
        )
        if self.lang != old_lang:
            self._build()

    def _toggle_wvd_form(self):
        visible = not self.wvd_form.isVisible()
        self.wvd_form.setVisible(visible)
        self.btn_toggle_wvd.setText(self.t("hide_wvd") if visible else self.t("show_wvd"))

    def _check_tools(self):
        lines = []
        for tool in ("yt-dlp", "mp4decrypt", "ffmpeg", "ffprobe"):
            found = media.resolve_tool(tool)
            lines.append(f"{'✓' if found else '×'} {tool}: {found or 'não encontrado'}")
        for pkg, imp in (("requests", "requests"), ("pywidevine", "pywidevine"), ("PySide6", "PySide6")):
            try:
                __import__(imp)
                lines.append(f"✓ {pkg}: instalado")
            except ImportError:
                lines.append(f"× {pkg}: não instalado")
        wvds = media.find_wvd_files()
        lines.append(f"{'✓' if wvds else '×'} .wvd: {wvds[0] if wvds else 'não encontrado'}")
        self.tools_status.setText("\n".join(lines))
        self._log("Verificação de ferramentas concluída.")

    def _refresh_wvd_status(self):
        wvds = media.find_wvd_files()
        if wvds:
            self.wvd_status.setText(f"✓ Encontrado: {wvds[0]}")
            self.wvd_status.setStyleSheet(f"background: transparent; color: {P['ok']}; border: none;")
        else:
            self.wvd_status.setText("× Nenhum .wvd encontrado em secrets/, ~/.wvd/ ou pastas conhecidas.")
            self.wvd_status.setStyleSheet(f"background: transparent; color: {P['warn']}; border: none;")

    def _generate_wvd(self):
        private_key = self.pref_private_key.text().strip()
        client_id = self.pref_client_id.text().strip()
        output_dir = str(SECRETS_DIR)
        if not private_key or not Path(private_key).exists():
            QMessageBox.warning(self, "Gerar .wvd", "Seleciona um private_key.pem válido.")
            return
        if not client_id or not Path(client_id).exists():
            QMessageBox.warning(self, "Gerar .wvd", "Seleciona um client_id.bin válido.")
            return
        self._busy("A gerar .wvd")
        self.overlay_status.start("A gerar ficheiro .wvd..." if self.lang == "pt" else "Generating .wvd...")
        self.btn_generate_wvd.setEnabled(False)
        thread = GenerateWvdThread(private_key, client_id, output_dir)
        thread.log_signal.connect(self._log)
        thread.done.connect(self._wvd_generated)
        self._run_thread(thread)

    def _wvd_generated(self, path):
        self._idle()
        self.btn_generate_wvd.setEnabled(True)
        self._refresh_wvd_status()
        QMessageBox.information(self, "Gerar .wvd", f"Concluído.\n{path or 'Verifica a pasta de saída.'}")

    def _run_thread(self, thread):
        self._threads.append(thread)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        thread.log_signal.connect(self._log)
        thread.error.connect(self._error)
        thread.start()

    def _error(self, text):
        self._idle()
        self._log(f"Erro: {text}")
        for row in self.download_rows:
            if row.progress.value() < 100:
                row.update_state("Erro")
        if hasattr(self, "btn_generate_wvd"):
            self.btn_generate_wvd.setEnabled(True)
        if self.current_download_thread:
            self.current_download_thread = None
            if hasattr(self, "download_status_label"):
                self.download_status_label.setText("Erro" if self.lang == "pt" else "Error")
            if hasattr(self, "download_controls_card"):
                self.download_controls_card.hide()
        QMessageBox.critical(self, "Erro", text)

    def _prepare_download_rows(self, episodes):
        for row in self.download_rows:
            row.setParent(None)
        self.download_rows = []
        self.download_groups = {}
        self.downloads_empty.hide()
        self.downloads_scroll.show()
        self.download_controls_card.show()
        self.download_status_label.setText(f"{len(episodes)} item(s) na fila" if self.lang == "pt" else f"{len(episodes)} item(s) queued")
        while self.downloads_layout.count() > 0:
            item = self.downloads_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        for idx, ep in enumerate(episodes):
            ep["_row_index"] = idx
            label = ep.get("label") or ep.get("output_name") or ep.get("url") or "Episódio"
            group = ep.get("group") or ("Episódio" if self.lang == "pt" else "Episode")
            if group not in self.download_groups:
                download_group = DownloadGroup(group)
                self.download_groups[group] = download_group
                self.downloads_layout.addWidget(download_group)
            row = DownloadRow(label, idx, self.lang)
            row.open_requested.connect(self._open_download_row)
            row.cancel_requested.connect(self._cancel_download_row)
            self.download_rows.append(row)
            self.download_groups[group].add_row(row)
        self.downloads_layout.addStretch()

    def _set_download_actions_visible(self, visible):
        if hasattr(self, "download_controls_card"):
            self.download_controls_card.setVisible(bool(visible))

    def _clear_download_rows(self):
        for row in self.download_rows:
            row.setParent(None)
        self.download_rows = []
        self.download_groups = {}
        while self.downloads_layout.count() > 0:
            item = self.downloads_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.downloads_layout.addStretch()
        self.downloads_scroll.hide()
        self.downloads_empty.show()
        self._set_download_actions_visible(False)

    def _hide_download_row(self, index):
        if not (0 <= index < len(self.download_rows)):
            return
        row = self.download_rows[index]
        body = row.parentWidget()
        row.hide()
        if body and body.layout():
            has_visible_rows = False
            for i in range(body.layout().count()):
                widget = body.layout().itemAt(i).widget()
                if isinstance(widget, DownloadRow) and widget.isVisible():
                    has_visible_rows = True
                    break
            group = body.parentWidget()
            if group:
                group.setVisible(has_visible_rows)

    def _on_download_progress(self, index, status, percent, speed, eta):
        if 0 <= index < len(self.download_rows):
            self.download_rows[index].update_state(status, percent, speed, eta)

    def _download_row_done(self, index, path):
        if 0 <= index < len(self.download_rows):
            self.download_rows[index].mark_done(path)

    def _download_row_cancelled(self, index):
        if 0 <= index < len(self.download_rows):
            self.download_rows[index].mark_cancelled()
            self._hide_download_row(index)

    def _download_row_failed(self, index, message):
        if 0 <= index < len(self.download_rows):
            self.download_rows[index].mark_failed(message)
        if not hasattr(self, "download_failed_rows"):
            self.download_failed_rows = set()
        self.download_failed_rows.add(index)
        self._log(f"Falhou episódio {index + 1}: {message}")

    def _download_row_skipped(self, index, path):
        if 0 <= index < len(self.download_rows):
            self.download_rows[index].mark_skipped(path)
        if not hasattr(self, "download_skipped_rows"):
            self.download_skipped_rows = set()
        self.download_skipped_rows.add(index)
        self._log(f"Ignorado episódio {index + 1}: já existe em {path}")

    def _toggle_pause_downloads(self):
        thread = self.current_download_thread
        if not thread or not thread.isRunning():
            return
        if thread.paused:
            thread.resume()
            self.btn_pause_downloads.setText(self.t("pause"))
            self.download_status_label.setText("Download em curso" if self.lang == "pt" else "Download running")
        else:
            thread.pause()
            self.btn_pause_downloads.setText(self.t("resume"))
            self.download_status_label.setText(self.t("paused"))

    def _cancel_downloads(self):
        thread = self.current_download_thread
        if thread and thread.isRunning():
            self.downloads_cancelled_by_user = True
            thread.cancel()
            self.download_status_label.setText(self.t("cancelled"))
            self._clear_download_rows()

    def _cancel_download_row(self, index):
        if not (0 <= index < len(self.download_rows)):
            return
        thread = self.current_download_thread
        if thread and thread.isRunning():
            thread.cancel_row(index)
            self.download_status_label.setText("Download cancelado da fila" if self.lang == "pt" else "Download removed from queue")
        self._hide_download_row(index)

    def _open_download_row(self, index):
        if 0 <= index < len(self.download_rows):
            self._open_path(self.download_rows[index].path)

    def _open_path(self, path):
        if not path:
            return
        p = Path(path)
        target = p if p.exists() else p.parent
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            elif os.name == "nt":
                os.startfile(str(target))
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            QMessageBox.warning(self, self.t("downloads"), str(exc))


    def _analyze_episode(self):
        value = self.episode_input.text().strip()
        if not value:
            QMessageBox.warning(self, "Episódio", "Insere URL ou UUID do episódio.")
            return
        self.btn_episode_download.hide()
        self.episode_controls.hide()
        self._busy("A analisar episódio")
        self.overlay_episode.start("A analisar episódio...")
        thread = AnalyzeEpisodeThread(value)
        thread.done.connect(self._episode_ready)
        self._run_thread(thread)

    def _episode_ready(self, data):
        self._idle()
        self._episode_data = data
        heights = sorted(
            {int(q["height"]) for q in data.get("qualities", []) if q.get("height")},
            reverse=True,
        )
        qualities = ", ".join(f"{height}p" for height in heights)
        self.episode_summary.setText(
            f"{data.get('title')}  ·  T{data.get('season')}E{data.get('episode')}\n"
            f"MPD, license e PSSH resolvidos. Qualidades: {qualities or 'n/d'}"
        )
        self.episode_controls.show()
        self.btn_episode_download.show()
        self.btn_episode_play.show()

    def _analyze_series(self):
        value = self.series_input.text().strip()
        if not value:
            QMessageBox.warning(self, "Série", "Insere URL da série.")
            return
        self.tree.clear()
        self.btn_series_download.hide()
        self.series_controls.hide()
        self._busy("A carregar série")
        self.overlay_series.start("A carregar série...")
        thread = AnalyzeSeriesThread(value)
        thread.done.connect(self._series_ready)
        self._run_thread(thread)

    def _series_ready(self, data):
        self._idle()
        self._series_data = data
        self.tree.clear()
        for season_key, episodes in data.get("episodes_by_season", {}).items():
            parent = QTreeWidgetItem([f"{season_key} ({len(episodes)} episódios)", "", ""])
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.CheckState.Checked)
            self.tree.addTopLevelItem(parent)
            for ep in episodes:
                dur = ""
                if ep.get("duration"):
                    dur = f"{ep['duration']//60}m{ep['duration']%60:02d}s"
                child = QTreeWidgetItem([
                    f"E{int(ep.get('episode') or 0):02d}  {ep.get('title', '')}",
                    dur,
                    ep.get("url", ""),
                ])
                child.setData(0, Qt.ItemDataRole.UserRole, ep)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                parent.addChild(child)
        self.tree.expandAll()
        self.series_controls.show()
        self.btn_series_download.show()
        self.btn_series_play.show()
        self._log(f"Série pronta: {data.get('episode_count')} episódios.")

    def _set_all_checked(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._syncing_tree_checks = True
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            parent.setCheckState(0, state)
            for j in range(parent.childCount()):
                parent.child(j).setCheckState(0, state)
        self._syncing_tree_checks = False

    def _on_tree_item_changed(self, item, column):
        if column != 0 or getattr(self, "_syncing_tree_checks", False):
            return
        self._syncing_tree_checks = True
        try:
            state = item.checkState(0)
            if item.childCount():
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, state)
            else:
                parent = item.parent()
                if parent:
                    checked = sum(
                        1
                        for i in range(parent.childCount())
                        if parent.child(i).checkState(0) == Qt.CheckState.Checked
                    )
                    if checked == parent.childCount():
                        parent.setCheckState(0, Qt.CheckState.Checked)
                    elif checked == 0:
                        parent.setCheckState(0, Qt.CheckState.Unchecked)
                    else:
                        parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        finally:
            self._syncing_tree_checks = False

    def _selected_episodes(self):
        selected = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    ep = child.data(0, Qt.ItemDataRole.UserRole)
                    if ep:
                        season = int(ep.get("season") or 0)
                        season_name = (
                            ep.get("season_name")
                            or parent.text(0).split(" (", 1)[0]
                            or (f"T{season:02d}" if season else "")
                        )
                        series_name = (
                            self._series_data.get("title")
                            or self._series_data.get("series_title")
                            or self.series_input.text().strip()
                            or self.t("series")
                        )
                        season_folder = f"{safe_folder_name(series_name)}_S{season:02d}" if season else safe_folder_name(series_name)
                        selected.append({
                            "url": ep["url"],
                            "label": child.text(0),
                            "output_name": f"{ep.get('title', 'SIC_OPTO')}_T{int(ep.get('season') or 0):02d}E{int(ep.get('episode') or 0):02d}",
                            "group": f"{series_name} > {season_name}" if season_name else series_name,
                            "output_dir": str(Path(self.output_series.text() or DEFAULT_OUTPUT_DIR) / season_folder),
                        })
        return selected

    def _download_episode(self):
        if not self._episode_data:
            return
        ep = {
            "url": self._episode_data["episode_uuid"],
            "resolved": self._episode_data,
            "label": f"{self._episode_data.get('title')} T{self._episode_data.get('season')}E{self._episode_data.get('episode')}",
            "group": self.t("episode"),
        }
        self._start_download([ep], self.output_episode.text(), self.quality_episode.value())

    def _download_series(self):
        episodes = self._selected_episodes()
        if not episodes:
            QMessageBox.warning(self, "Série", "Seleciona pelo menos um episódio.")
            return
        self._start_download(episodes, self.output_series.text(), self.quality_series.value())

    def _play_episode(self):
        if not self._episode_data:
            return
        ep = {
            "url": self._episode_data["episode_uuid"],
            "resolved": self._episode_data,
            "label": f"{self._episode_data.get('title')} T{self._episode_data.get('season')}E{self._episode_data.get('episode')}",
            "output_name": media.default_output_name(self._episode_data),
        }
        self._start_player([ep], self.quality_episode.value())

    def _play_series(self):
        episodes = self._selected_episodes()
        if not episodes:
            QMessageBox.warning(self, "Série", "Seleciona pelo menos um episódio.")
            return
        self._start_player(episodes, self.quality_series.value())

    def _start_player(self, episodes, quality):
        self._reset_player_cache()
        self.player_playlist = list(episodes)
        self.player_index = 0 if self.player_playlist else -1
        self.player_quality = quality
        self._nav(3)
        self._load_player_index(self.player_index)

    def _reset_player_cache(self):
        if self.current_player_thread and self.current_player_thread.isRunning():
            self.current_player_thread.cancel()
        for thread in list(self.player_prefetch_threads.values()):
            if thread.isRunning():
                thread.cancel()
        self.player_prefetch_threads = {}
        self.player_cache = {}
        self.player_queue = []
        for temp_dir in list(self.player_temp_dirs):
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.player_temp_dirs.clear()
        self.player_current_path = ""

    def _playlist_has_index(self, index):
        return 0 <= index < len(self.player_playlist)

    def _update_player_nav_buttons(self):
        has_current = bool(self.player_current_path)
        self.btn_player_prev.setEnabled(self._playlist_has_index(self.player_index - 1))
        self.btn_player_next.setEnabled(self._playlist_has_index(self.player_index + 1))
        self.btn_player_play.setEnabled(has_current)
        self.btn_player_open.setEnabled(has_current)

    def _load_player_index(self, index):
        if not self._playlist_has_index(index):
            self.player_status.setText(self.t("player_empty"))
            self._update_player_nav_buttons()
            return
        self.player_index = index
        cached = self.player_cache.get(index)
        if cached:
            self._player_use_cache(index, autoplay=True)
            return
        promoted = self.player_prefetch_threads.pop(index, None)
        if promoted and promoted.isRunning():
            self.current_player_thread = promoted
            self.player_status.setText(self.t("player_preparing"))
            self._set_player_loading(True, self.t("player_preparing"))
            self._update_player_nav_buttons()
            return
        for thread in list(self.player_prefetch_threads.values()):
            if thread.isRunning():
                thread.cancel()
        self.player_prefetch_threads = {}
        if self.current_player_thread and self.current_player_thread.isRunning():
            self.current_player_thread.cancel()
        ep = self.player_playlist[index]
        self.player_title_label.setText(ep.get("label") or ep.get("output_name") or self.t("episode"))
        self.player_status.setText(self.t("player_preparing"))
        self.player_current_path = ""
        self._update_player_nav_buttons()
        self._set_player_loading(True, self.t("player_preparing"))
        thread = self._new_player_thread(index)
        self.current_player_thread = thread
        thread.start()

    def _new_player_thread(self, index):
        thread = PlayerPrepareThread(
            self.player_playlist[index],
            getattr(self, "player_quality", "best"),
            index,
        )
        thread.log_signal.connect(self._log)
        thread.progress_signal.connect(self._player_progress)
        thread.ready.connect(self._player_ready)
        thread.error.connect(self._player_error)
        self._threads.append(thread)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        return thread

    def _play_next_from_queue(self):
        self._load_player_index(self.player_index + 1)

    def _play_previous_from_playlist(self):
        self._load_player_index(self.player_index - 1)

    def _player_progress(self, index, text):
        if index == self.player_index:
            self.player_status.setText(text)
            self._set_player_loading(True, text)

    def _player_ready(self, index, path, title_text, temp_dir):
        self.player_cache[index] = {
            "path": path,
            "title": title_text,
            "temp_dir": temp_dir,
        }
        self.player_temp_dirs.append(temp_dir)
        if index in self.player_prefetch_threads:
            self.player_prefetch_threads.pop(index, None)
        if index == self.player_index:
            self._player_use_cache(index, autoplay=True)
        self._prefetch_player_neighbors()

    def _player_use_cache(self, index, autoplay=False):
        cached = self.player_cache.get(index)
        if not cached:
            return
        self._idle()
        self._set_player_loading(False)
        self.current_player_thread = None
        self.player_current_path = cached["path"]
        self.player_title_label.setText(cached["title"])
        self.player_status.setText(self.t("player_ready"))
        self._update_player_nav_buttons()
        if autoplay:
            self._player_play_current()

    def _prefetch_player_neighbors(self):
        if self.current_player_thread and self.current_player_thread.isRunning():
            return
        if self.player_prefetch_threads:
            return
        for index in (self.player_index + 1, self.player_index - 1):
            if not self._playlist_has_index(index):
                continue
            if index in self.player_cache or index in self.player_prefetch_threads:
                continue
            thread = self._new_player_thread(index)
            self.player_prefetch_threads[index] = thread
            thread.finished.connect(lambda i=index: self.player_prefetch_threads.pop(i, None))
            thread.start()
            return

    def _player_toggle_play(self):
        if self.media_player:
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.pause()
            else:
                self._player_play_current()
        else:
            self._player_play_current()

    def _set_player_loading(self, active, text=""):
        overlay = getattr(self, "player_video_overlay", None)
        if not overlay:
            return
        if active:
            if hasattr(self, "video_widget"):
                self.video_widget.hide()
            overlay.start(text or self.t("player_preparing"))
        else:
            overlay.stop()
            if hasattr(self, "video_widget"):
                self.video_widget.show()

    def _set_volume(self, value: int):
        """Set volume from slider value 0–100."""
        if self.audio_output:
            self.audio_output.setVolume(value / 100.0)
        # Update icon based on level
        if hasattr(self, "player_volume_slider"):
            pass  # icon label is cosmetic only

    def _player_play_current(self):
        if not self.player_current_path:
            return
        if self.media_player:
            if self.player_loaded_path != self.player_current_path:
                self.media_player.setSource(QUrl.fromLocalFile(self.player_current_path))
                self.player_loaded_path = self.player_current_path
            self.media_player.play()
        else:
            self._open_path(self.player_current_path)

    def _player_error(self, index, text):
        self.player_prefetch_threads.pop(index, None)
        if index != self.player_index:
            self._log(f"Erro player cache: {text}")
            self._prefetch_player_neighbors()
            return
        self._idle()
        self._set_player_loading(False)
        self.current_player_thread = None
        self.player_status.setText(text)
        self._log(f"Erro player: {text}")
        QMessageBox.warning(self, self.t("player"), text)

    def _on_player_media_status(self, status):
        if not self.media_player:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self._playlist_has_index(self.player_index + 1):
            self._play_next_from_queue()

    def _format_player_time(self, ms):
        secs = max(0, int(ms // 1000))
        return f"{secs // 60:02d}:{secs % 60:02d}"

    def _on_player_position(self, position):
        if hasattr(self, "player_slider") and not self.player_seeking:
            self.player_slider.setValue(position)
        if hasattr(self, "player_time"):
            self.player_time.setText(
                f"{self._format_player_time(position)} / {self._format_player_time(self.player_duration)}"
            )

    def _on_player_duration(self, duration):
        self.player_duration = duration
        if hasattr(self, "player_slider"):
            self.player_slider.setRange(0, max(0, duration))
        if hasattr(self, "player_time"):
            self.player_time.setText(f"00:00 / {self._format_player_time(duration)}")

    def _on_player_state(self, state):
        if hasattr(self, "btn_player_play"):
            self.btn_player_play.setText("⏸" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")

    def _seek_player(self, position):
        if self.media_player:
            self.media_player.setPosition(position)

    def _start_download(self, episodes, output_dir, quality):
        self._busy("Download em curso")
        self.downloads_cancelled_by_user = False
        self.download_failed_rows = set()
        self.download_skipped_rows = set()
        self._prepare_download_rows(episodes)
        self._nav(2)
        worker_count = max(1, min(int(self.config.get("download_workers", 2) or 2), 6))
        thread = DownloadThread(episodes, output_dir or str(DEFAULT_OUTPUT_DIR), quality, worker_count)
        self.current_download_thread = thread
        self._set_download_actions_visible(True)
        self.download_status_label.setText(
            f"{len(episodes)} item(s) na fila · {worker_count} worker(s)"
            if self.lang == "pt"
            else f"{len(episodes)} item(s) queued · {worker_count} worker(s)"
        )
        thread.done.connect(self._download_done)
        thread.progress_signal.connect(self._on_download_progress)
        thread.row_done.connect(self._download_row_done)
        thread.row_cancelled.connect(self._download_row_cancelled)
        thread.row_failed.connect(self._download_row_failed)
        thread.row_skipped.connect(self._download_row_skipped)
        self._run_thread(thread)

    def _download_done(self, outputs):
        self._idle()
        self.current_download_thread = None
        self.btn_pause_downloads.setText(self.t("pause"))
        self._set_download_actions_visible(False)
        if self.downloads_cancelled_by_user:
            self.downloads_cancelled_by_user = False
            self.download_status_label.setText(self.t("cancelled"))
            self._log("Downloads cancelados.")
            return
        failed = len(getattr(self, "download_failed_rows", set()))
        skipped = len(getattr(self, "download_skipped_rows", set()))
        if failed or skipped:
            status = (
                f"{len(outputs)} gerado(s), {skipped} ignorado(s), {failed} falhado(s)."
                if self.lang == "pt"
                else f"{len(outputs)} generated, {skipped} skipped, {failed} failed."
            )
            self.download_status_label.setText(status)
            self._log(f"Concluído: {status}")
            if failed:
                QMessageBox.warning(self, "Concluído com falhas", status)
            else:
                QMessageBox.information(self, "Concluído", status)
        else:
            self.download_status_label.setText(f"{len(outputs)} ficheiro(s) gerado(s)." if self.lang == "pt" else f"{len(outputs)} file(s) generated.")
            self._log(f"Concluído: {len(outputs)} ficheiro(s).")
            QMessageBox.information(self, "Concluído", f"{len(outputs)} ficheiro(s) gerado(s).")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Opto Downloader")
    win = App()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

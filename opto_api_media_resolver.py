#!/usr/bin/env python3
"""
opto_api_media_resolver.py — Resolver MPD/PSSH via API OPTO
===========================================================

Protótipo CLI para obter dados de reprodução de um episódio sem browser,
sem Playwright/Selenium e sem console/network scraping.

Fluxo:
    episódio URL/UUID
      -> /api/v1/content/item/{episode_uuid}
      -> media_id
      -> /api/v1/content/media/{media_id}
      -> vod_id (Kaltura entryId)
      -> Kaltura playManifest MPD
      -> PSSH extraído do MPD

Requisitos mínimos:
    pip install requests pywidevine yt-dlp

Para download completo:
    ficheiro .wvd em secrets/, ~/.wvd/ ou pasta da app antiga
    ffmpeg/ffprobe no PATH
    mp4decrypt (Bento4) no PATH ou vendor/bin

Uso:
    python3 opto_api_media_resolver.py "URL_DO_EPISODIO"
    python3 opto_api_media_resolver.py "URL_DO_EPISODIO" --json
    python3 opto_api_media_resolver.py "UUID_DO_EPISODIO" --test-keys --json
    python3 opto_api_media_resolver.py "URL_DO_EPISODIO" --download --quality 720
    python3 opto_api_media_resolver.py "URL_DO_EPISODIO" --download --keys "KID:KEY"
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERRO: instala o requests primeiro:  pip install requests", file=sys.stderr)
    sys.exit(1)


SCRIPT_DIR = Path(__file__).resolve().parent
FROZEN_DIRS = []
if getattr(sys, "frozen", False):
    FROZEN_DIRS.append(Path(sys.executable).resolve().parent)
    if hasattr(sys, "_MEIPASS"):
        FROZEN_DIRS.append(Path(sys._MEIPASS).resolve())
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "downloads"
SECRETS_DIR = SCRIPT_DIR / "secrets"
VENDOR_DIR = SCRIPT_DIR / "vendor"

BASE_SITE = "https://opto.sic.pt"
BASE_CONTENT_API = "https://opto.sic.pt/api/v1/content"
KALTURA_PARTNER_ID = "4526593"
KALTURA_SP_ID = "452659300"
KALTURA_UI_CONF_ID = "49763553"
KALTURA_CLIENT_TAG = "html5:v7.250"
KALTURA_WIDEVINE_LICENSE = "https://prod.udrmv3.kaltura.com/cenc/widevine/license"
KALTURA_API_MULTIREQUEST = "https://cdnapisec.kaltura.com/api_v3/service/multirequest"

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "pt-PT,pt;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://opto.sic.pt/",
    "Origin": "https://opto.sic.pt",
}

MPD_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://opto.sic.pt/",
    "Origin": "https://opto.sic.pt",
}


def log(msg):
    print(msg, flush=True)


PROGRESS_CALLBACK = None
CANCEL_CALLBACK = None


def set_progress_callback(callback):
    global PROGRESS_CALLBACK
    PROGRESS_CALLBACK = callback


def set_cancel_callback(callback):
    global CANCEL_CALLBACK
    CANCEL_CALLBACK = callback


def should_cancel():
    if not CANCEL_CALLBACK:
        return False
    try:
        return bool(CANCEL_CALLBACK())
    except Exception:
        return False


def emit_progress(event, data):
    if PROGRESS_CALLBACK:
        try:
            PROGRESS_CALLBACK(event, data)
        except Exception:
            pass


def resolve_tool(name: str):
    if not name:
        return None
    candidates = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        candidates.append(f"{name}.exe")
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    local_folders = [
        VENDOR_DIR / "bin",
        VENDOR_DIR / "tools",
        SCRIPT_DIR / "bin",
        SCRIPT_DIR / "tools",
        SCRIPT_DIR,
    ]
    for base in FROZEN_DIRS:
        local_folders.extend([
            base / "vendor" / "bin",
            base / "vendor" / "tools",
            base / "bin",
            base / "tools",
            base,
        ])

    local_folders.extend([
        Path.home() / "Documents" / "sic-opto-downloader-macos" / "vendor" / "bin",
        Path.home() / "Documents" / "sic-opto-downloader-macos" / "vendor" / "tools",
        Path.home() / "Downloads" / "sic-opto-downloader-macos" / "vendor" / "bin",
        Path.home() / "Downloads" / "sic-opto-downloader-macos" / "vendor" / "tools",
    ])

    for folder in local_folders:
        if not folder.exists():
            continue
        for candidate in candidates:
            direct = folder / candidate
            if direct.is_file():
                return str(direct)
            hits = list(folder.rglob(candidate))
            if hits:
                return str(hits[0])
    return None


TOOLS = {
    "yt-dlp": resolve_tool("yt-dlp") or "yt-dlp",
    "mp4decrypt": resolve_tool("mp4decrypt") or "mp4decrypt",
    "ffmpeg": resolve_tool("ffmpeg") or "ffmpeg",
    "ffprobe": resolve_tool("ffprobe") or "ffprobe",
}


def parse_uuid(value: str) -> str:
    """Aceita URL OPTO ou UUID puro e devolve o primeiro UUID encontrado."""
    match = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        value or "",
        re.I,
    )
    return match.group(0) if match else ""


def api_get_json(url: str, params: dict | None = None) -> dict:
    response = requests.get(url, headers=HEADERS, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_text(url: str) -> tuple[str, str]:
    response = requests.get(
        url,
        headers=MPD_HEADERS,
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.text, response.url


def find_wvd_files():
    candidates = [
        SECRETS_DIR,
        SCRIPT_DIR,
        Path.home() / ".wvd",
        Path.home() / "Documents" / "sic-opto-downloader-macos" / "secrets",
        Path.home() / "Documents" / "sic-opto-downloader-macos",
        Path.home() / "Downloads" / "sic-opto-downloader-macos" / "secrets",
        Path.home() / "Downloads" / "sic-opto-downloader-macos",
    ]
    found = []
    for folder in candidates:
        try:
            found.extend(Path(folder).expanduser().glob("*.wvd"))
        except Exception:
            pass
    return sorted({p.resolve() for p in found if p.exists()})


def build_kaltura_mpd_url(vod_id: str) -> str:
    return (
        f"https://cdnapisec.kaltura.com/p/{KALTURA_PARTNER_ID}/sp/{KALTURA_SP_ID}"
        f"/playManifest/entryId/{urllib.parse.quote(vod_id, safe='')}"
        f"/protocol/https/format/mpegdash/a.mpd"
        f"?uiConfId={KALTURA_UI_CONF_ID}&clientTag={KALTURA_CLIENT_TAG}"
    )


def fetch_kaltura_playback_context(vod_id: str, referrer: str = "") -> dict:
    """
    Replica a chamada pública do Kaltura Player:
      1. startWidgetSession
      2. baseEntry.list
      3. baseEntry.getPlaybackContext

    O getPlaybackContext devolve sources, flavorIds e DRM licenseURL assinada.
    """
    referrer = referrer or "https://opto.sic.pt/"
    payload = {
        "format": 1,
        "clientTag": KALTURA_CLIENT_TAG,
        "apiVersion": "3.3.0",
        "partnerId": KALTURA_PARTNER_ID,
        "1:service": "session",
        "1:action": "startWidgetSession",
        "1:widgetId": f"_{KALTURA_PARTNER_ID}",
        "2:service": "baseentry",
        "2:action": "list",
        "2:ks": "{1:result:ks}",
        "2:filter:objectType": "KalturaBaseEntryFilter",
        "2:filter:idEqual": vod_id,
        "3:service": "baseentry",
        "3:action": "getPlaybackContext",
        "3:ks": "{1:result:ks}",
        "3:entryId": vod_id,
        "3:contextDataParams:objectType": "KalturaContextDataParams",
        "3:contextDataParams:flavorTags": "all",
        "3:contextDataParams:streamerType": "mpegdash",
        "3:contextDataParams:mediaProtocol": "https",
        "3:contextDataParams:referrer": referrer,
    }
    response = requests.post(
        KALTURA_API_MULTIREQUEST,
        headers=HEADERS,
        data=payload,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or len(data) < 3:
        raise RuntimeError("Resposta multirequest inesperada.")
    for part in data:
        if isinstance(part, dict) and part.get("objectType") == "KalturaAPIException":
            raise RuntimeError(f"Kaltura multirequest: {part.get('message')}")

    session = data[0] if isinstance(data[0], dict) else {}
    entry_list = data[1] if isinstance(data[1], dict) else {}
    playback = data[2] if isinstance(data[2], dict) else {}
    sources = playback.get("sources") or []

    dash_sources = [
        source for source in sources
        if source.get("format") == "mpegdash" and source.get("url")
    ]
    selected_source = dash_sources[0] if dash_sources else (sources[0] if sources else {})

    widevine_license = ""
    for source in sources:
        for drm in source.get("drm") or []:
            if drm.get("scheme") == "drm.WIDEVINE_CENC" and drm.get("licenseURL"):
                widevine_license = drm["licenseURL"]
                selected_source = source
                break
        if widevine_license:
            break

    return {
        "ks": session.get("ks", ""),
        "entry": (entry_list.get("objects") or [{}])[0] if entry_list.get("objects") else {},
        "sources": sources,
        "source_url": selected_source.get("url", ""),
        "flavor_ids": selected_source.get("flavorIds", ""),
        "widevine_license_url": widevine_license,
    }


def extract_pssh_values(mpd_text: str) -> list[str]:
    values = []
    for pattern in (
        r"<cenc:pssh[^>]*>([A-Za-z0-9+/=]+)</cenc:pssh>",
        r"<ContentProtection[^>]*>.*?<cenc:pssh[^>]*>([A-Za-z0-9+/=]+)</cenc:pssh>",
    ):
        for hit in re.findall(pattern, mpd_text, re.DOTALL | re.IGNORECASE):
            pssh = hit.strip()
            if pssh and pssh not in values:
                values.append(pssh)
    return values


def list_mpd_qualities(mpd_text: str) -> list[dict]:
    qualities = []
    rep_re = re.compile(
        r"<Representation\b(?P<attrs>[^>]*)>",
        re.IGNORECASE | re.DOTALL,
    )
    attr_re = re.compile(r'([A-Za-z_:][-A-Za-z0-9_:.]*)="([^"]*)"')
    for match in rep_re.finditer(mpd_text):
        attrs = dict(attr_re.findall(match.group("attrs")))
        if not attrs.get("height"):
            continue
        qualities.append({
            "id": attrs.get("id", ""),
            "height": int(attrs.get("height") or 0),
            "width": int(attrs.get("width") or 0),
            "bandwidth": int(attrs.get("bandwidth") or 0),
            "codecs": attrs.get("codecs", ""),
        })
    qualities.sort(key=lambda q: (q["height"], q["bandwidth"]), reverse=True)
    return qualities


def get_keys_with_pywidevine(pssh_b64: str, license_url: str, wvd_path: str) -> list[str]:
    try:
        from pywidevine.cdm import Cdm
        from pywidevine.device import Device
        from pywidevine.pssh import PSSH
    except ImportError as exc:
        raise RuntimeError("pywidevine não está instalado.") from exc

    device = Device.load(wvd_path)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    try:
        challenge = cdm.get_license_challenge(session_id, PSSH(pssh_b64))
        session = requests.Session()
        session.headers.update(MPD_HEADERS)
        response = session.post(license_url, data=bytes(challenge), timeout=30)
        response.raise_for_status()
        cdm.parse_license(session_id, response.content)
        keys = []
        for key in cdm.get_keys(session_id):
            if key.type == "CONTENT":
                keys.append(f"{key.kid.hex}:{key.key.hex()}")
        return keys
    finally:
        cdm.close(session_id)


def compact_ytdlp_logger(label):
    state = {"bucket": -1}
    important = (
        "error", "warning", "failed", "unable", "destination",
        "merging", "decrypt", "fixing", "already"
    )

    def _log(line):
        stripped = line.strip()
        if not stripped:
            return
        if "[download]" in stripped:
            match = re.search(r"(\d+(?:\.\d+)?)%", stripped)
            if match:
                pct = float(match.group(1))
                speed_match = re.search(r"\bat\s+([^\s]+(?:/s)?)", stripped)
                eta_match = re.search(r"\bETA\s+([0-9:]+)", stripped)
                emit_progress("download", {
                    "stream": label,
                    "percent": pct,
                    "speed": speed_match.group(1) if speed_match else "",
                    "eta": eta_match.group(1) if eta_match else "",
                })
                bucket = int(pct // 10) * 10
                if bucket != state["bucket"] or pct >= 99.9:
                    state["bucket"] = bucket
                    log(f"{label}: {pct:.0f}%")
                return
            if "100%" not in stripped and "Destination:" not in stripped:
                return
        if any(token in stripped.lower() for token in important):
            log(stripped)
    return _log


def run_cmd(cmd, cwd=None, line_filter=None):
    log(f"▶ {' '.join(str(part) for part in cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in proc.stdout or []:
        if should_cancel():
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            log("Processo cancelado.")
            return 130
        if line_filter:
            line_filter(line)
        else:
            log(line.rstrip())
    proc.wait()
    return proc.returncode


def run_cmd_quiet(cmd, cwd=None):
    log(f"▶ {' '.join(str(part) for part in cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    out = []
    while True:
        if should_cancel():
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            log("Processo cancelado.")
            return 130
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            out.append(line)
        elif proc.poll() is not None:
            break
        else:
            time.sleep(0.1)
    if proc.returncode != 0:
        log("\n".join("".join(out).splitlines()[-15:]))
    return proc.returncode


def find_downloaded_file(base, exts):
    base = str(base)
    for ext in exts:
        candidate = base.rsplit(".", 1)[0] + ext
        if Path(candidate).exists():
            return candidate
        hits = list(Path(base).parent.glob(f"*{ext}"))
        if hits:
            return str(hits[0])
    return base if Path(base).exists() else ""


def resolve_video_format_id(mpd_url, quality):
    if not quality or quality == "best":
        return "bestvideo"
    max_h = int(quality)
    log(f"A escolher stream <= {max_h}p...")
    proc = subprocess.run(
        [TOOLS["yt-dlp"], "--allow-unplayable-formats", "-J", mpd_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        log(f"yt-dlp -J falhou; a usar bestvideo: {proc.stderr[:300]}")
        return "bestvideo"
    json_start = proc.stdout.find("{")
    if json_start < 0:
        return "bestvideo"
    info = json.loads(proc.stdout[json_start:])
    candidates = [
        fmt for fmt in info.get("formats", [])
        if (fmt.get("vcodec") and fmt.get("vcodec") != "none")
        and (not fmt.get("acodec") or fmt.get("acodec") == "none")
        and fmt.get("height") and fmt["height"] <= max_h
    ]
    if not candidates:
        log(f"Sem streams <= {max_h}p; a usar bestvideo.")
        return "bestvideo"
    best = max(candidates, key=lambda fmt: (fmt.get("height", 0), fmt.get("tbr", 0)))
    log(f"Stream: {best['format_id']} ({best.get('height')}p)")
    return best["format_id"]


def validate_final_media(path):
    ffprobe = resolve_tool(TOOLS["ffprobe"])
    if not ffprobe:
        return True
    log("A validar ficheiro final...")
    proc = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,codec_name",
            "-of", "json",
            path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        log("ffprobe falhou.")
        return False
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    duration = float(data.get("format", {}).get("duration") or 0)
    log(f"{duration:.1f}s | vídeo:{has_video} | áudio:{has_audio}")
    return has_video and has_audio and duration >= 5


def download_decrypt_mux(mpd_url, keys, output_dir, output_name, quality="best"):
    if should_cancel():
        raise RuntimeError("Download cancelado.")
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="sic_opto_api_"))
    log(f"Temp: {tmp_dir}")

    try:
        video_enc = tmp_dir / "video_enc.mp4"
        audio_enc = tmp_dir / "audio_enc.m4a"
        if should_cancel():
            raise RuntimeError("Download cancelado.")
        video_fmt = resolve_video_format_id(mpd_url, quality)
        results = {"video": None, "audio": None}

        def download_video():
            results["video"] = run_cmd(
                [
                    TOOLS["yt-dlp"], "--allow-unplayable-formats",
                    "--newline",
                    "--concurrent-fragments", "32",
                    "-f", video_fmt, "-o", str(video_enc), mpd_url,
                ],
                cwd=str(tmp_dir),
                line_filter=compact_ytdlp_logger("vídeo"),
            )

        def download_audio():
            results["audio"] = run_cmd(
                [
                    TOOLS["yt-dlp"], "--allow-unplayable-formats",
                    "--newline",
                    "--concurrent-fragments", "32",
                    "-f", "bestaudio", "-o", str(audio_enc), mpd_url,
                ],
                cwd=str(tmp_dir),
                line_filter=compact_ytdlp_logger("áudio"),
            )

        t_video = threading.Thread(target=download_video)
        t_audio = threading.Thread(target=download_audio)
        t_video.start()
        t_audio.start()
        t_video.join()
        t_audio.join()

        if should_cancel():
            raise RuntimeError("Download cancelado.")
        if results["video"] != 0 or results["audio"] != 0:
            raise RuntimeError("Download falhou.")
        emit_progress("stage", {"status": "A localizar ficheiros", "percent": 72})

        video_enc_path = find_downloaded_file(video_enc, [".mp4", ".mkv", ".webm"])
        audio_enc_path = find_downloaded_file(audio_enc, [".m4a", ".aac", ".opus", ".mp4"])
        if not video_enc_path or not audio_enc_path:
            raise RuntimeError("Ficheiros encriptados não encontrados.")

        mp4decrypt = resolve_tool(TOOLS["mp4decrypt"])
        if not mp4decrypt:
            raise RuntimeError("mp4decrypt não encontrado.")
        key_args = []
        for key in keys:
            parts = key.strip().split(":")
            if len(parts) == 2:
                key_args += ["--key", f"{parts[0]}:{parts[1]}"]
        if not key_args:
            raise RuntimeError("Keys inválidas.")

        if should_cancel():
            raise RuntimeError("Download cancelado.")
        emit_progress("stage", {"status": "A desencriptar", "percent": 78})
        video_dec = tmp_dir / "video_dec.mp4"
        audio_dec = tmp_dir / "audio_dec.m4a"
        if run_cmd([mp4decrypt] + key_args + [video_enc_path, str(video_dec)]) != 0:
            raise RuntimeError("mp4decrypt falhou no vídeo.")
        if run_cmd([mp4decrypt] + key_args + [audio_enc_path, str(audio_dec)]) != 0:
            raise RuntimeError("mp4decrypt falhou no áudio.")

        if should_cancel():
            raise RuntimeError("Download cancelado.")
        safe_name = re.sub(r"[^\w\-_. ]", "_", output_name or "SIC_OPTO")
        final_out = output_dir / f"{safe_name}.mp4"
        emit_progress("stage", {"status": "A juntar vídeo e áudio", "percent": 90})
        ffmpeg_cmd = [
            TOOLS["ffmpeg"], "-hide_banner", "-loglevel", "warning", "-y",
            "-i", str(video_dec), "-i", str(audio_dec),
            "-c", "copy", "-movflags", "+faststart", str(final_out),
        ]
        if run_cmd_quiet(ffmpeg_cmd) != 0 or not final_out.exists():
            raise RuntimeError("ffmpeg falhou.")
        emit_progress("stage", {"status": "A validar ficheiro", "percent": 96})
        if not validate_final_media(str(final_out)):
            invalid = final_out.with_suffix(".invalid.mp4")
            final_out.replace(invalid)
            raise RuntimeError(f"Ficheiro final inválido: {invalid}")
        log(f"Concluído: {final_out}")
        return str(final_out)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def resolve_episode_media(episode_url_or_uuid: str) -> dict:
    episode_uuid = parse_uuid(episode_url_or_uuid)
    if not episode_uuid:
        raise ValueError(f"Não encontrei UUID em: {episode_url_or_uuid}")

    item_url = f"{BASE_CONTENT_API}/item/{episode_uuid}"
    item = api_get_json(item_url)
    media_id = item.get("media_id") or ""
    if not media_id:
        raise RuntimeError("A resposta do episódio não trouxe media_id.")

    media_url = f"{BASE_CONTENT_API}/media/{media_id}"
    media = api_get_json(media_url)
    vod_id = media.get("vod_id") or ""
    if not vod_id:
        raise RuntimeError("A resposta media não trouxe vod_id.")

    referrer = (
        episode_url_or_uuid
        if episode_url_or_uuid.startswith("http")
        else f"{BASE_SITE}/vod/{episode_uuid}"
    )
    playback_context = {}
    license_url = KALTURA_WIDEVINE_LICENSE
    try:
        playback_context = fetch_kaltura_playback_context(vod_id, referrer=referrer)
        license_url = playback_context.get("widevine_license_url") or license_url
    except Exception as exc:
        playback_context = {"error": str(exc)}

    mpd_candidate_url = playback_context.get("source_url") or build_kaltura_mpd_url(vod_id)
    mpd_text, mpd_url = fetch_text(mpd_candidate_url)
    pssh_values = extract_pssh_values(mpd_text)
    qualities = list_mpd_qualities(mpd_text)

    return {
        "episode_uuid": episode_uuid,
        "episode_url": episode_url_or_uuid if episode_url_or_uuid.startswith("http") else "",
        "title": item.get("title", ""),
        "reference": item.get("reference", ""),
        "media_id": media_id,
        "vod_id": vod_id,
        "mpd_candidate_url": mpd_candidate_url,
        "mpd_url": mpd_url,
        "license_url": license_url,
        "license_source": "kaltura_playback_context" if license_url != KALTURA_WIDEVINE_LICENSE else "fallback",
        "flavor_ids": playback_context.get("flavor_ids", ""),
        "playback_context_error": playback_context.get("error", ""),
        "pssh": pssh_values[0] if pssh_values else "",
        "pssh_count": len(pssh_values),
        "pssh_values": pssh_values,
        "qualities": qualities,
        "duration": item.get("duration") or 0,
        "season": (item.get("season") or {}).get("season") if isinstance(item.get("season"), dict) else "",
        "episode": item.get("episode_number") or item.get("episode_order") or "",
    }


def default_output_name(data: dict) -> str:
    title = data.get("title") or "SIC_OPTO"
    season = data.get("season")
    episode = data.get("episode")
    suffix = ""
    if season and episode:
        suffix = f"_T{int(season):02d}E{int(episode):02d}"
    return f"{title}{suffix}"


def parse_manual_keys(raw: str) -> list[str]:
    if not raw:
        return []
    keys = []
    for item in raw.replace(",", "\n").splitlines():
        item = item.strip()
        if re.match(r"^[0-9a-fA-F-]{32,36}:[0-9a-fA-F]{32}$", item):
            keys.append(item)
    return keys


def main():
    parser = argparse.ArgumentParser(
        description="Resolve MPD/PSSH de um episódio OPTO usando só APIs HTTP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 opto_api_media_resolver.py "https://opto.sic.pt/vod/a-heranca-t3-e320/63abca1d-0070-4db1-b6e0-03bd0ba834fa"
  python3 opto_api_media_resolver.py "63abca1d-0070-4db1-b6e0-03bd0ba834fa" --json
  python3 opto_api_media_resolver.py "URL_DO_EPISODIO" --test-keys --json
  python3 opto_api_media_resolver.py "URL_DO_EPISODIO" --download --quality 720
  python3 opto_api_media_resolver.py "URL_DO_EPISODIO" --download --keys "KID:KEY"
""",
    )
    parser.add_argument("episode", help="URL ou UUID do episódio OPTO.")
    parser.add_argument("--json", action="store_true", help="Imprime resultado em JSON.")
    parser.add_argument(
        "--test-keys",
        action="store_true",
        help="Tenta obter keys com pywidevine usando o primeiro PSSH e .wvd encontrado.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Faz download completo: keys, yt-dlp, mp4decrypt e ffmpeg.",
    )
    parser.add_argument(
        "--license-url",
        default="",
        help="Override da license URL. Útil se a license assinada for capturada noutro fluxo.",
    )
    parser.add_argument(
        "--keys",
        default="",
        help="Keys manuais KID:KEY, separadas por vírgula ou nova linha. Salta pywidevine.",
    )
    parser.add_argument(
        "--quality",
        default="best",
        choices=("best", "1080", "720", "540", "480", "360"),
        help="Qualidade máxima de vídeo para --download. Default: best.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Pasta de saída para --download. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--output-name",
        default="",
        help="Nome do MP4 final sem extensão. Default: título + TxxExx.",
    )
    args = parser.parse_args()

    data = resolve_episode_media(args.episode)
    if args.license_url:
        data["license_url"] = args.license_url

    keys = []
    manual_keys = parse_manual_keys(args.keys)
    if manual_keys:
        keys = manual_keys
        data["keys_ok"] = True
        data["key_count"] = len(keys)
        data["keys_source"] = "manual"
    elif args.test_keys or args.download:
        if not data["pssh"]:
            raise RuntimeError("Sem PSSH para testar keys.")
        wvds = find_wvd_files()
        if not wvds:
            raise RuntimeError(".wvd não encontrado.")
        keys = get_keys_with_pywidevine(data["pssh"], data["license_url"], str(wvds[0]))
        data["keys_ok"] = bool(keys)
        data["key_count"] = len(keys)
        data["wvd"] = str(wvds[0])
        data["keys_source"] = "pywidevine"
        if not keys:
            raise RuntimeError("Não foi possível obter keys.")

    if args.download:
        output_name = args.output_name or default_output_name(data)
        data["output_path"] = download_decrypt_mux(
            data["mpd_url"],
            keys,
            args.output_dir,
            output_name,
            args.quality,
        )

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print(f"Episódio: {data['title']} T{data['season']}E{data['episode']}")
    print(f"UUID:     {data['episode_uuid']}")
    print(f"media_id: {data['media_id']}")
    print(f"vod_id:   {data['vod_id']}")
    print(f"MPD:      {data['mpd_url']}")
    print(f"License:  {data['license_url']}")
    print(f"PSSH:     {data['pssh'][:90]}{'...' if len(data['pssh']) > 90 else ''}")
    print(f"PSSHs:    {data['pssh_count']}")
    if data["qualities"]:
        pretty = ", ".join(
            f"{q['height']}p" for q in data["qualities"] if q.get("height")
        )
        print(f"Qual.:    {pretty}")
    if args.test_keys:
        print(f"Keys:     {'OK' if data.get('keys_ok') else 'Falhou'} ({data.get('key_count', 0)})")
    if args.download:
        print(f"MP4:      {data['output_path']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)

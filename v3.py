#!/usr/bin/env python3
"""
SIC OPTO Downloader
====================
Usa Selenium + Chrome DevTools Protocol para capturar MPD e License URL
da tua sessão autenticada, depois descarrega e desencripta com pywidevine.

USO PESSOAL APENAS - requer subscrição SIC OPTO ativa.

DEPENDÊNCIAS:
    pip install yt-dlp pywidevine requests selenium websocket-client
    Chrome instalado + chromedriver no PATH
    mp4decrypt (bento4): https://www.bento4.com/downloads/
    ffmpeg: https://ffmpeg.org/download.html
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import subprocess
import os
import sys
import re
import json
import shutil
import tempfile
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime


# ─── Configuração ─────────────────────────────────────────────────────────────

SCRIPT_DIR               = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR       = str(SCRIPT_DIR / "downloads")
DEFAULT_PROFILE_DIR      = SCRIPT_DIR / "chrome-debug-profile"
CONFIG_DIR               = SCRIPT_DIR / "config"
STATE_DIR                = SCRIPT_DIR / "state"
SECRETS_DIR              = SCRIPT_DIR / "secrets"
VENDOR_DIR               = SCRIPT_DIR / "vendor"
EXTENSIONS_DIR           = VENDOR_DIR / "extensions"
UBLOCK_EXTENSION_DIR     = EXTENSIONS_DIR / "ublock-origin-lite"
CONFIG_FILE              = CONFIG_DIR / "sic_opto_config.json"
LEGACY_CONFIG_FILE       = SCRIPT_DIR / "sic_opto_config.json"

CACHE_FILE = STATE_DIR / "sic_opto_cache.json"
LEGACY_CACHE_FILE = SCRIPT_DIR / "sic_opto_cache.json"
CHROME_LAUNCH_LOG = STATE_DIR / "chrome_launch.log"

def _read_json(primary_path, legacy_path=None):
    for path in (primary_path, legacy_path):
        if path and path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
    return {}

def project_path(path):
    """Resolve caminhos relativos à pasta do projeto."""
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = SCRIPT_DIR / p
    return p

def find_wvd_files():
    return (list(SECRETS_DIR.glob("*.wvd")) +
            list(SCRIPT_DIR.glob("*.wvd")) +
            list(Path.home().glob("*.wvd")) +
            list(Path.home().glob(".wvd/*.wvd")))

def chrome_extension_args():
    manifest = UBLOCK_EXTENSION_DIR / "manifest.json"
    if manifest.exists():
        ext_dir = str(UBLOCK_EXTENSION_DIR)
        return [
            f"--disable-extensions-except={ext_dir}",
            f"--load-extension={ext_dir}",
        ]
    return []

def centered_app_geometry(screen_w=None, screen_h=None):
    screen_w = int(screen_w or 1366)
    screen_h = int(screen_h or 768)
    app_w = max(760, min(1040, int(screen_w * 0.58)))
    app_h = max(660, min(820, screen_h - 120))
    app_x = max(0, (screen_w - app_w) // 2)
    app_y = max(0, (screen_h - app_h) // 2)
    return app_w, app_h, app_x, app_y

def chrome_start_args():
    return [
        "--start-minimized",
        "--mute-audio",
        "--autoplay-policy=user-gesture-required",
        "--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies",
    ]

def load_cache():
    return _read_json(CACHE_FILE, LEGACY_CACHE_FILE)

def save_cache(data):
    try:
        existing = load_cache()
        existing.update(data)
        CACHE_FILE.parent.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    except Exception:
        pass

DOWNLOADS_FILE = STATE_DIR / "sic_opto_downloads.json"
LEGACY_DOWNLOADS_FILE = SCRIPT_DIR / "sic_opto_downloads.json"

def load_downloads():
    """Carrega registo de downloads concluídos: {ep_uuid: {path, date, title}}"""
    return _read_json(DOWNLOADS_FILE, LEGACY_DOWNLOADS_FILE)

def save_download(ep_url, title, path):
    """Regista episódio como descarregado com sucesso."""
    try:
        data = load_downloads()
        # Usar UUID do URL como chave
        uuid = ep_url.rstrip("/").split("/")[-1]
        data[uuid] = {
            "title": title,
            "path": str(path),
            "url": ep_url,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        DOWNLOADS_FILE.parent.mkdir(exist_ok=True)
        DOWNLOADS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                   encoding="utf-8")
    except Exception:
        pass

def is_downloaded(ep_url):
    """Verifica se este episódio já foi descarregado e se o ficheiro ainda existe."""
    try:
        uuid = ep_url.rstrip("/").split("/")[-1]
        item = load_downloads().get(uuid)
        if not item:
            return False
        path = item.get("path")
        return bool(path and Path(path).exists())
    except Exception:
        return False

def cache_key(series_url):
    """Chave de cache baseada no UUID da série."""
    m = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', series_url, re.I)
    return f"series_{m.group()}" if m else None

KALTURA_WIDEVINE_LICENSE = "https://prod.udrmv3.kaltura.com/cenc/widevine/license"
OPTO_API_BASE            = "https://opto.sic.pt/api"
KALTURA_PARTNER_ID       = "4526593"
KALTURA_SP_ID            = "452659300"
DEBUG_PORT               = 9222

DEFAULT_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

# ─── Config persistente ────────────────────────────────────────────────────────

def load_config():
    return _read_json(CONFIG_FILE, LEGACY_CONFIG_FILE)

def save_config(data):
    try:
        existing = load_config()
        existing.update(data)
        CONFIG_FILE.parent.mkdir(exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass

# ─── Ferramentas ───────────────────────────────────────────────────────────────

def resolve_tool(name):
    if not name:
        return None
    candidates = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        candidates.append(f"{name}.exe")
    for c in candidates:
        found = shutil.which(c)
        if found:
            return found
    for folder in (
        VENDOR_DIR / "bin",
        VENDOR_DIR / "tools",
        SCRIPT_DIR / "bin",
        SCRIPT_DIR / "tools",
        SCRIPT_DIR,
    ):
        if not folder.exists():
            continue
        for c in candidates:
            direct = folder / c
            if direct.is_file():
                return str(direct)
            hits = list(folder.rglob(c))
            if hits:
                return str(hits[0])
    return None

def find_chrome():
    cfg = load_config()
    if cfg.get("chrome_exe") and Path(cfg["chrome_exe"]).exists():
        return cfg["chrome_exe"]
    for p in DEFAULT_CHROME_PATHS:
        if Path(p).exists():
            return p
    return resolve_tool("google-chrome") or resolve_tool("chromium-browser") or ""

TOOLS = {
    "yt-dlp":     resolve_tool("yt-dlp")     or "yt-dlp",
    "mp4decrypt": resolve_tool("mp4decrypt") or "mp4decrypt",
    "ffmpeg":     resolve_tool("ffmpeg")     or "ffmpeg",
    "ffprobe":    resolve_tool("ffprobe")    or "ffprobe",
}

# ─── Helpers URL ───────────────────────────────────────────────────────────────

def name_from_url(url):
    """Extrai nome legível do URL: .../nome-do-episodio/uuid -> 'nome-do-episodio'"""
    parts = [p for p in url.rstrip("/").split("/") if p]
    uuid_pat = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-', re.I)
    # Pegar o último segmento que não seja um UUID
    for part in reversed(parts):
        if not uuid_pat.match(part) and part not in ("vod", "series", "opto.sic.pt",
                                                       "https:", "http:"):
            return part
    return ""

def is_series_url(url):
    """Retorna True se for URL de série (sem episódio específico)."""
    return "/series/" in url and "/vod/" not in url

# ─── API OPTO ─────────────────────────────────────────────────────────────────

def api_fetch(path, cookies_str=None):
    url = f"{OPTO_API_BASE}{path}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://opto.sic.pt/",
        "Origin": "https://opto.sic.pt",
        "Accept": "application/json",
    }
    if cookies_str:
        headers["Cookie"] = cookies_str
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def get_series_episodes(series_url, log_fn, chrome_exe="", profile_dir="", profile_name="",
                        cancel_event=None):
    """
    Dado URL de série, devolve dict:
      { "T1": [{"title": "Ep1", "url": "...", "season": 1, "episode": 1}, ...], "T2": [...] }

    Usa Selenium para renderizar a página e scraping direto do DOM:
    - Cada episódio é um .mg-card-descriptive dentro de .playlist-grid
    - Título em .bodyRegularBold.text-cardText01  →  "N. Título"
    - Kaltura Entry ID extraído do thumbAssetId na imagem  →  URL do episódio
    - Temporada lida do selector de temporadas ativo
    """
    log_fn("🔎 A obter episódios da série...\n")

    def cancelled():
        return bool(cancel_event and cancel_event.is_set())

    if cancelled():
        log_fn("⏹ Scrape de série cancelado.\n")
        return {}

    # ── Cache: verificar o que já foi scrapeado ────────────────────────────
    ck = cache_key(series_url)
    cached_all = load_cache().get(ck, {}) if ck else {}
    if cached_all:
        total_cached = sum(len(v) for v in cached_all.values())
        log_fn(f"💾 Cache parcial/completa: {total_cached} episódio(s) em "
               f"{len(cached_all)} temporada(s).\n")
        log_fn(f"   (Apaga {CACHE_FILE.relative_to(SCRIPT_DIR)} para forçar novo scrape)\n")


    # Extrair UUID e slug da série do URL
    # URL: https://opto.sic.pt/series/<slug>/<uuid>
    series_uuid = None
    series_slug = None
    parts = [p for p in series_url.rstrip("/").split("/") if p]
    uuid_pat = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-', re.I)
    for i, part in enumerate(reversed(parts)):
        idx = len(parts) - 1 - i
        if uuid_pat.match(part):
            series_uuid = part
            if idx > 0:
                series_slug = parts[idx - 1]
            break

    if not series_uuid:
        log_fn("⚠ UUID da série não encontrado no URL.\n")
        return {}

    log_fn(f"   Série: {series_slug or '?'}  UUID: {series_uuid}\n")

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        log_fn("❌ pip install selenium\n")
        return {}

    # Lançar Chrome com argumentos atualizados (minimizado + extensões).
    global _chrome_proc
    if _chrome_already_running():
        log_fn("♻️  Chrome debug já ativo — a relançar com configuração atual.\n")
        _kill_chrome()
        time.sleep(1)
    if not _chrome_already_running():
        chrome_cmd = [chrome_exe or find_chrome(),
                      f"--remote-debugging-port={DEBUG_PORT}",
                      "--remote-allow-origins=*",
                      "--no-first-run"]
        chrome_cmd += chrome_start_args()
        chrome_cmd += chrome_extension_args()
        if chrome_extension_args():
            log_fn("🧩 uBlock Origin Lite: extensão carregada no Chrome.\n")
        else:
            log_fn("⚠ uBlock Origin Lite não encontrado em vendor/extensions.\n")
        profile_path = project_path(profile_dir)
        if profile_path:
            profile_path.mkdir(parents=True, exist_ok=True)
            chrome_cmd += [f"--user-data-dir={profile_path}"]
            if profile_name:
                chrome_cmd += [f"--profile-directory={profile_name}"]
        chrome_cmd += ["about:blank"]
        log_fn(f"🌐 A lançar Chrome (porta {DEBUG_PORT})...\n")
        try:
            _chrome_proc = _start_chrome_debug(chrome_cmd)
        except FileNotFoundError:
            log_fn(f"❌ Chrome não encontrado: {chrome_exe}\n")
            return {}
        for _ in range(45):
            if cancelled():
                log_fn("⏹ Scrape de série cancelado.\n")
                return {}
            if _chrome_already_running():
                log_fn("✅ Chrome ativo.\n")
                break
            if _chrome_proc.poll() is not None:
                log_fn(f"❌ Chrome fechou ao arrancar (código {_chrome_proc.returncode}).\n")
                _log_chrome_launch_failure(log_fn)
                return {}
            time.sleep(1)
        else:
            log_fn("❌ Chrome não respondeu.\n")
            _log_chrome_launch_failure(log_fn)
            _kill_chrome()
            return {}

    try:
        driver = _attach_selenium_debugger(series_url, req_lib, log_fn)
    except Exception as e:
        log_fn(f"❌ Selenium: {e}\n")
        return {}

    episodes_by_season = {}

    try:
        if cancelled():
            log_fn("⏹ Scrape de série cancelado.\n")
            return {}

        # Aguardar o grid de episódios aparecer
        wait = WebDriverWait(driver, 20)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".playlist-grid")))
        except Exception:
            log_fn("⚠ Timeout a aguardar .playlist-grid — a tentar mesmo assim...\n")
        time.sleep(2)  # deixar lazy-load das imagens começar

        # Descobrir temporadas via swiper SIC OPTO:
        #   #swiper-filters-web  .swiper-slide  →  cada slide é uma temporada
        #   O clique deve ser na div.texts dentro do slide
        #   Slide ativo tem classe "active"
        # Descobrir números das temporadas (guardar só os números, não os elementos
        # Selenium — ficam stale após navegação e causariam cliques silenciosos)
        season_nums = []
        for slide in driver.find_elements(
                By.CSS_SELECTOR, "#swiper-filters-web .swiper-slide"):
            if cancelled():
                log_fn("⏹ Scrape de série cancelado.\n")
                return {}
            label = slide.text.strip()
            if not label:
                continue
            m = re.search(r'\d+', label)
            season_nums.append(int(m.group()) if m else (len(season_nums) + 1))

        if not season_nums:
            log_fn("   Uma temporada (sem swiper de temporadas).\n")
            season_nums = [1]
        else:
            log_fn(f"   {len(season_nums)} temporada(s) encontrada(s).\n")

        def _click_season(snum):
            """Re-localiza o slide fresco e clica nele se não estiver activo."""
            if cancelled():
                return
            slides = driver.find_elements(
                By.CSS_SELECTOR, "#swiper-filters-web .swiper-slide")
            for slide in slides:
                if cancelled():
                    return
                label = slide.text.strip()
                m = re.search(r'\d+', label)
                if not m or int(m.group()) != snum:
                    continue
                if "active" in (slide.get_attribute("class") or ""):
                    return  # já activa, nada a fazer
                ct = (slide.find_elements(By.CSS_SELECTOR, ".texts") or [slide])[0]
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.4)
                driver.execute_script("arguments[0].click();", ct)
                time.sleep(2.5)
                log_fn(f"   📌 Temporada {snum} seleccionada.\n")
                return
            log_fn(f"   ⚠ Slide T{snum} não encontrado.\n")

        for season_num in season_nums:
            if cancelled():
                log_fn("⏹ Scrape de série cancelado.\n")
                return {}
            season_key = f"T{season_num}"

            # Recarregar do disco: _save_progressive pode ter atualizado o JSON
            already_scraped = (load_cache().get(ck, {}) if ck else {}).get(season_key, [])

            # Seleccionar a temporada (re-localiza o elemento fresco, sem stale)
            _click_season(season_num)

            # Se há cache, fazer scroll completo ANTES de comparar totais —
            # o scroll parcial (LAZY_LOAD_BATCH) pode coincidir com o nº em cache
            # e causar um skip prematuro (ex: 67 cache == 67 DOM parcial mas real=129).
            if already_scraped:
                log_fn(f"   🔍 T{season_num}: {len(already_scraped)} em cache — "
                       f"a verificar total real (scroll completo)...\n")
                _scroll_load_all(driver, log_fn, cancel_event=cancel_event)
            else:
                # Sem cache: scroll mínimo só para saber se há episódios
                _scroll_until_cards(driver, log_fn, need_cards=LAZY_LOAD_BATCH,
                                    cancel_event=cancel_event)

            if cancelled():
                log_fn("⏹ Scrape de série cancelado.\n")
                return {}

            total_dom = len(driver.find_elements(
                By.CSS_SELECTOR, ".playlist-grid .mg-card-descriptive"))

            # Só salta se TODOS os episódios em cache têm URL scrapeada (/vod/)
            # E o total do DOM (agora real, após scroll completo) confirma que está tudo
            all_have_url = all("/vod/" in ep.get("url", "") for ep in already_scraped)
            if already_scraped and len(already_scraped) == total_dom and total_dom > 0 and all_have_url:
                log_fn(f"   ✅ T{season_num} já completa em cache "
                       f"({len(already_scraped)} ep de {total_dom}) — a saltar.\n")
                episodes_by_season[season_key] = already_scraped
                continue

            if already_scraped and total_dom < len(already_scraped):
                log_fn(f"   ⚠ DOM carregou só {total_dom} cards, mas a cache já tem "
                       f"{len(already_scraped)}. Lazy-load incompleto — a forçar retoma.\n")
            elif already_scraped and total_dom > len(already_scraped):
                log_fn(f"   📈 T{season_num}: encontrados {total_dom} cards; cache tem "
                       f"{len(already_scraped)}. Há episódios por descobrir.\n")

            if already_scraped:
                log_fn(f"   ♻️  T{season_num}: {len(already_scraped)} em cache de "
                       f"{total_dom} reais — a retomar scrape...\n")

            # Sem cache: scroll COMPLETO para ter todos os cards no DOM (Fase 1)
            if not already_scraped:
                _scroll_load_all(driver, log_fn, cancel_event=cancel_event)

            eps = _scrape_episode_cards(
                driver, season_num, series_url, log_fn,
                ck=ck, already_scraped=already_scraped,
                cancel_event=cancel_event)
            if cancelled():
                log_fn("⏹ Scrape de série cancelado.\n")
                return {}
            if eps:
                episodes_by_season[season_key] = eps
                log_fn(f"   T{season_num}: {len(eps)} episódios\n")

    except Exception as e:
        import traceback
        log_fn(f"⚠ Erro Selenium: {e}\n{traceback.format_exc()}\n")
    # Não fechar o driver — está partilhado com o Chrome de debug

    if episodes_by_season:
        total = sum(len(v) for v in episodes_by_season.values())
        log_fn(f"✅ {total} episódio(s) em {len(episodes_by_season)} temporada(s).\n")
        if ck:
            log_fn(f"💾 Cache progressivo activo — {CACHE_FILE.name}\n")
    else:
        log_fn("⚠ Não foi possível obter episódios.\n")
        log_fn("   Certifica-te que o Chrome tem o perfil autenticado (aba CONFIG).\n")

    return episodes_by_season


LAZY_LOAD_BATCH = 30  # SIC OPTO carrega este nº de cards por batch


def _scroll_load_all(driver, log_fn, cancel_event=None):
    """Scroll completo — força o lazy-load de TODOS os cards."""
    _scroll_until_cards(driver, log_fn, need_cards=None, cancel_event=cancel_event)


def _scroll_until_cards(driver, log_fn, need_cards=None, cancel_event=None):
    """
    Scroll até ter pelo menos `need_cards` cards no DOM.
    Se need_cards=None, faz scroll completo até não aparecerem mais cards.
    """
    from selenium.webdriver.common.by import By
    CARD_SEL = ".playlist-grid .mg-card-descriptive"

    def cancelled():
        return bool(cancel_event and cancel_event.is_set())

    def count_cards():
        return len(driver.find_elements(By.CSS_SELECTOR, CARD_SEL))

    def trigger_lazy_load():
        """Tenta várias formas de acordar o lazy-load da página."""
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, CARD_SEL)
            if cards:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'end', inline:'nearest'});",
                    cards[-1]
                )
                time.sleep(0.2)
        except Exception:
            pass
        try:
            driver.execute_script("""
                window.scrollBy(0, Math.max(window.innerHeight * 0.9, 700));
                document.dispatchEvent(new Event('scroll', {bubbles: true}));
                window.dispatchEvent(new Event('scroll'));
            """)
        except Exception:
            pass
        try:
            driver.execute_script("""
                for (const el of document.querySelectorAll('*')) {
                    if (el.scrollHeight > el.clientHeight + 80) {
                        el.scrollTop = el.scrollHeight;
                        el.dispatchEvent(new Event('scroll', {bubbles: true}));
                    }
                }
            """)
        except Exception:
            pass
        try:
            more = driver.find_elements(
                By.XPATH,
                "//*[self::button or self::a or @role='button']"
                "[contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÕÔÚÇ', "
                "'abcdefghijklmnopqrstuvwxyzáàãâéêíóõôúç'), 'ver mais') "
                "or contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÕÔÚÇ', "
                "'abcdefghijklmnopqrstuvwxyzáàãâéêíóõôúç'), 'carregar mais') "
                "or contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÕÔÚÇ', "
                "'abcdefghijklmnopqrstuvwxyzáàãâéêíóõôúç'), 'mostrar mais')]"
            )
            for el in more[:2]:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.7)
                    break
        except Exception:
            pass

    if cancelled():
        return count_cards()

    current = count_cards()
    if need_cards is not None and current >= need_cards:
        return current

    if need_cards is not None:
        target_batch = ((need_cards - 1) // LAZY_LOAD_BATCH + 1) * LAZY_LOAD_BATCH
        log_fn(f"   ↕ A carregar até {target_batch} cards (preciso de {need_cards})...\n")
    else:
        target_batch = None
        log_fn("   ↕ A fazer scroll para carregar todos os episódios...\n")

    prev = current
    stale = 0
    passes = 0

    max_stale = 6 if target_batch is None else 3
    max_passes = 80 if target_batch is None else 20

    while stale < max_stale:
        if cancelled():
            log_fn("   ⏹ Scroll cancelado.\n")
            break
        passes += 1
        scroll_height = driver.execute_script("return document.body.scrollHeight")
        pos = driver.execute_script("return window.pageYOffset")
        step = 600
        while pos < scroll_height:
            if cancelled():
                log_fn("   ⏹ Scroll cancelado.\n")
                break
            pos = min(pos + step, scroll_height)
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(0.15)
            scroll_height = driver.execute_script("return document.body.scrollHeight")
            if target_batch is not None and count_cards() >= target_batch:
                break
        if cancelled():
            break
        trigger_lazy_load()
        time.sleep(0.8)
        current = count_cards()
        if current > prev:
            log_fn(f"   ↕ Pass {passes}: {current} cards (+{current - prev})\n")
            prev = current
            stale = 0
            if target_batch is not None and current >= target_batch:
                break
        else:
            stale += 1
            if target_batch is None:
                log_fn(f"   ↕ Pass {passes}: sem novos cards ({current})\n")
        if passes > max_passes:
            break

    driver.execute_script("window.scrollTo(0, 0);")
    final = count_cards()
    log_fn(f"   ✅ Scroll: {final} cards no DOM.\n")
    if target_batch is None and final <= LAZY_LOAD_BATCH:
        log_fn("   ⚠ Só foi carregado o primeiro batch. "
               "A página pode ainda não ter acordado o lazy-load.\n")
    return final


def _scrape_episode_cards(driver, season_num, series_url, log_fn, ck=None,
                          already_scraped=None, cancel_event=None):
    """
    Fase 1: lê títulos/sinopses de todos os cards no DOM (rápido).
    Fase 2: para cada card, navega de novo para a série, faz scroll
            completo (lazy-load), clica, captura URL e guarda no cache.

    ck              – chave de cache; se fornecida guarda cada episódio
                      obtido imediatamente no JSON (cache progressivo).
    already_scraped – lista de dicts já em cache para esta temporada;
                      episódios com ep_num já presente são saltados.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    CARD_SEL = ".playlist-grid .mg-card-descriptive"

    def cancelled():
        return bool(cancel_event and cancel_event.is_set())

    def get_cards():
        return driver.find_elements(By.CSS_SELECTOR, CARD_SEL)

    # ── Fase 1: ler títulos no DOM (já com scroll feito) ──────────────────
    cards_info = []
    ep_num_global = 0
    for card in get_cards():
        if cancelled():
            log_fn("   ⏹ Leitura de cards cancelada.\n")
            return []
        try:
            title_el = None
            for sel in (".bodyRegularBold.text-cardText01", ".bodyRegularBold",
                        "[class*='cardText01']"):
                els = card.find_elements(By.CSS_SELECTOR, sel)
                if els: title_el = els[0]; break
            raw = title_el.text.strip() if title_el else ""
            m = re.match(r'^(\d+)\.\s*(.*)', raw)
            if m:
                ep_num, ep_title = int(m.group(1)), m.group(2).strip() or raw
            else:
                ep_num_global += 1
                ep_num, ep_title = ep_num_global, raw or f"Ep{ep_num_global:02d}"
            desc = ""
            for sel in (".description-desktop", "[class*='cardText02']"):
                d = card.find_elements(By.CSS_SELECTOR, sel)
                if d: desc = d[0].text.strip(); break
            cards_info.append({"ep_num": ep_num, "title": ep_title, "desc": desc})
        except Exception as e:
            log_fn(f"   ⚠ Erro a ler card: {e}\n")

    total_cards = len(cards_info)
    log_fn(f"   🖱 A clicar {total_cards} cards para obter URLs...\n")

    # Episódios já em cache para esta temporada → saltar pelo ep_num
    done_ep_nums = {ep["episode"] for ep in (already_scraped or [])}
    if done_ep_nums:
        log_fn(f"   ⏭ {len(done_ep_nums)} episódio(s) já em cache — a saltar.\n")

    # Começar com os episódios já conhecidos
    episodes = list(already_scraped) if already_scraped else []

    def _save_progressive(ep_dict):
        """Guarda imediatamente este episódio no JSON de cache."""
        if not ck:
            return
        try:
            existing = load_cache()
            season_key = f"T{season_num}"
            current = existing.get(ck, {})
            season_list = current.get(season_key, [])
            # Evitar duplicados
            known_nums = {e["episode"] for e in season_list}
            if ep_dict["episode"] not in known_nums:
                season_list.append(ep_dict)
                # Ordenar por número de episódio
                season_list.sort(key=lambda e: e["episode"])
                current[season_key] = season_list
                existing[ck] = current
                CACHE_FILE.parent.mkdir(exist_ok=True)
                CACHE_FILE.write_text(
                    json.dumps(existing, indent=2, ensure_ascii=False),
                    encoding="utf-8")
        except Exception as ex:
            log_fn(f"   ⚠ Erro ao guardar cache progressivo: {ex}\n")

    # ── Fase 2: navegar à série + scroll completo + clicar ───────────────
    wait = WebDriverWait(driver, 15)
    def select_season_if_needed():
        """Re-selecionar a temporada correta após recarregar a página."""
        if cancelled():
            return
        # Aguardar o swiper aparecer
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#swiper-filters-web .swiper-slide")))
        except Exception:
            pass
        time.sleep(0.5)
        slides = driver.find_elements(By.CSS_SELECTOR, "#swiper-filters-web .swiper-slide")
        if not slides or season_num == 1:
            return  # sem swiper ou T1 já é a default
        for slide in slides:
            if cancelled():
                return
            label = slide.text.strip()
            m = re.search(r'\d+', label)
            slide_snum = int(m.group()) if m else 0
            if slide_snum != season_num:
                continue
            # Clicar sempre — mesmo que pareça "active", após reload pode não estar
            ct = (slide.find_elements(By.CSS_SELECTOR, ".texts") or [slide])[0]
            driver.execute_script("window.scrollTo(0,0);")
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", ct)
            time.sleep(2.5)
            log_fn(f"   📌 T{season_num} re-seleccionada após reload.\n")
            return
        log_fn(f"   ⚠ Slide T{season_num} não encontrado após reload.\n")

    # Cache da página carregada: evitar driver.get() + scroll_load_all
    # desnecessários quando episódios consecutivos estão na mesma carga.
    # Formato: {"url": series_url, "season": season_num, "cards": [elements]}
    _page_cache = {}

    def _ensure_page_loaded(need_index=0):
        """
        Garante que pelo menos (need_index + 1) cards estão no DOM.
        Reutiliza a página se possível; caso contrário recarrega e faz
        scroll só até ao batch que cobre o índice pretendido.
        """
        need_cards = need_index + 1
        cache_ok = (
            _page_cache.get("url") == series_url
            and _page_cache.get("season") == season_num
        )
        if cache_ok:
            cards = get_cards()
            if len(cards) >= need_cards:
                return cards
            # Página certa mas faltam cards — scroll adicional
            _scroll_until_cards(driver, log_fn, need_cards=need_cards,
                                cancel_event=cancel_event)
            return get_cards()

        # Recarregar a página
        if cancelled():
            return []
        driver.get(series_url)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, CARD_SEL)))
        except Exception:
            pass
        time.sleep(1.5)
        select_season_if_needed()
        _scroll_until_cards(driver, log_fn, need_cards=need_cards,
                            cancel_event=cancel_event)
        _page_cache["url"]    = series_url
        _page_cache["season"] = season_num
        return get_cards()

    for i, info in enumerate(cards_info):
        if cancelled():
            log_fn("⏹ Scrape de série cancelado.\n")
            break
        # Saltar episódios já em cache
        if info["ep_num"] in done_ep_nums:
            log_fn(f"   ⏭ [{i+1}/{total_cards}] E{info['ep_num']:02d} já em cache.\n")
            continue

        try:
            current_cards = _ensure_page_loaded(need_index=i)

            if i >= len(current_cards):
                log_fn(f"   ⚠ Card {i+1} fora do DOM ({len(current_cards)} disponíveis).\n")
                _page_cache.clear()
                continue

            card = current_cards[i]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", card)

            # Aguardar navegação para /vod/
            try:
                wait.until(lambda d: "/vod/" in d.current_url)
            except Exception:
                pass

            ep_url = driver.current_url
            if "/vod/" not in ep_url:
                log_fn(f"   ⚠ [{i+1}/{total_cards}] URL inesperado: {ep_url}\n")
                _page_cache.clear()
                continue

            log_fn(f"   [{i+1}/{total_cards}] {info['title'][:45]}\n"
                   f"      → {ep_url}\n")

            episodes.append({
                "title":       info["title"],
                "url":         ep_url,
                "season":      season_num,
                "episode":     info["ep_num"],
                "uuid":        ep_url.split("/")[-1],
                "description": info["desc"],
            })
            _save_progressive(episodes[-1])
            log_fn(f"      💾 cache guardado ({len(episodes)} ep)\n")

            # Página mudou após clicar — invalida só a URL do cache
            # para que _ensure_page_loaded recarregue na próxima iteração
            # mas mantenha o season_num para scroll progressivo correto.
            _page_cache.pop("url", None)

        except Exception as e:
            log_fn(f"   ⚠ Erro no card {i+1}: {e}\n")
            _page_cache.clear()

    return episodes



# ─── Gestão do Chrome ──────────────────────────────────────────────────────────

_chrome_proc = None


# ─── Gestão do Chrome ──────────────────────────────────────────────────────────

def _kill_chrome():
    global _chrome_proc
    if _chrome_proc and _chrome_proc.poll() is None:
        try:
            _chrome_proc.terminate()
            _chrome_proc.wait(timeout=5)
        except Exception:
            pass
    _chrome_proc = None
    _kill_debug_port_owner()

def _kill_debug_port_owner():
    """Fecha processos que estejam a ocupar a porta de debug do Chrome."""
    try:
        if os.name == "nt":
            r = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True, text=True, timeout=5
            )
            pids = set()
            for line in r.stdout.splitlines():
                if f":{DEBUG_PORT}" in line and "LISTENING" in line.upper():
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        pids.add(parts[-1])
            for pid in pids:
                subprocess.run(
                    ["taskkill", "/PID", pid, "/F", "/T"],
                    capture_output=True, text=True, timeout=8
                )
        else:
            r = subprocess.run(
                ["lsof", "-ti", f"tcp:{DEBUG_PORT}"],
                capture_output=True, text=True, timeout=5
            )
            for pid in {p.strip() for p in r.stdout.splitlines() if p.strip().isdigit()}:
                subprocess.run(["kill", "-TERM", pid], capture_output=True, timeout=5)
    except Exception:
        pass

def _chrome_already_running():
    try:
        import requests as rl
        return rl.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=1).status_code == 200
    except Exception:
        return False

def _start_chrome_debug(chrome_cmd):
    STATE_DIR.mkdir(exist_ok=True)
    log_file = CHROME_LAUNCH_LOG.open("w", encoding="utf-8", errors="replace")
    return subprocess.Popen(chrome_cmd, stdout=log_file, stderr=subprocess.STDOUT)

def _log_chrome_launch_failure(log_fn):
    if not CHROME_LAUNCH_LOG.exists():
        return
    try:
        lines = CHROME_LAUNCH_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return
    if not lines:
        return
    log_fn("📄 Log do Chrome:\n")
    for line in lines[-12:]:
        log_fn(f"   {line}\n")

def _get_or_create_debug_page(req_lib, url="about:blank"):
    def _pages():
        tabs = req_lib.get(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=3).json()
        return [
            t for t in tabs
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl")
        ]

    pages = _pages()
    if pages:
        return pages[-1]

    encoded_url = urllib.parse.quote(url, safe="")
    try:
        req_lib.put(f"http://127.0.0.1:{DEBUG_PORT}/json/new?{encoded_url}", timeout=3)
    except Exception:
        req_lib.get(f"http://127.0.0.1:{DEBUG_PORT}/json/new?{encoded_url}", timeout=3)
    time.sleep(1)

    pages = _pages()
    if not pages:
        raise RuntimeError("nenhuma aba page disponível no Chrome debug")
    return pages[-1]

def _attach_selenium_debugger(page_url, req_lib, log_fn):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    _get_or_create_debug_page(req_lib)
    opts = Options()
    opts.debugger_address = f"127.0.0.1:{DEBUG_PORT}"
    driver = webdriver.Chrome(options=opts)

    try:
        handles = driver.window_handles
        if handles:
            driver.switch_to.window(handles[-1])
    except Exception:
        try:
            driver.quit()
        except Exception:
            pass
        _get_or_create_debug_page(req_lib)
        driver = webdriver.Chrome(options=opts)
        handles = driver.window_handles
        if handles:
            driver.switch_to.window(handles[-1])

    log_fn(f"🔗 A navegar: {page_url}\n")
    driver.get(page_url)
    return driver

# ─── Captura CDP ───────────────────────────────────────────────────────────────

def capture_mpd_and_license(page_url, chrome_exe, profile_dir, profile_name,
                             log_fn, timeout=45):
    global _chrome_proc

    try:
        import requests as req_lib
        import websocket
    except ImportError:
        log_fn("❌ pip install requests websocket-client selenium\n")
        return None, None

    # Lançar Chrome com argumentos atualizados (minimizado + extensões).
    if _chrome_already_running():
        log_fn(f"♻️  Chrome debug já ativo — a relançar com configuração atual.\n")
        _kill_chrome()
        time.sleep(1)
    if not _chrome_already_running():
        chrome_cmd = [chrome_exe,
                      f"--remote-debugging-port={DEBUG_PORT}",
                      "--remote-allow-origins=*",
                      "--no-first-run"]
        chrome_cmd += chrome_start_args()
        chrome_cmd += chrome_extension_args()
        if chrome_extension_args():
            log_fn("🧩 uBlock Origin Lite: extensão carregada no Chrome.\n")
        else:
            log_fn("⚠ uBlock Origin Lite não encontrado em vendor/extensions.\n")
        profile_path = project_path(profile_dir)
        if profile_path:
            profile_path.mkdir(parents=True, exist_ok=True)
            chrome_cmd += [f"--user-data-dir={profile_path}"]
            if profile_name:
                chrome_cmd += [f"--profile-directory={profile_name}"]
        chrome_cmd += ["about:blank"]

        log_fn(f"🌐 A lançar Chrome (porta {DEBUG_PORT})...\n")
        try:
            _chrome_proc = _start_chrome_debug(chrome_cmd)
        except FileNotFoundError:
            log_fn(f"❌ Chrome não encontrado: {chrome_exe}\n")
            return None, None

        for i in range(45):
            if _chrome_already_running():
                log_fn("✅ Chrome ativo.\n")
                break
            if _chrome_proc.poll() is not None:
                log_fn(f"❌ Chrome fechou ao arrancar (código {_chrome_proc.returncode}).\n")
                _log_chrome_launch_failure(log_fn)
                return None, None
            time.sleep(1)
        else:
            log_fn("❌ Chrome não respondeu.\n")
            _log_chrome_launch_failure(log_fn)
            _kill_chrome()
            return None, None

    # Obter tab e abrir WebSocket ANTES de navegar
    try:
        tab    = _get_or_create_debug_page(req_lib)
        ws_url = tab["webSocketDebuggerUrl"]
    except Exception as e:
        log_fn(f"❌ Erro tabs CDP: {e}\n")
        return None, None

    mpd_url = license_url = None
    ws = None
    try:
        import websocket
        ws = websocket.create_connection(ws_url, timeout=10)
        # Ativar Network ANTES de navegar
        ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        try:
            ws.settimeout(2); ws.recv()
        except Exception:
            pass
        log_fn("✅ CDP Network ativo.\n")
    except Exception as e:
        log_fn(f"❌ WebSocket: {e}\n")
        return None, None

    # Navegar
    try:
        driver = _attach_selenium_debugger(page_url, req_lib, log_fn)
        time.sleep(4)
    except Exception as e:
        log_fn(f"⚠ Selenium: {e}\n")

    # Escutar eventos
    log_fn(f"👂 À espera de MPD/License (máx {timeout}s)...\n")
    log_fn("   Faz play no vídeo se não arrancar automaticamente.\n")
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            ws.settimeout(2)
            try:
                raw = ws.recv()
            except Exception:
                rem = int(deadline - time.time())
                if rem > 0 and rem % 10 == 0:
                    log_fn(f"   ⏳ {rem}s...\n")
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            method = msg.get("method", "")
            urls_to_check = []
            if method == "Network.responseReceived":
                urls_to_check.append(msg["params"]["response"].get("url", ""))
            elif method == "Network.requestWillBeSent":
                urls_to_check.append(msg["params"]["request"].get("url", ""))
                rr = msg["params"].get("redirectResponse")
                if rr:
                    urls_to_check.append(rr.get("url", ""))
            else:
                continue

            for url in urls_to_check:
                if not url.startswith("http"):
                    continue
                try:
                    from urllib.parse import urlparse as _up
                    _p = _up(url)
                    if not _p.hostname or "." not in _p.hostname:
                        continue
                except Exception:
                    continue
                ul = url.lower()
                if not mpd_url and (".mpd" in ul or "format/mpegdash" in ul
                                     or "playmanifest" in ul):
                    mpd_url = url
                    log_fn(f"✅ MPD: {url}\n")
                if not license_url and "license" in ul:
                    if any(x in ul for x in ["widevine","udrmv3","kaltura","license?"]):
                        license_url = url
                        log_fn(f"✅ License: {url}\n")
            if mpd_url and license_url:
                log_fn("✅ Captura completa!\n")
                break
    except Exception as e:
        log_fn(f"⚠ Escuta: {e}\n")
    finally:
        try: ws.close()
        except Exception: pass

    if not license_url:
        log_fn("⚠ License não capturada — a usar padrão Kaltura.\n")
        license_url = KALTURA_WIDEVINE_LICENSE

    return mpd_url, license_url

# ─── PSSH ─────────────────────────────────────────────────────────────────────

def extract_pssh_from_mpd(mpd_url, log_fn):
    log_fn("🔍 A extrair PSSH...\n")
    try:
        import requests as _req
        r = _req.get(mpd_url, headers={"User-Agent": "Mozilla/5.0"},
                     timeout=30, allow_redirects=True)
        r.raise_for_status()
        mpd_content = r.text
    except Exception as e:
        log_fn(f"⚠ Erro MPD (fetch): {e}\n")
        return None
    try:
        for pat in [r'<cenc:pssh[^>]*>([A-Za-z0-9+/=]+)</cenc:pssh>',
                    r'<ContentProtection[^>]*>.*?<cenc:pssh[^>]*>([A-Za-z0-9+/=]+)</cenc:pssh>']:
            hits = re.findall(pat, mpd_content, re.DOTALL | re.IGNORECASE)
            if hits:
                log_fn(f"✅ PSSH: {hits[0][:50]}...\n")
                return hits[0].strip()
        log_fn("⚠ PSSH não encontrado no MPD.\n")
    except Exception as e:
        log_fn(f"⚠ Erro MPD (parse): {e}\n")
    return None

# ─── Keys ─────────────────────────────────────────────────────────────────────

def get_keys_local(pssh_b64, license_url, log_fn):
    log_fn("🔑 A obter keys (pywidevine)...\n")
    try:
        from pywidevine.cdm import Cdm
        from pywidevine.device import Device
        from pywidevine.pssh import PSSH
        import requests
    except ImportError:
        log_fn("❌ pip install pywidevine\n")
        return None

    wvd_paths = find_wvd_files()
    if not wvd_paths:
        log_fn("❌ .wvd não encontrado. Coloca o ficheiro em secrets/.\n")
        return None

    log_fn(f"   CDM: {wvd_paths[0].name}\n")
    try:
        device     = Device.load(wvd_paths[0])
        cdm        = Cdm.from_device(device)
        sid        = cdm.open()
        challenge  = cdm.get_license_challenge(sid, PSSH(pssh_b64))
        sess       = requests.Session()
        sess.headers.update({"User-Agent": "Mozilla/5.0",
                              "Origin": "https://opto.sic.pt",
                              "Referer": "https://opto.sic.pt/"})
        resp = sess.post(license_url, data=bytes(challenge))
        resp.raise_for_status()
        cdm.parse_license(sid, resp.content)
        keys = []
        for key in cdm.get_keys(sid):
            if key.type == "CONTENT":
                k = f"{key.kid.hex}:{key.key.hex()}"
                keys.append(k)
                log_fn(f"   🗝 {k}\n")
        cdm.close(sid)
        return keys or None
    except Exception as e:
        log_fn(f"⚠ pywidevine: {e}\n")
        return None

# ─── Validação ─────────────────────────────────────────────────────────────────

def _resolve_video_format_id(mpd_url, quality, log_fn):
    """
    Lista os formatos disponíveis no MPD via yt-dlp e devolve o ID
    do melhor stream de vídeo com height <= quality.
    Com --allow-unplayable-formats o yt-dlp ignora filtros bestvideo[height<=N],
    por isso resolvemos o ID manualmente.
    """
    if not quality or quality == "best":
        return "bestvideo"
    max_h = int(quality)
    log_fn(f"   🔍 A listar formatos para escolher ≤{max_h}p...\n")
    try:
        r = subprocess.run(
            [TOOLS["yt-dlp"], "--allow-unplayable-formats", "-J", mpd_url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=30
        )
        if r.returncode != 0:
            log_fn(f"   ⚠ yt-dlp -J falhou (rc={r.returncode}):\n{r.stderr[:300]}\n")
            return "bestvideo"
        stdout = r.stdout
        json_start = stdout.find("{")
        if json_start < 0:
            log_fn(f"   ⚠ yt-dlp -J sem JSON:\n{stdout[:300]}\n")
            return "bestvideo"
        info = json.loads(stdout[json_start:])
        formats = info.get("formats", [])
        log_fn(f"   📋 {len(formats)} formatos encontrados\n")
        candidates = [
            f for f in formats
            if (f.get("vcodec") and f.get("vcodec") != "none")
            and (not f.get("acodec") or f.get("acodec") == "none")
            and f.get("height") and f["height"] <= max_h
        ]
        log_fn(f"   🎯 Candidatos ≤{max_h}p: {[f['format_id'] for f in candidates]}\n")
        if not candidates:
            log_fn(f"   ⚠ Sem streams ≤{max_h}p — a usar bestvideo\n")
            return "bestvideo"
        best = max(candidates, key=lambda f: (f.get("height", 0), f.get("tbr", 0)))
        fid = best["format_id"]
        log_fn(f"   ✅ Stream: {fid} ({best.get('height')}p, {int(best.get('tbr', 0))}k)\n")
        return fid
    except Exception as e:
        import traceback
        log_fn(f"   ⚠ Erro ao resolver formato:\n{traceback.format_exc()}\n")
        return "bestvideo"


def validate_final_media(path, log_fn):
    """Verifica se o ficheiro final tem vídeo + áudio válidos e não está encriptado."""
    ffprobe = resolve_tool(TOOLS["ffprobe"])
    if not ffprobe:
        return True
    log_fn("🔎 A validar...\n")
    p = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,codec_name",
                        "-of", "json", path],
                       capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        log_fn("❌ ffprobe falhou.\n"); return False
    data = json.loads(p.stdout)
    streams = data.get("streams", [])
    has_v = any(s.get("codec_type") == "video" for s in streams)
    has_a = any(s.get("codec_type") == "audio" for s in streams)
    try:
        dur = float(data.get("format", {}).get("duration") or 0)
    except Exception:
        dur = 0
    log_fn(f"   {dur:.1f}s | vídeo:{has_v} | áudio:{has_a}\n")
    if not has_v or not has_a or dur < 5:
        log_fn("❌ Streams inválidos.\n"); return False

    test_at = max(5, int(dur * 0.2))
    t = subprocess.run([TOOLS["ffmpeg"], "-v", "error", "-xerror",
                        "-ss", str(test_at), "-t", "8",
                        "-i", path, "-map", "0:v:0", "-map", "0:a:0?",
                        "-f", "null", "-"],
                       capture_output=True, text=True, timeout=60)
    if t.returncode != 0:
        lines = (t.stderr or t.stdout or "").splitlines()
        log_fn("❌ Stream corrompido/encriptado ou não reproduzível:\n")
        for l in lines[-8:]:
            log_fn(f"   {l}\n")
        return False
    log_fn("✅ Validação OK.\n")
    return True

# ─── Pipeline de um episódio ───────────────────────────────────────────────────

def _terminate_process(proc):
    if not proc or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

def _compact_ytdlp_logger(log_fn, label):
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
            m = re.search(r"(\d+(?:\.\d+)?)%", stripped)
            if m:
                pct = float(m.group(1))
                bucket = int(pct // 10) * 10
                if bucket != state["bucket"] or pct >= 99.9:
                    state["bucket"] = bucket
                    log_fn(f"   {label}: {pct:.0f}%\n")
                return
            if "100%" not in stripped and "Destination:" not in stripped:
                return
        if any(token in stripped.lower() for token in important):
            log_fn(line if line.endswith("\n") else line + "\n")

    return _log

def run_cmd(cmd, log_fn, cwd=None, cancel_event=None, line_filter=None):
    log_fn(f"▶ {' '.join(str(x) for x in cmd)}\n")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, cwd=cwd)
    for line in proc.stdout:
        if cancel_event and cancel_event.is_set():
            _terminate_process(proc)
            log_fn("⏹ Processo cancelado.\n")
            return 130
        if line_filter:
            line_filter(line)
        else:
            log_fn(line)
    proc.wait()
    if cancel_event and cancel_event.is_set():
        return 130
    return proc.returncode

def run_cmd_q(cmd, log_fn, cwd=None, cancel_event=None):
    log_fn(f"▶ {' '.join(str(x) for x in cmd)}\n")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, cwd=cwd)
    out = []
    while True:
        if cancel_event and cancel_event.is_set():
            _terminate_process(proc)
            log_fn("⏹ Processo cancelado.\n")
            return 130
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            out.append(line)
        elif proc.poll() is not None:
            break
        else:
            time.sleep(0.1)
    if proc.returncode != 0:
        log_fn("".join(out[-15:]))
    return proc.returncode

def process_episode(page_url, mpd_url, license_url, pssh_manual, keys_manual,
                    output_dir, output_name, chrome_exe, profile_dir, profile_name,
                    log_fn, progress_fn, quality="best", cancel_event=None):
    """
    Processa UM episódio. Devolve (True, path) ou (False, None).
    """
    def step(n, label):
        progress_fn(n / 5 * 100, label)
        log_fn(f"\n{'─'*50}\n📌 {n}/5: {label}\n{'─'*50}\n")

    os.makedirs(output_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="sic_opto_")
    log_fn(f"📁 Temp: {tmp}\n")

    try:
        # 1. Capturar MPD
        if cancel_event and cancel_event.is_set():
            log_fn("⏹ Download cancelado.\n"); return False, None
        step(1, "Capturar MPD e License (Chrome)")
        mpd = mpd_url.strip() if mpd_url and mpd_url.strip() else None
        lic = license_url.strip() if license_url and license_url.strip() else None
        if not mpd:
            mpd, lic_cap = capture_mpd_and_license(
                page_url, chrome_exe, profile_dir, profile_name, log_fn)
            if not lic: lic = lic_cap
        if not mpd:
            log_fn("❌ MPD não obtido.\n"); return False, None

        # 2. Keys
        step(2, "Obter Chaves")
        if cancel_event and cancel_event.is_set():
            log_fn("⏹ Download cancelado.\n"); return False, None
        keys = []
        if keys_manual and keys_manual.strip():
            keys = [k.strip() for k in keys_manual.replace(",","\n").splitlines()
                    if ":" in k.strip()]
            log_fn(f"✅ Keys manuais: {len(keys)}\n")
        else:
            pssh = pssh_manual.strip() if pssh_manual and pssh_manual.strip() else None
            if not pssh: pssh = extract_pssh_from_mpd(mpd, log_fn)
            if pssh and lic:
                keys = get_keys_local(pssh, lic, log_fn) or []
        if not keys:
            log_fn("❌ Sem keys. Verifica .wvd e License URL.\n"); return False, None

        # 3. Download
        step(3, "Download (yt-dlp)")
        if cancel_event and cancel_event.is_set():
            log_fn("⏹ Download cancelado.\n"); return False, None
        video_enc = os.path.join(tmp, "video_enc.mp4")
        audio_enc = os.path.join(tmp, "audio_enc.m4a")
        video_fmt = _resolve_video_format_id(mpd, quality, log_fn)

        results = {"video": None, "audio": None}

        def download_video():
            results["video"] = run_cmd([
                TOOLS["yt-dlp"], "--allow-unplayable-formats",
                "--concurrent-fragments", "32",
                "-f", video_fmt, "-o", video_enc, mpd
            ], log_fn, cwd=tmp, cancel_event=cancel_event,
                line_filter=_compact_ytdlp_logger(log_fn, "vídeo"))

        def download_audio():
            results["audio"] = run_cmd([
                TOOLS["yt-dlp"], "--allow-unplayable-formats",
                "--concurrent-fragments", "32",
                "-f", "bestaudio", "-o", audio_enc, mpd
            ], log_fn, cwd=tmp, cancel_event=cancel_event,
                line_filter=_compact_ytdlp_logger(log_fn, "áudio"))

        t_video = threading.Thread(target=download_video)
        t_audio = threading.Thread(target=download_audio)
        t_video.start(); t_audio.start()
        t_video.join();  t_audio.join()

        if cancel_event and cancel_event.is_set():
            log_fn("⏹ Download cancelado.\n")
            return False, None

        if results["video"] != 0 or results["audio"] != 0:
            log_fn("❌ Download falhou.\n")
            return False, None

        def find_file(base, exts):
            for ext in exts:
                p = base.rsplit(".", 1)[0] + ext
                if os.path.exists(p): return p
                hits = list(Path(base).parent.glob(f"*{ext}"))
                if hits: return str(hits[0])
            return base if os.path.exists(base) else None

        video_enc = find_file(video_enc, [".mp4",".mkv",".webm"]) or video_enc
        audio_enc = find_file(audio_enc, [".m4a",".aac",".opus",".mp4"]) or audio_enc
        if not os.path.exists(video_enc) or not os.path.exists(audio_enc):
            log_fn("❌ Download falhou.\n"); return False, None

        # 4. Desencriptar
        step(4, "Desencriptação (mp4decrypt)")
        if cancel_event and cancel_event.is_set():
            log_fn("⏹ Download cancelado.\n"); return False, None
        mp4d = resolve_tool(TOOLS["mp4decrypt"])
        if not mp4d:
            log_fn("❌ mp4decrypt não encontrado.\n"); return False, None
        key_args = []
        for k in keys:
            parts = k.strip().split(":")
            if len(parts) == 2:
                key_args += ["--key", f"{parts[0]}:{parts[1]}"]
        video_dec = os.path.join(tmp, "video_dec.mp4")
        audio_dec = os.path.join(tmp, "audio_dec.m4a")
        rv = run_cmd([mp4d] + key_args + [video_enc, video_dec], log_fn,
                     cancel_event=cancel_event)
        ra = run_cmd([mp4d] + key_args + [audio_enc, audio_dec], log_fn,
                     cancel_event=cancel_event)
        if rv != 0 or ra != 0:
            log_fn("❌ mp4decrypt falhou.\n"); return False, None

        # Verificação rápida
        ffprobe = resolve_tool(TOOLS["ffprobe"])
        if ffprobe:
            for lbl, fp in [("vídeo", video_dec), ("áudio", audio_dec)]:
                pr = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                                     "stream=codec_name", "-of", "json", fp],
                                    capture_output=True, text=True, timeout=20)
                if pr.returncode != 0:
                    log_fn(f"❌ {lbl} ainda encriptado!\n"); return False, None
                log_fn(f"   ✅ {lbl} OK\n")

        # 5. Muxing
        step(5, "Muxing (ffmpeg)")
        if cancel_event and cancel_event.is_set():
            log_fn("⏹ Download cancelado.\n"); return False, None
        safe_name = re.sub(r'[^\w\-_. ]', '_', output_name or "SIC_OPTO")
        final_out = os.path.join(output_dir, f"{safe_name}.mp4")

        ffmpeg_cmd = [
            TOOLS["ffmpeg"], "-hide_banner", "-loglevel", "warning", "-y",
            "-i", video_dec, "-i", audio_dec, "-c", "copy",
            "-movflags", "+faststart",
            final_out
        ]

        ret = run_cmd_q(ffmpeg_cmd, log_fn, cancel_event=cancel_event)
        if ret != 0 or not os.path.exists(final_out):
            log_fn("❌ ffmpeg falhou.\n"); return False, None
        if not validate_final_media(final_out, log_fn):
            inv = str(Path(final_out).with_suffix(".invalid.mp4"))
            os.replace(final_out, inv)
            log_fn(f"❌ Inválido: {inv}\n"); return False, None

        log_fn(f"\n✅ Concluído: {final_out}\n")
        return True, final_out

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ─── Pipeline principal (episódio único ou série) ──────────────────────────────

def download_and_decrypt(page_url, mpd_url, license_url, pssh_manual, keys_manual,
                         output_dir, output_name, chrome_exe, profile_dir, profile_name,
                         log_fn, progress_fn, done_fn,
                         batch_episodes=None, quality="best", cancel_event=None):
    """
    batch_episodes: None → episódio único
                    list  → lista de dicts {title, url, season, episode}
    """
    try:
        if batch_episodes:
            # ── Modo série ────────────────────────────────────────────────────
            total = len(batch_episodes)
            ok_count = 0
            for i, ep in enumerate(batch_episodes, 1):
                if cancel_event and cancel_event.is_set():
                    log_fn("⏹ Série cancelada.\n")
                    break
                ep_name = re.sub(r'[^\w\-_. ]', '_',
                                 f"{ep['title']}_T{ep['season']:02d}E{ep['episode']:02d}")
                log_fn(f"\n{'═'*54}\n🎬 Episódio {i}/{total}: {ep['title']}\n{'═'*54}\n")
                progress_fn(((i-1) / total) * 100, f"Ep {i}/{total}: {ep['title'][:30]}")

                success, path = process_episode(
                    ep["url"], "", "", "", "",
                    output_dir, ep_name,
                    chrome_exe, profile_dir, profile_name,
                    log_fn, lambda pct, lbl, _i=i, _t=total:
                        progress_fn((_i-1)/_t*100 + pct/_t, lbl),
                    quality=quality,
                    cancel_event=cancel_event,
                )
                if cancel_event and cancel_event.is_set():
                    log_fn("⏹ Série cancelada.\n")
                    break
                if success:
                    ok_count += 1
                    save_download(ep["url"], ep["title"], path or "")
                else:
                    log_fn(f"⚠ Episódio {ep['title']} falhou — a continuar...\n")

            all_ok = ok_count == total
            status = "Série concluída" if all_ok else "Série incompleta"
            progress_fn(100, f"{status}: {ok_count}/{total}")
            log_fn(f"\n{'✅' if all_ok else '⚠'} {status}: {ok_count}/{total} episódios.\n")
            done_fn(all_ok)

        else:
            # ── Modo episódio único ───────────────────────────────────────────
            success, path = process_episode(
                page_url, mpd_url, license_url, pssh_manual, keys_manual,
                output_dir, output_name,
                chrome_exe, profile_dir, profile_name,
                log_fn, progress_fn,
                quality=quality,
                cancel_event=cancel_event,
            )
            was_cancelled = bool(cancel_event and cancel_event.is_set())
            progress_fn(0 if was_cancelled else 100,
                        "Cancelado" if was_cancelled else "Concluído!" if success else "Falhou")
            if success and page_url:
                save_download(page_url, output_name or name_from_url(page_url), path or "")
            done_fn(success, path)

    except Exception as e:
        import traceback
        log_fn(f"\n❌ Erro inesperado: {e}\n{traceback.format_exc()}")
        done_fn(False)

# ─── Diálogo de seleção de temporada/episódios ────────────────────────────────

class SeasonSelectDialog(tk.Toplevel):
    """
    Janela de seleção de temporada e episódios.
    Retorna lista de episódios selecionados via self.result.
    """
    def __init__(self, parent, episodes_by_season, colors):
        super().__init__(parent)
        self.title("Selecionar Episódios")
        self.geometry("560x520")
        self.resizable(True, True)
        self.configure(bg=colors["BG"])
        self.transient(parent)
        self.grab_set()
        self.result = []
        self._c = colors
        self._eps = episodes_by_season
        self._vars = {}   # (season_key, idx) → BooleanVar
        self._build(episodes_by_season)

    def _build(self, eps_by_season):
        c = self._c
        tk.Label(self, text="Seleciona temporada(s) e episódios a descarregar:",
                 bg=c["BG"], fg=c["FG"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(14,6))

        # Scroll frame
        outer = tk.Frame(self, bg=c["BG"])
        outer.pack(fill="both", expand=True, padx=12, pady=4)
        canvas = tk.Canvas(outer, bg=c["BG"], highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=c["BG"])
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        for season_key in sorted(eps_by_season.keys(),
                                  key=lambda k: int(re.sub(r'\D','',k) or 0)):
            episodes = eps_by_season[season_key]

            # Header da temporada com checkbox "selecionar tudo"
            season_frame = tk.Frame(inner, bg=c["BG"])
            season_frame.pack(fill="x", pady=(8,2), padx=4)

            all_var = tk.BooleanVar(value=False)  # atualizado depois de criar ep_vars
            ep_vars = []

            def make_season_toggle(av, evs):
                def toggle():
                    v = av.get()
                    for ev in evs: ev.set(v)
                return toggle

            # Episódios
            ep_frame = tk.Frame(inner, bg=c["SURFACE"])
            ep_frame.pack(fill="x", padx=16, pady=(0,4))

            for idx, ep in enumerate(episodes):
                already_dl = is_downloaded(ep.get("url", ""))
                var = tk.BooleanVar(value=not already_dl)  # já baixado → desmarcado
                ep_vars.append(var)
                self._vars[(season_key, idx)] = var
                dl_mark = " ✅" if already_dl else ""
                lbl = f"E{ep['episode']:02d}  {ep['title']}{dl_mark}"
                cb = tk.Checkbutton(
                    ep_frame, text=lbl, variable=var,
                    bg=c["SURFACE"], fg=c["OK"] if already_dl else c["FG"],
                    selectcolor=c["PANEL"],
                    activebackground=c["SURFACE"],
                    activeforeground=c["FG"],
                    font=("Segoe UI", 9)
                )
                cb.pack(anchor="w", padx=8, pady=1)

            # Contar já descarregados para o header da temporada
            dl_count = sum(1 for ep in episodes if is_downloaded(ep.get("url", "")))
            dl_suffix = f"  —  {dl_count} já descarregado(s) ✅" if dl_count else ""
            none_selected = all(not v.get() for v in ep_vars)
            all_var.set(not none_selected)

            tk.Checkbutton(
                season_frame, text=f"  {season_key}  —  {len(episodes)} episódios{dl_suffix}",
                variable=all_var, bg=c["BG"], fg=c["ACC2"],
                selectcolor=c["PANEL"], activebackground=c["BG"],
                activeforeground=c["FG"],
                font=("Segoe UI", 10, "bold"),
                command=make_season_toggle(all_var, ep_vars)
            ).pack(side="left")

        # Botões
        bot = tk.Frame(self, bg=c["BG"])
        bot.pack(fill="x", padx=12, pady=10)
        ttk.Button(bot, text="✔  Descarregar selecionados",
                   command=self._confirm).pack(side="right", padx=(4,0))
        ttk.Button(bot, text="Cancelar", style="Sec.TButton",
                   command=self.destroy).pack(side="right")
        ttk.Button(bot, text="Selecionar tudo", style="Sec.TButton",
                   command=lambda: [v.set(True) for v in self._vars.values()]).pack(side="left")
        ttk.Button(bot, text="Limpar", style="Sec.TButton",
                   command=lambda: [v.set(False) for v in self._vars.values()]).pack(side="left", padx=4)

    def _confirm(self):
        self.result = []
        for (season_key, idx), var in self._vars.items():
            if var.get():
                self.result.append(self._eps[season_key][idx])
        self.destroy()

# ─── Interface Principal ───────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SIC OPTO Downloader")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        app_w, app_h, app_x, app_y = centered_app_geometry(sw, sh)
        self.geometry(f"{app_w}x{app_h}+{app_x}+{app_y}")
        self.resizable(True, True)
        self._cfg = load_config()
        self._series_scrape_cancel = None
        self._download_cancel = None
        self._placeholder_values = set()
        self._setup_styles()
        self.configure(bg=self._c["BG"])
        self._build_ui()
        self._load_config_to_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)


    def _on_close(self):
        _kill_chrome()
        self.destroy()


    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        BG, SURFACE, PANEL = "#f5f3ef", "#ffffff", "#ebe7df"
        FG, MUTED = "#1f2933", "#6b7280"
        ACC, ACC_HOVER = "#2f6f73", "#275f63"
        EB = "#ffffff"
        s.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("TButton", background=ACC, foreground="#fff",
                    borderwidth=0, font=("Segoe UI", 10, "bold"), padding=(14,7))
        s.map("TButton", background=[("active", ACC_HOVER), ("disabled", "#d1d5db")],
              foreground=[("disabled", "#8b949e")])
        s.configure("Sec.TButton", background=PANEL, foreground=FG,
                    borderwidth=0, font=("Segoe UI", 9), padding=(10,6))
        s.map("Sec.TButton", background=[("active", "#ded8ce"), ("disabled", "#ececec")],
              foreground=[("disabled", "#9ca3af")])
        s.configure("TEntry", fieldbackground=EB, foreground=FG,
                    insertcolor=ACC, borderwidth=1, relief="solid",
                    padding=(8, 6))
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                    padding=(16,8), font=("Segoe UI", 9, "bold"))
        s.map("TNotebook.Tab", background=[("selected", SURFACE)],
              foreground=[("selected",ACC)])
        s.configure("TProgressbar", troughcolor=PANEL, background=ACC,
                    borderwidth=0, thickness=7)
        self._c = dict(BG=BG, SURFACE=SURFACE, PANEL=PANEL, FG=FG,
                       MUTED=MUTED, ACC=ACC, EB=EB, ACC2="#9a6a23",
                       WARN="#b45309", ERR="#b42318", OK="#2f6f4e")

    # ── helpers UI ────────────────────────────────────────────────────────────
    def _lbl(self, p, text, small=False):
        c = self._c
        tk.Label(p, text=text, bg=p.cget("bg") if isinstance(p, tk.Frame) else c["BG"],
                 fg=c["MUTED"] if not small else "#8b949e",
                 font=("Segoe UI", 8 if small else 9, "bold" if not small else "normal")
                 ).pack(anchor="w", pady=(8,2))

    def _entry(self, p, var, ph=""):
        c = self._c
        e = ttk.Entry(p, textvariable=var, font=("Segoe UI", 10))
        e.pack(fill="x")
        if ph and var and not var.get():
            self._placeholder_values.add(ph)
            e.insert(0, ph); e.config(foreground="#555")
            def fi(ev, en=e, _ph=ph):
                if en.get() == _ph: en.delete(0,"end"); en.config(foreground=c["FG"])
            def fo(ev, en=e, _ph=ph):
                if not en.get(): en.insert(0,_ph); en.config(foreground="#555")
            e.bind("<FocusIn>",fi); e.bind("<FocusOut>",fo)
        return e

    def _textarea(self, p, h=2, ph=""):
        c = self._c
        t = tk.Text(p, height=h, font=("Segoe UI",10), bg=c["EB"], fg=c["FG"],
                    insertbackground=c["ACC"], relief="flat", wrap="word", borderwidth=0)
        t.pack(fill="x")
        if ph:
            t.insert("1.0", ph); t.config(fg="#555")
            def fi(ev,w=t,_ph=ph):
                if w.get("1.0","end-1c")==_ph: w.delete("1.0","end"); w.config(fg=c["FG"])
            def fo(ev,w=t,_ph=ph):
                if not w.get("1.0","end-1c").strip(): w.insert("1.0",_ph); w.config(fg="#555")
            t.bind("<FocusIn>",fi); t.bind("<FocusOut>",fo)
        return t

    def _get_text(self, w):
        v = w.get("1.0","end-1c").strip()
        return "" if w.cget("fg") in ("#555","gray50") else v

    def _clean_entry_value(self, value):
        value = (value or "").strip()
        return "" if value in self._placeholder_values else value

    # ── build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        c = self._c
        hdr = tk.Frame(self, bg=c["SURFACE"], height=58)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="SIC OPTO Downloader", bg=c["SURFACE"], fg=c["FG"],
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=18)
        tk.Label(hdr, text="uso pessoal · subscrição requerida", bg=c["SURFACE"],
                 fg=c["MUTED"], font=("Segoe UI", 9)).pack(side="right", padx=18)

        main = ttk.Frame(self, padding=(18,12))
        main.pack(fill="both", expand=True)

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True)
        for text, builder in [(" DOWNLOAD ", self._tab_dl),
                               (" AVANÇADO ", self._tab_adv),
                               (" CONFIG ",   self._tab_cfg),
                               (" LOG ",      self._tab_log)]:
            tab = ttk.Frame(nb, padding=16)
            nb.add(tab, text=text)
            if text.strip() == "CONFIG":
                builder(self._scrollable_frame(tab))
            else:
                builder(tab)

        bot = ttk.Frame(main, padding=(0,8,0,0))
        bot.pack(fill="x")
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(bot, variable=self.progress_var, maximum=100).pack(fill="x", pady=(0,5))
        self.status_var = tk.StringVar(value="Pronto.")
        tk.Label(bot, textvariable=self.status_var, bg=c["BG"], fg=c["ACC2"],
                 font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(bot, text="Limpar Log", style="Sec.TButton",
                   command=self._clear_log).pack(side="right")
        self.btn_series = ttk.Button(bot, text="📺  SÉRIE", style="Sec.TButton",
                                     command=self._start_series)
        self.btn_series.pack(side="right", padx=(4,0))
        self.btn_cancel_series = ttk.Button(bot, text="⏹  CANCELAR SCRAPE",
                                            style="Sec.TButton",
                                            command=self._cancel_series_scrape)
        self.btn_cancel_series.pack(side="right", padx=(4,0))
        self.btn_cancel_series.config(state="disabled")
        self.btn_cancel_download = ttk.Button(bot, text="⏹  CANCELAR DOWNLOAD",
                                              style="Sec.TButton",
                                              command=self._cancel_download)
        self.btn_cancel_download.pack(side="right", padx=(4,0))
        self.btn_cancel_download.config(state="disabled")
        self.btn_start = ttk.Button(bot, text="▶  INICIAR DOWNLOAD",
                                    command=self._start)
        self.btn_start.pack(side="right", padx=(8,0))

    def _scrollable_frame(self, parent):
        c = self._c
        canvas = tk.Canvas(parent, bg=c["BG"], highlightthickness=0, borderwidth=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def update_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", update_scroll)
        canvas.bind("<Configure>", update_width)
        return inner

    def _tab_dl(self, p):
        c = self._c
        self._lbl(p, "🌐  URL do episódio SIC OPTO  (ou URL de série para modo batch)")
        self.var_page = tk.StringVar()
        url_entry = self._entry(p, self.var_page,
                                "https://opto.sic.pt/vod/nome-do-episodio/uuid")
        # Auto-fill nome ao sair do campo URL
        url_entry.bind("<FocusOut>", self._autofill_name)
        url_entry.bind("<Return>",   self._autofill_name)

        self._lbl(p, "📡  MPD direto (opcional — capturado automaticamente)")
        self.var_mpd = tk.StringVar()
        self._entry(p, self.var_mpd, "https://...manifest.mpd")

        self._lbl(p, "🔒  License URL (opcional — capturada automaticamente)")
        self.var_license = tk.StringVar()
        self._entry(p, self.var_license, "https://.../license?...")

        tk.Frame(p, bg=c["PANEL"], height=1).pack(fill="x", pady=14)

        row = ttk.Frame(p); row.pack(fill="x")
        col1 = ttk.Frame(row); col1.pack(side="left", fill="x", expand=True, padx=(0,8))
        self._lbl(col1, "📝  Nome do ficheiro final (auto-preenchido pelo URL)")
        self.var_name = tk.StringVar()
        self.name_entry = self._entry(col1, self.var_name, "ex: nome-do-episodio")

        col2 = ttk.Frame(row); col2.pack(side="left", fill="x", expand=True)
        self._lbl(col2, "📁  Pasta de destino")
        dr = ttk.Frame(col2); dr.pack(fill="x")
        self.var_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        ttk.Entry(dr, textvariable=self.var_dir,
                  font=("Segoe UI",10)).pack(side="left", fill="x", expand=True)
        ttk.Button(dr, text="…", style="Sec.TButton",
                   command=self._pick_dir, width=3).pack(side="left", padx=(4,0))

        # ── Qualidade de vídeo ────────────────────────────────────────────
        self._lbl(p, "🎬  Qualidade de vídeo")
        qrow = ttk.Frame(p); qrow.pack(fill="x", pady=(2, 0))
        self.var_quality = tk.StringVar(value=load_config().get("quality", "best"))
        QUALITY_OPTIONS = [
            ("Melhor disponível", "best"),
            ("1080p", "1080"),
            ("720p",  "720"),
            ("480p",  "480"),
            ("360p",  "360"),
        ]
        for label, val in QUALITY_OPTIONS:
            tk.Radiobutton(
                qrow, text=label, variable=self.var_quality, value=val,
                bg=c["BG"], fg=c["FG"], selectcolor=c["PANEL"],
                activebackground=c["BG"], activeforeground=c["FG"],
                font=("Segoe UI", 9),
                command=lambda: save_config({"quality": self.var_quality.get()})
            ).pack(side="left", padx=(0, 10))

        info = tk.Frame(p, bg=c["PANEL"], pady=10, padx=12)
        info.pack(fill="x", pady=(12,0))
        tk.Label(info,
                 text="URL de episódio → Iniciar download\n"
                      "URL de série → Série\n"
                      "O Chrome abre com o perfil autenticado e captura o MPD automaticamente.",
                 bg=c["PANEL"], fg=c["MUTED"], font=("Segoe UI", 9),
                 justify="left").pack(anchor="w")

    def _tab_adv(self, p):
        self._lbl(p, "🔐  PSSH manual (auto-extraído se vazio)")
        self.txt_pssh = self._textarea(p, 2, "AAAAUHBzc2g...")
        self._lbl(p, "🗝  Keys manuais (KID:KEY, uma por linha)")
        self.txt_keys = self._textarea(p, 3,
            "b68ac497...:ff223450...\n(vazio = auto)")
        tk.Frame(p, bg=self._c["PANEL"], height=1).pack(fill="x", pady=14)
        self._lbl(p, "⚙️  Ferramentas")
        self.tool_vars = {}
        for tool, val in TOOLS.items():
            self._lbl(p, f"  {tool}")
            var = tk.StringVar(value=val or "")
            self.tool_vars[tool] = var
            self._entry(p, var, f"caminho para {tool}")
        ttk.Button(p, text="Verificar ferramentas", style="Sec.TButton",
                   command=self._check_tools).pack(anchor="w", pady=(10,0))

    def _tab_cfg(self, p):
        c = self._c
        tk.Label(p, text="Configuração Chrome  (guardada automaticamente)",
                 bg=c["BG"], fg=c["FG"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,8))

        self._lbl(p, "🌐  Executável do Chrome")
        self.var_chrome = tk.StringVar(value=find_chrome())
        dr = ttk.Frame(p); dr.pack(fill="x")
        ttk.Entry(dr, textvariable=self.var_chrome,
                  font=("Segoe UI",10)).pack(side="left", fill="x", expand=True)
        ttk.Button(dr, text="…", style="Sec.TButton", width=3,
                   command=lambda: self._pick_file(self.var_chrome)).pack(side="left", padx=(4,0))

        self._lbl(p, "👤  Pasta do perfil Chrome")
        self._lbl(p, f"   Ex: {DEFAULT_PROFILE_DIR}", small=True)
        self.var_profile_dir = tk.StringVar(value=str(DEFAULT_PROFILE_DIR))
        dr2 = ttk.Frame(p); dr2.pack(fill="x")
        ttk.Entry(dr2, textvariable=self.var_profile_dir,
                  font=("Segoe UI",10)).pack(side="left", fill="x", expand=True)
        ttk.Button(dr2, text="…", style="Sec.TButton", width=3,
                   command=lambda: self._pick_dir_to(self.var_profile_dir)).pack(side="left", padx=(4,0))

        self._lbl(p, "👤  Nome do perfil (ex: Default, Profile 1)")
        self.var_profile_name = tk.StringVar(value="Default")
        self._entry(p, self.var_profile_name, "Default")

        info = tk.Frame(p, bg=c["PANEL"], pady=10, padx=12)
        info.pack(fill="x", pady=(10,0))
        tk.Label(info,
                 text="Cria um perfil Chrome separado, faz login no SIC OPTO e aponta para essa pasta.\n"
                      "A configuração é guardada ao clicar Guardar ou ao fechar.\n\n"
                      "Fecha qualquer Chrome aberto na porta 9222 antes de iniciar.",
                 bg=c["PANEL"], fg=c["MUTED"], font=("Segoe UI", 9),
                 justify="left").pack(anchor="w")

        tk.Frame(p, bg=c["PANEL"], height=1).pack(fill="x", pady=14)

        ttk.Button(p, text="💾  Guardar configuração", command=self._save_cfg).pack(anchor="w")

        tk.Frame(p, bg=c["PANEL"], height=1).pack(fill="x", pady=14)

        tk.Label(p, text="Secrets e .wvd",
                 bg=c["BG"], fg=c["FG"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,8))

        self.var_wvd_status = tk.StringVar(value=".wvd: a verificar...")
        self.lbl_wvd_status = tk.Label(
            p, textvariable=self.var_wvd_status, bg=c["BG"], fg=c["MUTED"],
            font=("Segoe UI", 9, "bold"))
        self.lbl_wvd_status.pack(anchor="w", pady=(0,6))

        secret_buttons = ttk.Frame(p); secret_buttons.pack(fill="x", pady=(0,4))
        ttk.Button(secret_buttons, text="Abrir pasta secrets", style="Sec.TButton",
                   command=self._open_secrets_dir).pack(side="left")
        ttk.Button(secret_buttons, text="Atualizar estado .wvd", style="Sec.TButton",
                   command=self._refresh_wvd_status).pack(side="left", padx=(6,0))

        tk.Frame(p, bg=c["PANEL"], height=1).pack(fill="x", pady=14)

        tk.Label(p, text="Gerar ficheiro .wvd",
                 bg=c["BG"], fg=c["FG"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,8))

        self._lbl(p, "🔑  Private key")
        self.var_wvd_private_key = tk.StringVar(value=str(SECRETS_DIR / "private_key.pem"))
        key_row = ttk.Frame(p); key_row.pack(fill="x")
        ttk.Entry(key_row, textvariable=self.var_wvd_private_key,
                  font=("Segoe UI",10)).pack(side="left", fill="x", expand=True)
        ttk.Button(key_row, text="…", style="Sec.TButton", width=3,
                   command=lambda: self._pick_file(
                       self.var_wvd_private_key,
                       [("Private key", "*.pem"), ("Todos", "*")]
                   )).pack(side="left", padx=(4,0))

        self._lbl(p, "🪪  Client ID")
        self.var_wvd_client_id = tk.StringVar(value=str(SECRETS_DIR / "client_id.bin"))
        client_row = ttk.Frame(p); client_row.pack(fill="x")
        ttk.Entry(client_row, textvariable=self.var_wvd_client_id,
                  font=("Segoe UI",10)).pack(side="left", fill="x", expand=True)
        ttk.Button(client_row, text="…", style="Sec.TButton", width=3,
                   command=lambda: self._pick_file(
                       self.var_wvd_client_id,
                       [("Client ID", "*.bin"), ("Todos", "*")]
                   )).pack(side="left", padx=(4,0))

        self._lbl(p, "📁  Pasta de saída")
        self.var_wvd_output_dir = tk.StringVar(value=str(SECRETS_DIR))
        out_row = ttk.Frame(p); out_row.pack(fill="x")
        ttk.Entry(out_row, textvariable=self.var_wvd_output_dir,
                  font=("Segoe UI",10)).pack(side="left", fill="x", expand=True)
        ttk.Button(out_row, text="…", style="Sec.TButton", width=3,
                   command=lambda: self._pick_dir_to(self.var_wvd_output_dir)).pack(side="left", padx=(4,0))

        self.btn_generate_wvd = ttk.Button(
            p, text="Gerar .wvd", style="Sec.TButton", command=self._generate_wvd)
        self.btn_generate_wvd.pack(anchor="w", pady=(10,0))

        self._refresh_wvd_status()

    def _tab_log(self, p):
        c = self._c
        self.log_box = scrolledtext.ScrolledText(
            p, bg=c["SURFACE"], fg=c["FG"], font=("Consolas", 9),
            relief="flat", insertbackground=c["ACC"], state="disabled", wrap="word")
        self.log_box.pack(fill="both", expand=True)
        self.log_box.tag_configure("ok",   foreground=c["OK"])
        self.log_box.tag_configure("warn", foreground=c["WARN"])
        self.log_box.tag_configure("err",  foreground=c["ERR"])
        self.log_box.tag_configure("step", foreground=c["ACC"])

    # ── load/save config ──────────────────────────────────────────────────────
    def _load_config_to_ui(self):
        cfg = self._cfg
        if cfg.get("chrome_exe"):   self.var_chrome.set(cfg["chrome_exe"])
        if cfg.get("profile_dir"):  self.var_profile_dir.set(cfg["profile_dir"])
        if cfg.get("profile_name"): self.var_profile_name.set(cfg["profile_name"])
        if cfg.get("output_dir"):   self.var_dir.set(cfg["output_dir"])
        if cfg.get("quality"):      self.var_quality.set(cfg["quality"])

    def _save_cfg(self):
        save_config({
            "chrome_exe":   self._clean_entry_value(self.var_chrome.get()),
            "profile_dir":  self._clean_entry_value(self.var_profile_dir.get()),
            "profile_name": self._clean_entry_value(self.var_profile_name.get()),
            "output_dir":   self._clean_entry_value(self.var_dir.get()),
            "quality":      self.var_quality.get(),
        })
        messagebox.showinfo("Config", "✅ Configuração guardada!")

    # ── acções ────────────────────────────────────────────────────────────────
    def _autofill_name(self, event=None):
        url = self._clean_entry_value(self.var_page.get())
        current_name = self._clean_entry_value(self.var_name.get())
        if url and not current_name:
            name = name_from_url(url)
            if name:
                self.var_name.set(name)
                if hasattr(self, "name_entry"):
                    self.name_entry.config(foreground=self._c["FG"])

    def _log(self, text):
        def _i():
            self.log_box.config(state="normal")
            tag = ("ok" if "✅" in text else "warn" if "⚠" in text else
                   "err" if "❌" in text else "step" if "📌" in text else "")
            self.log_box.insert("end", text, tag)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _i)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0","end")
        self.log_box.config(state="disabled")

    def _set_progress(self, pct, label=""):
        self.after(0, lambda: (self.progress_var.set(pct), self.status_var.set(label)))

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.var_dir.get())
        if d: self.var_dir.set(d)

    def _pick_dir_to(self, var):
        d = filedialog.askdirectory()
        if d: var.set(d)

    def _pick_file(self, var, filetypes=None):
        f = filedialog.askopenfilename(filetypes=filetypes or [("Executável","*.exe"),("Todos","*")])
        if f: var.set(f)

    def _refresh_wvd_status(self):
        wvds = find_wvd_files()
        if wvds:
            wvd = wvds[0]
            text = f"✅ .wvd encontrado: {wvd.name}"
            fg = self._c["OK"]
        else:
            text = "⚠ .wvd não encontrado em secrets/"
            fg = self._c["WARN"]
        self.var_wvd_status.set(text)
        self.lbl_wvd_status.config(fg=fg)

    def _open_secrets_dir(self):
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(SECRETS_DIR)])
            elif os.name == "nt":
                os.startfile(str(SECRETS_DIR))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(SECRETS_DIR)])
            self._log(f"📁 Pasta secrets aberta: {SECRETS_DIR}\n")
        except Exception as e:
            self._log(f"❌ Não foi possível abrir secrets/: {e}\n")
            messagebox.showerror("Secrets", f"Não foi possível abrir a pasta:\n{SECRETS_DIR}")

    def _generate_wvd(self):
        private_key = project_path(self._clean_entry_value(self.var_wvd_private_key.get()))
        client_id = project_path(self._clean_entry_value(self.var_wvd_client_id.get()))
        output_dir = project_path(self._clean_entry_value(self.var_wvd_output_dir.get())) or SECRETS_DIR

        if not private_key or not private_key.exists():
            messagebox.showerror("Gerar .wvd", "Seleciona um ficheiro private_key.pem válido.")
            return
        if not client_id or not client_id.exists():
            messagebox.showerror("Gerar .wvd", "Seleciona um ficheiro client_id.bin válido.")
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        before = {p.resolve() for p in output_dir.glob("*.wvd")}
        pywidevine_bin = resolve_tool("pywidevine")
        if pywidevine_bin:
            cmd = [
                pywidevine_bin,
                "create-device",
                "-k", str(private_key),
                "-c", str(client_id),
                "-t", "ANDROID",
                "-l", "3",
                "-o", str(output_dir),
            ]
        else:
            cmd = [
                sys.executable,
                "-c", "from pywidevine.main import main; main()",
                "create-device",
                "-k", str(private_key),
                "-c", str(client_id),
                "-t", "ANDROID",
                "-l", "3",
                "-o", str(output_dir),
            ]

        self.btn_generate_wvd.config(state="disabled")
        self._set_progress(0, "A gerar .wvd...")
        self._log("\n🔑 Gerar .wvd\n")
        self._log(f"   Private key: {private_key}\n")
        self._log(f"   Client ID: {client_id}\n")
        self._log(f"   Saída: {output_dir}\n")

        def worker():
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(SCRIPT_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                for line in proc.stdout or []:
                    self._log(f"   {line}")
                code = proc.wait()
                after = {p.resolve() for p in output_dir.glob("*.wvd")}
                created = sorted(after - before)
                if code == 0:
                    if created:
                        self._log(f"✅ .wvd gerado: {created[-1]}\n")
                    else:
                        wvds = sorted(output_dir.glob("*.wvd"), key=lambda p: p.stat().st_mtime)
                        if wvds:
                            self._log(f"✅ .wvd disponível: {wvds[-1]}\n")
                        else:
                            self._log("⚠ Comando terminou, mas não encontrei nenhum .wvd na pasta de saída.\n")
                    self.after(0, self._refresh_wvd_status)
                    self.after(0, lambda: messagebox.showinfo("Gerar .wvd", "Processo concluído. Confirma o Log."))
                else:
                    self._log(f"❌ pywidevine terminou com erro ({code}).\n")
                    self.after(0, self._refresh_wvd_status)
                    self.after(0, lambda: messagebox.showerror("Gerar .wvd", "Falhou. Consulta o Log."))
            except Exception as e:
                msg = str(e)
                self._log(f"❌ Erro ao gerar .wvd: {e}\n")
                self.after(0, self._refresh_wvd_status)
                self.after(0, lambda: messagebox.showerror("Gerar .wvd", f"Erro: {msg}"))
            finally:
                self.after(0, lambda: (
                    self.btn_generate_wvd.config(state="normal"),
                    self._set_progress(0, "Pronto.")
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _check_tools(self):
        self._log("\n🔧 Verificar:\n")
        for name, var in self.tool_vars.items():
            found = resolve_tool(self._clean_entry_value(var.get()) or name)
            self._log(f"  {'✅' if found else '❌'} {name}: {found or 'não encontrado'}\n")
        for pkg, imp in [("pywidevine","pywidevine"),("selenium","selenium"),
                         ("websocket-client","websocket")]:
            try:
                __import__(imp); self._log(f"  ✅ {pkg}\n")
            except ImportError:
                self._log(f"  ⚠ {pkg}: pip install {pkg}\n")
        chrome = self._clean_entry_value(self.var_chrome.get())
        self._log(f"  {'✅' if Path(chrome).exists() else '❌'} Chrome: {chrome}\n")
        wvds = find_wvd_files()
        self._log(f"  {'✅' if wvds else '⚠'} .wvd: {wvds[0] if wvds else 'não encontrado'}\n")
        self._refresh_wvd_status()

    def _get_common_args(self):
        for name, var in self.tool_vars.items():
            v = self._clean_entry_value(var.get())
            if v: TOOLS[name] = v
        def clean_placeholder(v):
            v = self._clean_entry_value(v)
            placeholders = {
                "https://opto.sic.pt/vod/nome-do-episodio/uuid",
                "ex: nome-do-episodio",
                "https://manifest.mpd",
                "https://...manifest.mpd",
                "https://.../license?...",
            }
            return "" if v in placeholders else v

        return {
            "mpd_url":      clean_placeholder(self.var_mpd.get()),
            "license_url":  clean_placeholder(self.var_license.get()),
            "pssh_manual":  self._get_text(self.txt_pssh),
            "keys_manual":  self._get_text(self.txt_keys),
            "output_dir":   self._clean_entry_value(self.var_dir.get()) or DEFAULT_OUTPUT_DIR,
            "chrome_exe":   self._clean_entry_value(self.var_chrome.get()),
            "profile_dir":  self._clean_entry_value(self.var_profile_dir.get()),
            "profile_name": self._clean_entry_value(self.var_profile_name.get()),
            "quality":      self.var_quality.get(),
        }

    def _disable_buttons(self):
        self.btn_start.config(state="disabled")
        self.btn_series.config(state="disabled")

    def _enable_buttons(self):
        self.btn_start.config(state="normal")
        self.btn_series.config(state="normal")
        self.btn_cancel_series.config(state="disabled")
        self.btn_cancel_download.config(state="disabled")
        self._download_cancel = None

    def _begin_download(self):
        self._download_cancel = threading.Event()
        self.btn_start.config(state="disabled")
        self.btn_series.config(state="disabled")
        self.btn_cancel_series.config(state="disabled")
        self.btn_cancel_download.config(state="normal")
        return self._download_cancel

    def _cancel_download(self):
        if self._download_cancel and not self._download_cancel.is_set():
            self._download_cancel.set()
            self.btn_cancel_download.config(state="disabled")
            self._set_progress(0, "A cancelar download...")
            self._log("⏹ Pedido de cancelamento enviado. A parar processos...\n")

    def _begin_series_scrape(self):
        self._series_scrape_cancel = threading.Event()
        self.btn_start.config(state="disabled")
        self.btn_series.config(state="disabled")
        self.btn_cancel_series.config(state="normal")
        return self._series_scrape_cancel

    def _finish_series_scrape(self):
        self._series_scrape_cancel = None
        self._enable_buttons()

    def _cancel_series_scrape(self):
        if self._series_scrape_cancel and not self._series_scrape_cancel.is_set():
            self._series_scrape_cancel.set()
            self.btn_cancel_series.config(state="disabled")
            self._set_progress(0, "A cancelar scrape...")
            self._log("⏹ Pedido de cancelamento enviado. A aguardar paragem segura...\n")

    def _start(self):
        args = self._get_common_args()
        page_url = self._clean_entry_value(self.var_page.get())
        if not page_url and not args["mpd_url"]:
            messagebox.showerror("Erro", "Insere a URL da página ou o MPD."); return

        # Detectar URL de série e sugerir botão correto
        if page_url and is_series_url(page_url) and not args["mpd_url"]:
            if messagebox.askyesno("URL de Série",
                    "Este URL parece ser de uma série.\n\n"
                    "Usa o botão 📺 SÉRIE para listar e selecionar episódios.\n\n"
                    "Continuar mesmo assim com DOWNLOAD?"):
                pass  # o utilizador confirmou
            else:
                return

        # Auto-preencher nome se ainda vazio
        output_name = self._clean_entry_value(self.var_name.get())
        if not output_name:
            output_name = name_from_url(page_url) or \
                          f"SIC_OPTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Guardar config automaticamente
        save_config({"chrome_exe": args["chrome_exe"],
                     "profile_dir": args["profile_dir"],
                     "profile_name": args["profile_name"],
                     "output_dir": args["output_dir"]})

        cancel_event = self._begin_download()
        self._clear_log()
        self._log(f"🚀 {datetime.now().strftime('%H:%M:%S')} — {output_name}\n")

        def done_fn(success, path=None):
            def _f():
                self._enable_buttons()
                if cancel_event.is_set():
                    messagebox.showinfo("Cancelado", "⏹ Download cancelado.")
                elif success:
                    messagebox.showinfo("Concluído", f"✅ Download concluído!\n{path}")
                else:
                    messagebox.showerror("Erro", "Processo falhou. Consulta o Log.")
            self.after(0, _f)

        threading.Thread(
            target=download_and_decrypt,
            kwargs=dict(page_url=page_url, **args,
                        output_name=output_name,
                        log_fn=self._log, progress_fn=self._set_progress,
                        done_fn=done_fn,
                        cancel_event=cancel_event),
            daemon=True
        ).start()

    def _start_series(self):
        page_url = self._clean_entry_value(self.var_page.get())
        if not page_url:
            messagebox.showerror("Erro", "Insere o URL da série."); return

        args = self._get_common_args()
        save_config({"chrome_exe": args["chrome_exe"],
                     "profile_dir": args["profile_dir"],
                     "profile_name": args["profile_name"],
                     "output_dir": args["output_dir"]})

        cancel_event = self._begin_series_scrape()
        self._clear_log()
        self._log(f"📺 A carregar episódios de: {page_url}\n")

        def fetch_and_show():
            eps_by_season = get_series_episodes(
                page_url, self._log,
                chrome_exe=args["chrome_exe"],
                profile_dir=args["profile_dir"],
                profile_name=args["profile_name"],
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                self._log("⏹ Scrape de série abortado pelo utilizador.\n")
                self.after(0, self._finish_series_scrape)
                return
            if not eps_by_season:
                self._log("❌ Sem episódios encontrados.\n")
                self.after(0, self._finish_series_scrape)
                return

            def show_dialog():
                self.btn_cancel_series.config(state="disabled")
                dlg = SeasonSelectDialog(self, eps_by_season, self._c)
                self.wait_window(dlg)
                selected = dlg.result
                if not selected:
                    self._log("ℹ️  Nenhum episódio selecionado.\n")
                    self._finish_series_scrape()
                    return

                self._log(f"✅ {len(selected)} episódios selecionados.\n")
                self._series_scrape_cancel = None
                output_dir = args["output_dir"]
                # Subpasta com nome da série
                series_name = name_from_url(page_url) or "serie"
                output_dir  = os.path.join(output_dir, series_name)

                def done_fn(success, path=None):
                    self.after(0, lambda: (
                        self._enable_buttons(),
                        messagebox.showinfo("Concluído",
                            f"✅ Série concluída!\n{output_dir}") if success else
                        messagebox.showerror("Erro", "Alguns episódios falharam. Consulta o Log.")
                    ))

                series_args = {k: v for k, v in args.items() if k != "output_dir"}
                threading.Thread(
                    target=download_and_decrypt,
                    kwargs=dict(page_url=page_url, **series_args,
                                output_name="",
                                output_dir=output_dir,
                                log_fn=self._log, progress_fn=self._set_progress,
                                done_fn=done_fn, batch_episodes=selected,
                                cancel_event=threading.Event()),
                    daemon=True
                ).start()

            self.after(0, show_dialog)

        threading.Thread(target=fetch_and_show, daemon=True).start()

# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    App().mainloop()

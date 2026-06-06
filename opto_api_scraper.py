#!/usr/bin/env python3
"""
opto_api_scraper.py — Scraper de séries OPTO via API REST
==========================================================
Usa directamente a API interna do OPTO em vez de um browser.
Sem Playwright, sem scroll, sem cliques — apenas chamadas HTTP.

Velocidade típica: < 2 segundos por série independentemente do número
de episódios (uma chamada para metadados + uma chamada /list para a série).

Requisitos:
    pip install requests

Uso:
    python3 opto_api_scraper.py "https://opto.sic.pt/series/lua-vermelha/ab4750d7-229f-4c04-873e-754861bfd216"
    python3 opto_api_scraper.py "URL" --json

Notas:
    - Não requer autenticação para metadados (title, uuid, etc.).
    - O URL do episódio é construído a partir do slug da série +
      número de temporada/episódio + UUID do episódio.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERRO: instala o requests primeiro:  pip install requests", file=sys.stderr)
    sys.exit(1)

BASE_API   = "https://opto.sic.pt/api/v1/content/item"
BASE_SITE  = "https://opto.sic.pt"

HEADERS = {
    "Accept":          "application/json",
    "Accept-Language": "pt-PT,pt;q=0.9",
    "User-Agent":      (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://opto.sic.pt/",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg):
    print(msg, flush=True)


def parse_series_identity(series_url: str) -> dict:
    """Extrai slug e UUID a partir da URL da série."""
    parts = [p for p in series_url.rstrip("/").split("/") if p]
    uuid_pat = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)
    for i, part in enumerate(reversed(parts)):
        idx = len(parts) - 1 - i
        if uuid_pat.match(part):
            return {
                "uuid": part,
                "slug": parts[idx - 1] if idx > 0 else "",
            }
    return {"uuid": "", "slug": ""}


def build_episode_url(series_slug: str, season_num: int, ep_num: int, ep_uuid: str) -> str:
    """
    Constrói o URL canónico de um episódio.
    Formato: https://opto.sic.pt/vod/{series_slug}-t{season}-e{episode}/{uuid}
    Exemplo: https://opto.sic.pt/vod/lua-vermelha-t1-e1/81ad7b26-...
    """
    ep_slug = f"{series_slug}-t{season_num}-e{ep_num}"
    return f"{BASE_SITE}/vod/{ep_slug}/{ep_uuid}"


def api_get(url: str, params: dict = None, retries: int = 3) -> dict | None:
    """GET com retry e tratamento de erros."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            log(f"   HTTP {r.status_code} em {url}")
            if r.status_code in (401, 403, 404):
                return None  # não vale a pena tentar de novo
        except requests.RequestException as e:
            log(f"   Erro de rede (tentativa {attempt}/{retries}): {e}")
        if attempt < retries:
            time.sleep(1.5 * attempt)
    return None


def first_present(data: dict, *keys, default=None):
    """Devolve o primeiro valor não vazio encontrado em data."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def as_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

def fetch_series_info(series_uuid: str) -> dict | None:
    """Devolve metadados da série, incluindo a lista de temporadas."""
    url = f"{BASE_API}/{series_uuid}"
    data = api_get(url)
    if not data:
        log(f"ERRO: não foi possível obter informação da série ({series_uuid})")
    return data


def episode_from_item(item: dict, series_slug: str, season_num: int, season_name: str = "") -> dict:
    """Normaliza um episódio vindo da API para o formato usado pela app."""
    ep_uuid = first_present(item, "id", "uuid", default="")
    ep_num = as_int(
        first_present(item, "episode_number", "episode_order", "episode", default=0)
    )
    title = str(first_present(item, "title", "name", default="")).strip()
    desc = str(first_present(item, "short_description", "description", default="")).strip()
    duration = as_int(first_present(item, "duration", "duration_seconds", default=0))
    ep_url = build_episode_url(series_slug, season_num, ep_num, ep_uuid)

    return {
        "title":       title,
        "season":      season_num,
        "season_name": season_name or f"T{season_num}",
        "episode":     ep_num,
        "url":         ep_url,
        "uuid":        ep_uuid,
        "duration":    duration,
        "description": desc,
    }


def iter_episode_items(data: dict):
    """
    Itera episódios nas estruturas conhecidas da API OPTO.

    Estrutura atual de /api/v1/content/item/{uuid}/list:
        {"seasons": [{"season": 1, "item": [{episodio}, ...]}, ...]}

    Mantém fallback para respostas antigas/variantes com item/items/data.
    """
    seasons = data.get("seasons")
    if isinstance(seasons, list):
        for season in seasons:
            if not isinstance(season, dict):
                continue
            season_num = as_int(
                first_present(season, "season", "season_number", "number", default=1),
                1,
            )
            season_name = str(
                first_present(season, "name", "title", default=f"T{season_num}")
            ).strip() or f"T{season_num}"
            items = season.get("item") or season.get("items") or season.get("episodes") or []
            if isinstance(items, dict):
                items = items.get("items") or items.get("data") or []
            for item in items:
                if isinstance(item, dict):
                    yield season_num, season_name, item
        return

    items = data.get("item") or data.get("items") or data.get("data") or []
    if isinstance(items, dict):
        items = items.get("items") or items.get("data") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        season_value = first_present(
            item,
            "season_number",
            "season",
            "season_order",
            default=1,
        )
        if isinstance(season_value, dict):
            season_num = as_int(
                first_present(season_value, "season", "number", "order", default=1),
                1,
            )
            season_name = str(
                first_present(season_value, "name", "title", default=f"T{season_num}")
            ).strip() or f"T{season_num}"
        else:
            season_num = as_int(season_value, 1)
            season_name = f"T{season_num}"
        yield season_num, season_name, item


def fetch_series_episodes(series_uuid: str, series_slug: str) -> list[dict]:
    """
    Devolve todos os episódios da série numa única chamada /list.
    Cada episódio tem: title, season, episode, url, uuid, duration, description.
    """
    url = f"{BASE_API}/{series_uuid}/list"
    data = api_get(url)
    if not data:
        log("   Erro ao obter episódios")
        return []

    episodes = [
        episode_from_item(item, series_slug, season_num, season_name)
        for season_num, season_name, item in iter_episode_items(data)
    ]
    episodes.sort(
        key=lambda ep: (
            ep.get("season") or 0,
            ep.get("episode") or 0,
            ep.get("title") or "",
        )
    )
    return episodes


def scrape_series(series_url: str) -> dict:
    """
    Ponto de entrada principal.
    Devolve um dict com episodes_by_season, season_count, episode_count.
    """
    identity = parse_series_identity(series_url)
    series_uuid = identity["uuid"]
    series_slug = identity["slug"]

    if not series_uuid:
        raise ValueError(f"Não foi possível extrair UUID da URL: {series_url}")

    log(f"Série: {series_slug} ({series_uuid})")

    # 1. Obter metadados da série. As temporadas aqui são só informativas;
    #    os episódios vêm da chamada /list da série.
    series_info = fetch_series_info(series_uuid)
    if not series_info:
        raise RuntimeError("Falha ao obter informação da série.")

    series_title = series_info.get("title", series_slug)
    seasons      = series_info.get("seasons", []) or []

    log(f"Título: {series_title}")
    if seasons:
        names = [s.get("name", f"T{s.get('season', '?')}") for s in seasons]
        log(f"{len(seasons)} temporada(s) nos metadados: {', '.join(names)}")

    result = {
        "series_url":        series_url,
        "series_slug":       series_slug,
        "series_uuid":       series_uuid,
        "series_title":      series_title,
        "episodes_by_season": {},
    }

    # 2. Obter episódios via API.
    log("\nA obter episódios via /list...")
    episodes = fetch_series_episodes(series_uuid, series_slug)
    log(f"   {len(episodes)} episódio(s) obtidos.")

    for ep in episodes:
        season_key = ep.get("season_name") or f"T{ep.get('season') or 1}"
        result["episodes_by_season"].setdefault(season_key, []).append(
            {k: v for k, v in ep.items() if k != "description"}
        )

    total = sum(len(v) for v in result["episodes_by_season"].values())
    result["season_count"]   = len(result["episodes_by_season"])
    result["episode_count"]  = total
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scraper de séries OPTO via API REST — sem browser.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 opto_api_scraper.py "https://opto.sic.pt/series/lua-vermelha/ab4750d7-..."
  python3 opto_api_scraper.py "URL" --json
  python3 opto_api_scraper.py "URL" --output episodios.json
""",
    )
    parser.add_argument("url", help="URL da série OPTO.")
    parser.add_argument(
        "--json", action="store_true",
        help="Imprime resultado completo em JSON.",
    )
    parser.add_argument(
        "--output", metavar="FICHEIRO",
        help="Guarda o resultado JSON num ficheiro.",
    )
    args = parser.parse_args()

    t0   = time.time()
    data = scrape_series(args.url)
    elapsed = round(time.time() - t0, 2)

    log(f"\n✅ {data['episode_count']} episódios em {data['season_count']} temporada(s) — {elapsed}s")

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    if args.output:
        Path(args.output).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log(f"Guardado em: {args.output}")

    if not args.json and not args.output:
        for season_key, episodes in data["episodes_by_season"].items():
            print(f"\n{season_key} ({len(episodes)} episódios)")
            for ep in episodes:
                dur = f"{ep['duration']//60}m{ep['duration']%60:02d}s" if ep.get("duration") else ""
                print(f"  E{ep['episode']:02d}  {ep['title']:<40}  {dur:<8}  {ep['url']}")

    if not data["episode_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)

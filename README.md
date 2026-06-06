# Opto Downloader

Ferramenta local para analisar, reproduzir temporariamente e descarregar episódios SIC OPTO usando APIs HTTP. Não usa Selenium, Playwright nem Chrome.

Uso pessoal apenas. Requer acesso legítimo ao conteúdo e um ficheiro `.wvd` próprio para obter keys Widevine.

## Funcionalidades

- Interface Qt moderna em `opto_app.py`.
- Scrape de séries via API OPTO.
- Seleção de episódios por temporada, incluindo nomes reais como `Extras T2`.
- Resolução de MPD, license URL assinada e PSSH via API/Kaltura `multirequest`.
- Download final em MP4 com `yt-dlp`, `pywidevine`, `mp4decrypt` e `ffmpeg`.
- Página de downloads com fila, progresso, agrupamento por série/temporada e cancelamento.
- Player integrado que prepara um MP4 temporário para reprodução sem guardar na pasta final.
- CLI de série em `opto_api_scraper.py`.
- CLI de episódio/download em `opto_api_media_resolver.py`.

## Instalação Local

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 instalar_dependencias.py
```

Ou instala manualmente:

```bash
pip install PySide6 requests pywidevine yt-dlp
```

Também precisas de:

- `ffmpeg` e `ffprobe`
- `mp4decrypt` do Bento4
- um ficheiro `.wvd` em `secrets/`, `~/.wvd/` ou numa pasta antiga da app

## Interface

```bash
python3 opto_app.py
```

Fluxos principais:

- **Episódio**: cola URL/UUID, clica em `Analisar`, escolhe qualidade e faz download ou play temporário.
- **Série**: cola URL da série, carrega episódios, seleciona temporadas/episódios e faz download em lote ou play em playlist.
- **Downloads**: acompanha fila, progresso, cancelamentos e ficheiros concluídos.
- **Player**: reproduz temporários gerados pela app e mantém cache do episódio anterior/seguinte.
- **Preferências**: idioma, pasta predefinida e qualidade predefinida.
- **Estado**: verificação de ferramentas e geração de `.wvd`.

## CLI

Listar uma série:

```bash
python3 opto_api_scraper.py "https://opto.sic.pt/series/a-heranca/UUID" --json
```

Resolver episódio:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID_DO_EPISODIO" --json
```

Testar keys:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID_DO_EPISODIO" --test-keys --json
```

Download:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID_DO_EPISODIO" --download --quality 720
```

## Builds Locais

Os artefactos são criados em `release-dist/`.

ZIPs por plataforma:

```bash
scripts/build_release_zips.sh vX.Y.Z
```

macOS DMG:

```bash
scripts/build_macos_dmg.sh vX.Y.Z
```

Windows EXE:

```powershell
scripts\build_windows_exe.ps1 vX.Y.Z
```

Linux AppImage:

```bash
scripts/build_linux_appimage.sh vX.Y.Z
```

## Estrutura

- `opto_app.py`: interface Qt.
- `opto_api_scraper.py`: scrape de séries via API.
- `opto_api_media_resolver.py`: resolução de episódio, keys e download MP4.
- `assets/`: ícones e imagens da app.
- `instalar_dependencias.py`: instalador local de dependências.
- `platform/`: scripts de instalação/arranque por plataforma.
- `scripts/`: scripts de build/release.

## Segurança

Não publiques `.wvd`, keys, ficheiros descarregados, tokens, secrets ou dados de sessão.

# Opto Downloader

Aplicação desktop para analisar, reproduzir temporariamente e descarregar episódios da **OPTO/SIC** com interface gráfica moderna.

> Uso pessoal apenas. Requer acesso legítimo ao conteúdo e um ficheiro `.wvd` próprio para desencriptação Widevine.

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Windows%20%7C%20macOS%20%7C%20Linux-555?style=flat-square)](../../releases)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-f59e0b?style=flat-square)](https://buymeacoffee.com/miguelmaster12)

## Estado dos Instaladores

| Plataforma | Estado |
|---|---|
| Windows `.exe` | Testado e funcional |
| macOS `.dmg` | Testado e funcional |
| Linux `.AppImage` | Gerado, mas ainda não testado. Pode não funcionar em algumas distros |
| ZIPs | Alternativa manual para todas as plataformas |

## Download e Instalação

Vai a **[Releases](../../releases)** e descarrega o ficheiro para o teu sistema.

### Windows

Descarrega e abre:

```text
opto-downloader-*-windows-setup.exe
```

O instalador inclui/prepara automaticamente as dependências necessárias.

### macOS

Descarrega:

```text
opto-downloader-*-macos.dmg
```

Abre o DMG e arrasta a app para `Applications`.

Se o macOS bloquear a app por programador não verificado:

```bash
xattr -dr com.apple.quarantine "/Applications/OPTO Downloader.app"
open "/Applications/OPTO Downloader.app"
```

### Linux

Descarrega:

```text
opto-downloader-*-linux.AppImage
```

Depois:

```bash
chmod +x opto-downloader-*.AppImage
./opto-downloader-*.AppImage
```

Nota: o AppImage ainda não foi testado como o `.exe` e o `.dmg`.

## Primeira Configuração

1. Abre a app.
2. Vai a **Estado** e confirma se `ffmpeg`, `ffprobe` e `mp4decrypt` estão disponíveis.
3. Coloca o teu `.wvd` em `secrets/` ou `~/.wvd/`.
4. Em **Preferências**, escolhe pasta de destino, idioma e qualidade padrão.
5. Usa **Episódio** ou **Série** para analisar e descarregar.

## Como Usar

### Episódio

1. Abre a aba **Episódio**.
2. Cola o URL ou UUID.
3. Clica **Analisar**.
4. Escolhe a qualidade.
5. Clica **Download** ou **Play**.

### Série

1. Abre a aba **Série**.
2. Cola o URL da série.
3. Carrega os episódios.
4. Seleciona temporadas/episódios.
5. Clica **Download em lote** ou **Play selecionados**.

### Player

O player gera um ficheiro temporário para reprodução e não guarda o MP4 final na pasta de downloads. Em playlists, prepara episódios vizinhos em cache para navegação mais rápida.

## `.wvd`

O `.wvd` é necessário para conteúdo protegido por Widevine.

A app procura por ordem em:

- `secrets/`
- `~/.wvd/`
- pastas antigas da app

Nunca publiques nem partilhes:

- `.wvd`
- `private_key.pem`
- `client_id.bin`
- keys
- tokens
- downloads

## Instalação Manual por ZIP

Se descarregaste um ZIP em vez do instalador:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 instalar_dependencias.py
python3 opto_app.py
```

No Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python instalar_dependencias.py
python opto_app.py
```

Também podes usar os scripts em `platform/`.

## CLI

Listar episódios de uma série:

```bash
python3 opto_api_scraper.py "https://opto.sic.pt/series/nome/UUID" --json
```

Resolver um episódio:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID" --json
```

Testar keys:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID" --test-keys --json
```

Download via CLI:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID" --download --quality 720
```

## Builds Locais

Os artefactos ficam em `release-dist/`.

```bash
scripts/build_release_zips.sh vX.Y.Z
scripts/build_macos_dmg.sh vX.Y.Z
scripts/build_linux_appimage.sh vX.Y.Z
```

Windows:

```powershell
scripts\build_windows_exe.ps1 vX.Y.Z
```

## Dependências

- `PySide6`
- `requests`
- `yt-dlp`
- `pywidevine`
- `ffmpeg` / `ffprobe`
- `mp4decrypt` / Bento4

## Aviso Legal

Este projeto destina-se a uso pessoal e educativo com conteúdos aos quais tens acesso legítimo. Não redistribuas conteúdo protegido, credenciais, keys ou ficheiros de desencriptação.

O projeto não é afiliado à SIC ou OPTO.

## Apoiar

[Buy Me a Coffee](https://buymeacoffee.com/miguelmaster12)

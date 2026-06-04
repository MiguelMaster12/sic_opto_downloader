# SIC OPTO Downloader

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/Status-Test%20Project-orange)

Ferramenta experimental para testes pessoais com conteúdos SIC OPTO acessíveis pela própria conta do utilizador.

O projeto abre um perfil Chrome dedicado, captura dados técnicos de reprodução (`MPD`, `License URL`, `PSSH`), usa `pywidevine` com um `.wvd` fornecido pelo utilizador, descarrega streams e gera um ficheiro `.mp4`.

## Aviso Legal

Este projeto foi feito para fins de teste, aprendizagem e uso pessoal com conteúdos a que o utilizador tem acesso legítimo.

Não uses esta ferramenta para:

- aceder a conteúdos sem autorização;
- contornar subscrições;
- redistribuir conteúdos protegidos;
- partilhar ficheiros descarregados;
- violar termos de serviço da plataforma.

Cada utilizador é responsável pela forma como usa a ferramenta. O projeto não inclui credenciais, keys, ficheiros `.wvd`, conteúdos, nem qualquer mecanismo para obter acesso indevido.

## Funcionalidades

- Download de episódio único.
- Download de séries com seleção de episódios.
- Cache progressivo de listagens.
- Registo de episódios já descarregados.
- Perfil Chrome dedicado.
- Instalação automática de dependências.
- Chrome iniciado minimizado, com áudio mutado e autoplay bloqueado.
- Suporte a uBlock Origin Lite no perfil debug, quando instalado.

## Requisitos

- Python 3.9 ou superior.
- Google Chrome instalado.
- Conta SIC OPTO com acesso legítimo ao conteúdo.
- Ficheiro `.wvd` pessoal colocado em `secrets/`.

> O `.wvd` não é fornecido, não é gerado e não é descarregado por este projeto.

## Instalação Rápida

### Windows

```powershell
.\install_windows.bat
.\run_windows.bat
```

Se preferires PowerShell diretamente:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
```

### macOS

```bash
chmod +x install_macos.sh run_macos.sh
./install_macos.sh
./run_macos.sh
```

### Linux

```bash
chmod +x install_linux.sh run_linux.sh
./install_linux.sh
./run_linux.sh
```

## Primeiro Uso

1. Coloca o teu `.wvd` em:

```text
secrets/
```

2. Abre a ferramenta com o script `run_...` da tua plataforma.
3. Vai à aba `CONFIG`.
4. Confirma o caminho do Chrome.
5. Mantém o perfil Chrome como `chrome-debug-profile`.
6. Abre o Chrome pela ferramenta e faz login na SIC OPTO.
7. Volta à aba `DOWNLOAD`.

## Uso

### Episódio

Cola uma URL de episódio:

```text
https://opto.sic.pt/vod/nome-do-episodio/uuid
```

Escolhe qualidade/pasta e clica em `INICIAR DOWNLOAD`.

### Série

Cola uma URL de série:

```text
https://opto.sic.pt/series/nome-da-serie/uuid
```

Clica em `SÉRIE`, escolhe os episódios e confirma.

Notas:

- `CANCELAR SCRAPE` aborta a listagem.
- Episódios já descarregados ficam marcados.
- Cache: `state/sic_opto_cache.json`.
- Registo de downloads: `state/sic_opto_downloads.json`.

## Estrutura Do Projeto

```text
.
├── v3.py
├── instalar_dependencias.py
├── install_windows.bat
├── install_windows.ps1
├── install_macos.sh
├── install_linux.sh
├── run_windows.bat
├── run_windows.ps1
├── run_macos.sh
├── run_linux.sh
├── LEIA_ME.md
├── config/
├── state/
├── secrets/
├── vendor/
└── chrome-debug-profile/
```

## O Que Não Deve Ser Partilhado

Estas pastas podem conter dados locais, credenciais, ficheiros sensíveis ou downloads:

```text
.venv/
chrome-debug-profile/
secrets/
state/
vendor/
downloads/
```

O `.gitignore` já ignora estes caminhos.

## Configuração

Ficheiro:

```text
config/sic_opto_config.json
```

Exemplo:

```json
{
  "chrome_exe": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "profile_dir": "chrome-debug-profile",
  "profile_name": "Default",
  "output_dir": "downloads",
  "quality": "best"
}
```

## Dependências

O instalador tenta preparar:

- `yt-dlp`
- `requests`
- `pywidevine`
- `selenium`
- `websocket-client`
- `ffmpeg` / `ffprobe`
- `mp4decrypt`
- uBlock Origin Lite para Chrome debug

## Problemas Comuns

### `.wvd não encontrado`

Coloca o ficheiro `.wvd` em `secrets/`.

### `Chrome não respondeu`

Fecha outros Chromes abertos e confirma o caminho do Chrome na aba `CONFIG`.

### `MPD não obtido`

Confirma que:

- tens login feito no perfil Chrome da ferramenta;
- consegues reproduzir o vídeo no browser;
- a conta tem acesso ao conteúdo.

### `mp4decrypt`, `ffmpeg` ou `ffprobe` em falta

Corre novamente o instalador da tua plataforma.

### Ficheiro `.invalid.mp4`

A validação detetou que o ficheiro final não é reproduzível. Confirma `.wvd`, acesso ao conteúdo e `License URL`.

## Desenvolvimento

Verificar sintaxe:

```bash
python -m py_compile v3.py instalar_dependencias.py
```

Instalação manual:

```bash
python instalar_dependencias.py
```

Abrir manualmente:

```bash
python v3.py
```

## Apoiar

Este projeto é mantido em tempo livre. Se te foi útil, podes apoiar aqui:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-support-yellow?logo=buy-me-a-coffee)](https://www.buymeacoffee.com/miguelmaster12)

> Troca `TEU_USERNAME` pelo teu username do Buy Me a Coffee.

## Contribuições

Este é um projeto de testes. Melhorias são bem-vindas, especialmente em:

- instalação multiplataforma;
- robustez do scraping;
- tratamento de erros;
- documentação;
- limpeza da interface.

Não abras issues ou pull requests com conteúdo protegido, credenciais, `.wvd`, keys ou ficheiros descarregados.

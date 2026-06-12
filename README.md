<div align="center">

<br/>

<img src="assets/app-icon.png" alt="Opto Downloader" width="120" />

# Opto Downloader

### OPTO/SIC desktop downloader & player

<p>
  <a href="../../releases">
    <img src="https://img.shields.io/badge/release-v3.1.16-7A37FC?style=for-the-badge&logo=github&logoColor=white" alt="Release v3.1.16" />
  </a>
  <img src="https://img.shields.io/badge/Windows-tested-111111?style=for-the-badge&logo=windows11&logoColor=white&labelColor=7A37FC" alt="Windows testado" />
  <img src="https://img.shields.io/badge/macOS-tested-111111?style=for-the-badge&logo=apple&logoColor=white&labelColor=7A37FC" alt="macOS testado" />
  <img src="https://img.shields.io/badge/Linux-experimental-111111?style=for-the-badge&logo=linux&logoColor=white&labelColor=7A37FC" alt="Linux experimental" />
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.9%2B-2b2b2b?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/UI-PySide6-2b2b2b?style=flat-square&logo=qt&logoColor=white" alt="PySide6" />
  <img src="https://img.shields.io/badge/Engine-API--only-2b2b2b?style=flat-square" alt="API-only" />
</p>

</div>

---

## Visão Geral

O **Opto Downloader** é uma aplicação desktop local para analisar, reproduzir temporariamente e descarregar conteúdos OPTO aos quais tens acesso legítimo.

Não usa Selenium, Playwright ou Chrome. O fluxo atual é baseado em APIs HTTP, resolução Kaltura e ferramentas locais para download/desencriptação.

> Uso pessoal apenas. A app não inclui contas, tokens, ficheiros `.wvd`, chaves privadas ou conteúdos descarregados.

---

## Releases

Vai a **[Releases](../../releases)** e escolhe o ficheiro adequado ao teu sistema.

| Plataforma | Ficheiro recomendado                  | Estado                                                        |
| ---------- | ------------------------------------- | ------------------------------------------------------------- |
| Windows    | `opto-downloader-*-windows-setup.exe` | Testado e funcional                                           |
| macOS      | `opto-downloader-*-macos.dmg`         | Testado e funcional                                           |
| Linux      | `opto-downloader-*-linux.AppImage`    | Gerado, mas ainda não testado. Pode falhar em algumas distros |
| Manual     | `opto-downloader-*-*.zip`             | Alternativa para instalação manual                            |

### Windows

1. Descarrega o `.exe`.
2. Abre o instalador.
3. Segue o assistente.

O instalador prepara automaticamente a app e as ferramentas necessárias.

### macOS

1. Descarrega o `.dmg`.
2. Abre o DMG.
3. Arrasta a app para `Applications`.

Se o macOS bloquear a app por “programador não verificado”:

```bash
xattr -dr com.apple.quarantine "/Applications/OPTO Downloader.app"
open "/Applications/OPTO Downloader.app"
```

### Linux

O AppImage é disponibilizado, mas ainda não foi validado como o `.exe` e o `.dmg`.

```bash
chmod +x opto-downloader-*.AppImage
./opto-downloader-*.AppImage
```

---

## Primeira Configuração

1. Abre a aplicação.
2. Vai ao separador **Estado**.
3. Confirma que `ffmpeg`, `ffprobe` e `mp4decrypt` estão disponíveis.
4. Coloca o teu ficheiro `.wvd` em `secrets/` ou `~/.wvd/`.
5. Vai a **Preferências** e define:
   - idioma da app;
   - pasta de destino;
   - qualidade padrão;
   - preferências de download.

Depois disso podes usar **Episódio**, **Série**, **Downloads** e **Player**.

---

## Funcionalidades

| Área             | O que faz                                                                                                 |
| ---------------- | --------------------------------------------------------------------------------------------------------- |
| **Episódio**     | Analisa um URL/UUID, resolve MPD/license/PSSH, permite escolher qualidade e descarregar ou reproduzir     |
| **Série**        | Lista episódios por temporada usando a API OPTO, incluindo nomes reais como extras e temporadas especiais |
| **Downloads**    | Mostra fila, progresso, velocidade, estado e agrupamento por série/temporada                              |
| **Player**       | Reproduz um ficheiro temporário sem guardar o MP4 final na pasta de downloads                             |
| **Preferências** | Guarda idioma, pasta padrão, qualidade padrão e outras opções                                             |
| **Estado**       | Verifica ferramentas externas e permite gerar `.wvd` a partir de `private_key.pem` e `client_id.bin`      |
| **CLI**          | Scripts para uso avançado sem interface gráfica                                                           |

---

## Como Usar

### Descarregar um episódio

1. Vai a **Episódio**.
2. Cola o URL ou UUID do episódio.
3. Clica em **Analisar**.
4. Escolhe a qualidade.
5. Clica em **Download**.

Também podes clicar em **Play** para preparar uma reprodução temporária sem guardar o MP4 final.

### Descarregar uma série

1. Vai a **Série**.
2. Cola o URL da série.
3. Clica em **Carregar episódios**.
4. Seleciona temporadas ou episódios específicos.
5. Clica em **Download em lote**.

A app organiza a lista por série e temporada e mantém a fila visível no separador **Downloads**.

### Usar o player

O player prepara um MP4 temporário e reproduz dentro da app.

- Não guarda o ficheiro final na pasta de downloads.
- Em séries/playlists, prepara episódios vizinhos em cache para navegação mais rápida.
- O ficheiro temporário é limpo pela app.

---

## Instalação Manual por ZIP

Usa esta opção apenas se descarregaste um ZIP em vez do instalador.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 instalar_dependencias.py
python3 opto_app.py
```

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python instalar_dependencias.py
python opto_app.py
```

Também existem scripts auxiliares em `platform/`:

```text
platform/windows/
platform/macos/
platform/linux/
```

---

## CLI

Listar episódios de uma série:

```bash
python3 opto_api_scraper.py "https://opto.sic.pt/series/nome/UUID" --json
```

Resolver um episódio:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID" --json
```

Testar keys Widevine:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID" --test-keys --json
```

Descarregar via CLI:

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID" --download --quality 720
```

---

## Builds Locais

Os artefactos são gerados em `release-dist/`.

```bash
scripts/build_release_zips.sh vX.Y.Z
scripts/build_macos_dmg.sh vX.Y.Z
scripts/build_linux_appimage.sh vX.Y.Z
```

Windows:

```powershell
scripts\build_windows_exe.ps1 vX.Y.Z
```

---

## Dependências

| Dependência          | Função                     |
| -------------------- | -------------------------- |
| `PySide6`            | Interface gráfica e player |
| `requests`           | Chamadas HTTP/API          |
| `yt-dlp`             | Download dos streams       |
| `pywidevine`         | Licenças Widevine          |
| `ffmpeg` / `ffprobe` | Muxing e validação         |
| `mp4decrypt`         | Desencriptação MP4         |

---

## Problemas Comuns

### A app não encontra o `.wvd`

Coloca o ficheiro em `secrets/` ou `~/.wvd/` e reinicia a app.

### O macOS bloqueia a app

Executa:

```bash
xattr -dr com.apple.quarantine "/Applications/OPTO Downloader.app"
```

### Falta `ffmpeg`, `ffprobe` ou `mp4decrypt`

Vai a **Estado** e usa a verificação de ferramentas. Se instalaste por ZIP, volta a correr:

```bash
python3 instalar_dependencias.py
```

### O AppImage não abre

O AppImage ainda está em estado experimental. Usa o ZIP manual no Linux se o AppImage não funcionar.

---

## Segurança e Aviso Legal

Este projeto destina-se a uso pessoal e educativo com conteúdos aos quais tens acesso legítimo.

Não uses a ferramenta para redistribuir conteúdo protegido, contornar acesso indevido ou partilhar materiais privados de desencriptação.

O projeto não é afiliado à SIC ou OPTO.

---

<div align="center">

<br/>

<sub>Se este projeto te poupou tempo, podes apoiar a manutenção.</sub>

<br/>
<br/>

<p>
  <a href="https://buymeacoffee.com/miguelmaster12">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" width="190" />
  </a>
</p>

<br/>

</div>

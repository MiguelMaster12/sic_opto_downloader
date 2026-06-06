<div align="center">

<br/>

```
  ██████╗ ██████╗ ████████╗ ██████╗
 ██╔═══██╗██╔══██╗╚══██╔══╝██╔═══██╗
 ██║   ██║██████╔╝   ██║   ██║   ██║
 ██║   ██║██╔═══╝    ██║   ██║   ██║
 ╚██████╔╝██║        ██║   ╚██████╔╝
  ╚═════╝ ╚═╝        ╚═╝    ╚═════╝
         D O W N L O A D E R
```

**Download de conteúdos OPTO · Interface moderna · Windows · macOS · Linux**

<br/>

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-555?style=flat-square)](../../releases)
[![Status](https://img.shields.io/badge/Status-Active-22c55e?style=flat-square)](../../releases)
[![Buy Me a Coffee](https://img.shields.io/badge/☕%20Buy%20Me%20a%20Coffee-support-f59e0b?style=flat-square)](https://buymeacoffee.com/miguelmaster12)

<br/>

</div>

---

## O que é isto?

Uma aplicação desktop para descarregar episódios da plataforma **OPTO (SIC)** para uso pessoal — com interface gráfica moderna, suporte a séries completas, player integrado e downloads em paralelo.

> Requer uma conta OPTO com acesso legítimo ao conteúdo e um ficheiro `.wvd` próprio para desencriptação Widevine.

---

## ⚠️ Aviso Legal

Este projeto destina-se a **uso pessoal e educativo** com conteúdos aos quais tens acesso legítimo.

**Não utilizes esta ferramenta para:**
- aceder a conteúdos sem autorização
- contornar subscrições ou restrições de acesso
- redistribuir ou partilhar conteúdos protegidos
- violar os termos de serviço da plataforma

O projeto não inclui credenciais, ficheiros `.wvd`, chaves privadas nem qualquer mecanismo de acesso indevido. **Cada utilizador é responsável pela forma como usa a ferramenta.**

---

## ✨ Funcionalidades

| | Funcionalidade |
|---|---|
| 🖥️ | Interface Qt moderna e responsiva |
| 📥 | Download de episódio único ou série completa |
| 📂 | Seleção por temporada, incluindo extras e nomes reais |
| ▶️ | Player integrado com reprodução temporária |
| ⚡ | Fila de downloads com workers paralelos e progresso em tempo real |
| 🔑 | Gerador de `.wvd` integrado na interface |
| ⚙️ | Preferências persistentes (idioma, pasta, qualidade) |
| 🔍 | Diagnóstico de ferramentas e estado do ambiente |
| 💻 | CLIs autónomos para uso avançado sem interface |
| 🌐 | Windows · macOS · Linux |

---

## 🚀 Instalação Rápida

> **A forma mais simples é pelo instalador.** Descarrega, instala, e abre.

### Passo 1 — Descarregar

Vai à página de **[Releases](../../releases)** e escolhe o ficheiro para o teu sistema:

| Sistema | Instalador | Pacote ZIP |
|---|---|---|
| 🪟 Windows | `opto-downloader-*-windows-setup.exe` | `opto-downloader-*-windows.zip` |
| 🍎 macOS | `opto-downloader-*-macos.dmg` | `opto-downloader-*-macos.zip` |
| 🐧 Linux | `opto-downloader-*-linux.AppImage` | `opto-downloader-*-linux.zip` |

**Recomendado:** usa o instalador (`.exe` / `.dmg` / `.AppImage`). O ZIP é para quem prefere controlo manual.

---

### Passo 2 — Instalar

**🪟 Windows**
Abre o `.exe` e segue o assistente. O `ffmpeg`, `ffprobe` e `mp4decrypt` são incluídos automaticamente.

**🍎 macOS**
Abre o `.dmg` e arrasta a app para `Applications`.

Se o macOS bloquear a app por "programador não verificado", executa no Terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/OPTO Downloader.app"
open "/Applications/OPTO Downloader.app"
```

**🐧 Linux**
Dá permissão de execução ao `.AppImage` e abre:

```bash
chmod +x opto-downloader-*.AppImage
./opto-downloader-*.AppImage
```

---

### Passo 3 — Instalar a partir do ZIP *(opcional)*

Se preferiste o ZIP em vez do instalador:

```bash
# 1. Extrai o ZIP e entra na pasta
# 2. Cria e activa um ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instala as dependências
python3 instalar_dependencias.py
```

Ou usa o script da tua plataforma:

```bash
# Windows
.\platform\install_windows.bat

# macOS
./platform/install_macos.sh

# Linux
./platform/install_linux.sh
```

---

### Passo 4 — Arrancar a aplicação

```bash
# Interface gráfica
python3 opto_app.py

# Ou pelo script da plataforma:
.\platform\run_windows.bat      # Windows
./platform/run_macos.sh         # macOS
./platform/run_linux.sh         # Linux
```

---

## 🔑 Configurar o ficheiro `.wvd`

O `.wvd` é um ficheiro de desencriptação Widevine **pessoal e intransmissível** — sem ele, a app não consegue concluir downloads protegidos.

> 🔒 **Nunca partilhes** o teu `.wvd`, `private_key.pem`, `client_id.bin`, keys ou tokens de sessão.

Tens duas formas de o obter:

---

### Opção A — Criar a partir de um dispositivo Android *(recomendado)*

1. Prepara um ambiente Android (dispositivo físico ou emulador via Android Studio)
2. Segue o guia: [Dumping Your own L3 CDM — VideoHelp Forum](https://forum.videohelp.com/threads/408031-Dumping-Your-own-L3-CDM-with-Android-Studio)
3. Guarda os ficheiros `client_id.bin` e `private_key.pem` obtidos
4. Na app, vai ao separador **Estado → Gerar ficheiro .wvd**
5. Seleciona os dois ficheiros, escolhe a pasta de saída e clica em **Gerar .wvd**

### Opção B — Usar um CDM partilhado por terceiros

1. Descarrega de uma fonte de confiança: [Ready to use CDMs — VideoHelp Forum](https://forum.videohelp.com/threads/413719-Ready-to-use-CDMs-available-here%21)
2. Extrai o `client_id.bin` e o `private_key.pem`
3. Segue os passos 4 e 5 da Opção A

> ⚠️ A utilização de CDMs de terceiros é da tua inteira responsabilidade.

**Onde colocar o `.wvd`** — a app procura nestas localizações, por ordem:
- `secrets/` (pasta do projeto)
- `~/.wvd/`
- Pastas antigas da app

---

## 🎬 Como usar

### Primeiro arranque

1. Abre a app e vai ao separador **Estado**
2. Confirma que `ffmpeg`, `ffprobe` e `mp4decrypt` aparecem como disponíveis
3. Coloca o teu `.wvd` em `secrets/` — ou gera-o conforme acima
4. Vai a **Preferências** e define a pasta de destino e qualidade padrão
5. Estás pronto

---

### Descarregar um episódio

1. Vai ao separador **Episódio**
2. Cola o URL do episódio:
   ```
   https://opto.sic.pt/vod/nome-do-episodio/uuid
   ```
3. Clica em **Analisar**, escolhe a qualidade
4. Clica em **Download** — ou **Play** para reprodução temporária sem guardar

---

### Descarregar uma série

1. Vai ao separador **Série**
2. Cola o URL da série:
   ```
   https://opto.sic.pt/series/nome-da-serie/uuid
   ```
3. Carrega os episódios, seleciona temporadas ou episódios específicos
4. Clica em **Download em lote**

A app organiza automaticamente os ficheiros por série e temporada, ignora episódios já descarregados e faz prefetch de keys em background.

---

### Fila de downloads

No separador **Downloads** podes acompanhar o progresso, cancelar tarefas e ver o histórico de ficheiros concluídos. O número de workers paralelos é definido nas **Preferências**.

---

## 💻 Uso via linha de comandos *(avançado)*

```bash
# Listar episódios de uma série
python3 opto_api_scraper.py "https://opto.sic.pt/series/a-heranca/UUID" --json

# Resolver um episódio (MPD, License URL, PSSH)
python3 opto_api_media_resolver.py "URL_OU_UUID" --json

# Testar keys Widevine
python3 opto_api_media_resolver.py "URL_OU_UUID" --test-keys --json

# Fazer download via CLI
python3 opto_api_media_resolver.py "URL_OU_UUID" --download --quality 720
```

---

## 🔄 Atualizar

Vai à página de **[Releases](../../releases)** e descarrega a versão mais recente.

- **Windows:** abre o novo `.exe` e instala por cima da versão anterior
- **macOS:** abre o `.dmg` e substitui a app em `Applications`
- **Linux:** substitui o `.AppImage` antigo e confirma a permissão de execução
- **ZIP:** extrai para a mesma pasta, substituindo os ficheiros; corre o script de instalação se houver erros de dependências

> Mantém sempre a pasta `secrets/` e o teu `.wvd` ao atualizar.

---

## 🗑️ Desinstalar

**Windows** — usa "Aplicações instaladas" para remover; se usaste o ZIP, apaga a pasta manualmente.

**macOS:**
```bash
rm -rf "/Applications/OPTO Downloader.app"
```

**Linux** — apaga o `.AppImage` ou a pasta extraída.

**Limpeza opcional de dados locais:**
```bash
rm -rf config state downloads vendor secrets
```
> ⚠️ Apagar `secrets/` remove o teu `.wvd`, `private_key.pem` e `client_id.bin`.

---

## 🐛 Problemas comuns

<details>
<summary><strong>macOS bloqueia a app — "programador não verificado"</strong></summary>

A app ainda não está assinada pela Apple. Para contornar:

```bash
xattr -dr com.apple.quarantine "/Applications/OPTO Downloader.app"
open "/Applications/OPTO Downloader.app"
```

Em alternativa, no Finder clica com o botão direito na app e escolhe **Abrir**.
</details>

<details>
<summary><strong>Ficheiro <code>.wvd</code> não encontrado</strong></summary>

A app procura o `.wvd` em `secrets/`, `~/.wvd/` e pastas antigas da app.
Coloca o ficheiro em qualquer uma dessas localizações e reinicia a app.
</details>

<details>
<summary><strong>MPD ou License URL não obtidos</strong></summary>

Confirma que:
- a tua sessão na OPTO está ativa
- consegues reproduzir o conteúdo num browser normal
- a tua conta tem acesso ao conteúdo em causa
</details>

<details>
<summary><strong><code>ffmpeg</code>, <code>ffprobe</code> ou <code>mp4decrypt</code> em falta</strong></summary>

Corre novamente o instalador da tua plataforma, ou instala as ferramentas manualmente e garante que estão disponíveis no `PATH`.

Verifica o estado no separador **Estado** da interface.
</details>

<details>
<summary><strong>Ficheiro <code>.invalid.mp4</code> gerado</strong></summary>

A validação final detectou um problema. Confirma:
- acesso ao conteúdo na tua conta
- validade do `.wvd`
- disponibilidade de `ffmpeg`, `ffprobe` e `mp4decrypt` durante o download
</details>

---

## 📦 Dependências

| Pacote | Função |
|---|---|
| `PySide6` | Interface gráfica Qt |
| `yt-dlp` | Download de streams |
| `requests` | Pedidos HTTP |
| `pywidevine` | Desencriptação Widevine |
| `ffmpeg` / `ffprobe` | Processamento de média |
| `mp4decrypt` | Desencriptação de MP4 (Bento4) |

No instalador Windows, todos os binários são incluídos automaticamente.

---

## 📁 Estrutura do projeto

```
opto-downloader/
├── opto_app.py                  # Interface Qt principal
├── opto_api_scraper.py          # CLI — scrape de séries
├── opto_api_media_resolver.py   # CLI — resolução de episódio e download
├── instalar_dependencias.py     # Instalador local de dependências
├── assets/                      # Ícones e imagens
├── config/                      # Preferências persistentes
├── platform/                    # Scripts de instalação e arranque
├── scripts/                     # Scripts de build e release
├── secrets/                     # Pasta para o .wvd (não incluída no repo)
└── state/                       # Cache de listagens e histórico
```

---

## 🏗️ Builds locais

```bash
# ZIPs multiplataforma
scripts/build_release_zips.sh vX.Y.Z

# macOS DMG
scripts/build_macos_dmg.sh vX.Y.Z

# Windows Installer
scripts\build_windows_exe.ps1 vX.Y.Z

# Linux AppImage
scripts/build_linux_appimage.sh vX.Y.Z
```

Os artefactos são gerados em `release-dist/`.

---

## 🤝 Contribuir

Contribuições são bem-vindas, em especial em:

- robustez do scraping e resolução via API
- tratamento de erros e edge cases
- experiência de utilização
- documentação
- builds multiplataforma

Por favor, **não abras issues ou pull requests** com conteúdos protegidos, credenciais, tokens, ficheiros `.wvd`, chaves privadas ou ficheiros descarregados.

---

## ☕ Apoiar o projeto

Este projeto é desenvolvido e mantido em tempo livre.
Se te foi útil, considera apoiar:

<div align="center">

[![Buy Me a Coffee](https://img.shields.io/badge/☕%20Buy%20Me%20a%20Coffee-f59e0b?style=for-the-badge)](https://buymeacoffee.com/miguelmaster12)

</div>

---

<div align="center">
<sub>Uso pessoal · Sem afiliação com a SIC ou OPTO</sub>
</div>
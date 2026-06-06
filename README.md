# OPTO Downloader

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/Status-Active-success)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/miguelmaster12)

Ferramenta local para analisar, reproduzir temporariamente e descarregar episódios OPTO usando APIs HTTP.

Uso pessoal apenas. Requer acesso legítimo ao conteúdo e um ficheiro `.wvd` próprio para obter keys Widevine.

> **Nota:** A forma recomendada de instalação é através dos pacotes disponíveis na página de [Releases](../../releases).

---

## ⚠️ Aviso Legal

Este projeto foi desenvolvido para fins de **teste, aprendizagem e utilização pessoal** com conteúdos aos quais o utilizador possui acesso legítimo.

**Não utilizes esta ferramenta para:**

- aceder a conteúdos sem autorização;
- contornar subscrições ou restrições de acesso;
- redistribuir ou partilhar conteúdos protegidos;
- violar os termos de serviço da plataforma.

Cada utilizador é **responsável pela forma como utiliza a ferramenta**.

O projeto não inclui credenciais, contas, conteúdos, ficheiros `.wvd`, nem qualquer mecanismo destinado a obter acesso indevido a conteúdos protegidos.

---

## ✨ Funcionalidades

- Interface Qt moderna (`opto_app.py`)
- Download de episódio único
- Download de séries em lote com seleção por temporada (incluindo `Extras T2` e nomes reais)
- Player integrado com reprodução temporária e cache do episódio anterior/seguinte
- Fila de downloads com progresso, agrupamento por série/temporada e cancelamento
- Resolução de MPD, License URL assinada e PSSH via API/Kaltura `multirequest`
- Scrape de séries e episódios via API OPTO (sem browser)
- CLI de série em `opto_api_scraper.py`
- CLI de episódio/download em `opto_api_media_resolver.py`
- Gerador `.wvd` pela interface a partir de `private_key.pem` e `client_id.bin`
- Preferências persistentes (idioma, pasta e qualidade predefinidos)
- Verificação de ferramentas e estado do ambiente integrados
- Suporte para Windows, macOS e Linux

---

## 📋 Requisitos

- Python 3.9 ou superior
- Conta OPTO com acesso legítimo ao conteúdo
- Ficheiro `.wvd` pessoal colocado em `secrets/`, `~/.wvd/` ou numa pasta antiga da app
- `ffmpeg` e `ffprobe`
- `mp4decrypt` do Bento4

> O ficheiro `.wvd` **não é fornecido** por este projeto.
> Sem um `.wvd` válido, a ferramenta pode analisar e listar conteúdos, mas **não consegue desencriptar nem concluir downloads protegidos**.

---

## 🚀 Instalação

A forma recomendada de utilização é através dos ficheiros disponibilizados na página de [Releases](../../releases).

### 1. Descarregar

Escolhe o ficheiro correspondente ao teu sistema operativo.

**Instalador / DMG / AppImage**

| Sistema Operativo | Ficheiro                               |
| ----------------- | -------------------------------------- |
| Windows           | `opto-downloader-*-windows-setup.exe` |
| macOS             | `opto-downloader-*-macos.dmg`      |
| Linux             | `opto-downloader-*-linux.AppImage` |

**Pacotes ZIP com scripts de instalação**

| Sistema Operativo | Ficheiro                            |
| ----------------- | ----------------------------------- |
| Windows           | `opto-downloader-*-windows.zip` |
| macOS             | `opto-downloader-*-macos.zip`   |
| Linux             | `opto-downloader-*-linux.zip`   |

### 2. Instalar ou Extrair

Se descarregaste o instalador Windows, abre-o e escolhe a pasta de instalação no assistente. Se descarregaste um DMG ou AppImage, abre-o diretamente.

Se descarregaste um ZIP, extrai o conteúdo para uma pasta à tua escolha.

**macOS**

Se instalaste pelo `.dmg` e o macOS bloquear a app por programador não verificado, executa:

```bash
xattr -dr com.apple.quarantine "/Applications/OPTO Downloader.app"
open "/Applications/OPTO Downloader.app"
```

### 3. Instalação Local (a partir do ZIP ou repositório)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python3 instalar_dependencias.py
```

Ou instala manualmente:

```bash
pip install PySide6 requests pywidevine yt-dlp
```

Também precisas de `ffmpeg`, `ffprobe` e `mp4decrypt` (Bento4) disponíveis no PATH.

**Windows**

```powershell
.\platform\install_windows.bat
# ou
powershell -ExecutionPolicy Bypass -File .\platform\install_windows.ps1
```

**macOS**

```bash
chmod +x platform/install_macos.sh platform/run_macos.sh
./platform/install_macos.sh
```

**Linux**

```bash
chmod +x platform/install_linux.sh platform/run_linux.sh
./platform/install_linux.sh
```

### 4. Iniciar

**Interface gráfica**

```bash
python3 opto_app.py
```

**Windows**

```powershell
.\platform\run_windows.bat
```

**macOS**

```bash
./platform/run_macos.sh
```

**Linux**

```bash
./platform/run_linux.sh
```

---

## 🔑 Como Obter um `.wvd`

Este projeto requer um CDM Widevine L3 em formato `.wvd`.

> **Importante:** sem um `.wvd` válido em `secrets/`, `~/.wvd/` ou numa pasta antiga da app, os downloads protegidos não são concluídos.

Tens duas opções:

---

### Opção A — Criar o teu próprio CDM a partir de um dispositivo Android

Este é o método recomendado. O CDM é extraído de um dispositivo ou emulador Android que controlas.

**Guia de referência:**

- [Dumping Your own L3 CDM with Android Studio — VideoHelp Forum](https://forum.videohelp.com/threads/408031-Dumping-Your-own-L3-CDM-with-Android-Studio)

**Passos:**

1. Prepara um ambiente Android próprio (dispositivo físico ou emulador via Android Studio).
2. Segue o guia acima para extrair o CDM.
3. Guarda os ficheiros `client_id.bin` e `private_key.pem`.
4. Abre a aplicação, vai ao separador **Estado** e usa a secção **Gerar ficheiro .wvd**.
5. Seleciona os dois ficheiros, escolhe a pasta de saída e clica em **Gerar .wvd**.

---

### Opção B — Usar ficheiros partilhados por terceiros

Caso não queiras criar o teu próprio, existem ficheiros partilhados publicamente por terceiros:

- [Ready to use CDMs — VideoHelp Forum](https://forum.videohelp.com/threads/413719-Ready-to-use-CDMs-available-here%21)

O ZIP costuma conter os ficheiros `client_id.bin` e `private_key.pem`. Após descarregar:

1. Extrai o `client_id.bin` e o `private_key.pem`.
2. Abre a aplicação, vai ao separador **Estado** e usa a secção **Gerar ficheiro .wvd**.
3. Seleciona os dois ficheiros, escolhe a pasta de saída e clica em **Gerar .wvd**.

> ⚠️ Usa apenas ficheiros de fontes em que confias. A utilização de CDMs de terceiros é da tua inteira responsabilidade.

---

> 🔒 Nunca partilhes o teu `.wvd`, `client_id.bin`, `private_key.pem`, keys, tokens ou dados de sessão.

---

## 🛠️ Primeiro Uso

1. Inicia a aplicação com `python3 opto_app.py` ou pelo script da tua plataforma.
2. Vai ao separador **Estado**.
3. Verifica se todas as ferramentas necessárias estão disponíveis (`ffmpeg`, `ffprobe`, `mp4decrypt`).
4. Se já tens um `.wvd`, coloca-o em `secrets/` ou `~/.wvd/`.
5. Se tens `private_key.pem` e `client_id.bin`, usa **Gerar ficheiro .wvd** para criar o `.wvd`.
6. Vai ao separador **Preferências** e define a pasta de destino e a qualidade predefinida.
7. Abre o separador **Episódio** ou **Série** e começa a descarregar.

> Se o `.wvd` não existir ou não for válido, a aplicação pode resolver e analisar conteúdos, mas falhará na obtenção de keys e desencriptação.

---

## 📖 Utilização

### Interface Gráfica

#### Episódio

Cola uma URL ou UUID de episódio:

```
https://opto.sic.pt/vod/nome-do-episodio/uuid
```

Clica em **Analisar**, escolhe a qualidade e clica em **Download** ou **Play** para reprodução temporária sem guardar na pasta final.

#### Série

Cola uma URL de série:

```
https://opto.sic.pt/series/nome-da-serie/uuid
```

Carrega os episódios, seleciona temporadas/episódios e clica em **Download em lote** ou **Play em playlist**.

#### Downloads

Acompanha a fila de downloads com progresso individual, agrupamento por série/temporada, cancelamento e lista de ficheiros concluídos.

#### Player

Reproduz ficheiros temporários gerados pela app. Mantém cache do episódio anterior e seguinte para transições rápidas.

#### Preferências

Configura idioma, pasta de destino predefinida e qualidade predefinida.

#### Estado

Verifica a disponibilidade de ferramentas externas e gera o ficheiro `.wvd`.

---

## 💻 CLI

Para utilização sem interface gráfica, estão disponíveis dois scripts autónomos.

### Listar uma série

```bash
python3 opto_api_scraper.py "https://opto.sic.pt/series/a-heranca/UUID" --json
```

### Resolver um episódio

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID_DO_EPISODIO" --json
```

### Testar keys Widevine

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID_DO_EPISODIO" --test-keys --json
```

### Fazer download

```bash
python3 opto_api_media_resolver.py "URL_OU_UUID_DO_EPISODIO" --download --quality 720
```

---

## 🏗️ Builds Locais

Os artefactos são criados em `release-dist/`.

**ZIPs por plataforma**

```bash
scripts/build_release_zips.sh vX.Y.Z
```

**macOS DMG**

```bash
scripts/build_macos_dmg.sh vX.Y.Z
```

**Windows Installer**

```powershell
scripts\build_windows_exe.ps1 vX.Y.Z
```

**Linux AppImage**

```bash
scripts/build_linux_appimage.sh vX.Y.Z
```

---

## 🔄 Atualizar

Transfere a versão mais recente na página de [Releases](../../releases).

**Instalador / DMG / AppImage**

- Windows: abre o novo `*-windows-setup.exe` e instala por cima da versão anterior.
- macOS: abre o novo `.dmg` e copia a app novamente para `Applications`, substituindo a anterior.
- Linux: substitui o `.AppImage` antigo pelo novo e garante que tem permissão de execução.

**Pacote ZIP**

1. Descarrega o ZIP mais recente para a tua plataforma.
2. Extrai para uma nova pasta ou substitui os ficheiros antigos.
3. Executa novamente o script de instalação da tua plataforma se houver erro de dependências.

> Mantém a pasta `secrets/` e o teu `.wvd`. Sem o `.wvd`, os downloads protegidos não são concluídos.

---

## 🗑️ Desinstalar

Fecha a aplicação antes de remover ficheiros.

**Windows**

Usa "Aplicações instaladas" / "Programas e Funcionalidades" do Windows para remover o Opto Downloader. Se usaste o ZIP, apaga a pasta onde o extraíste.

**macOS**

```bash
rm -rf "/Applications/OPTO Downloader.app"
```

**Linux**

Apaga a pasta onde extraíste o ZIP ou remove o `.AppImage` que descarregaste.

**Limpeza opcional de dados locais**

```bash
rm -rf config state downloads vendor secrets
```

> Atenção: apagar `secrets/` remove o teu `.wvd`, `private_key.pem` e `client_id.bin`.

---

## 📦 Dependências

O instalador prepara automaticamente:

| Dependência          | Tipo                            |
| -------------------- | ------------------------------- |
| `PySide6`            | Interface gráfica Qt            |
| `yt-dlp`             | Download de streams             |
| `requests`           | Pedidos HTTP                    |
| `pywidevine`         | Desencriptação Widevine         |
| `ffmpeg` / `ffprobe` | Processamento de média          |
| `mp4decrypt`         | Desencriptação de ficheiros MP4 |

> Dependendo do sistema operativo, algumas dependências podem exigir permissões de administrador.

---

## 📁 Estrutura do Projeto

| Ficheiro / Pasta             | Descrição                                                  |
| ---------------------------- | ---------------------------------------------------------- |
| `opto_app.py`                | Interface Qt principal                                     |
| `opto_api_scraper.py`        | CLI de scrape de séries via API                            |
| `opto_api_media_resolver.py` | CLI de resolução de episódio, keys e download              |
| `instalar_dependencias.py`   | Instalador local de dependências                           |
| `assets/`                    | Ícones e imagens da app                                    |
| `config/`                    | Configuração persistente                                   |
| `platform/`                  | Scripts de instalação e arranque por plataforma            |
| `scripts/`                   | Scripts de build e release                                 |
| `secrets/`                   | Pasta para o ficheiro `.wvd` (não incluída no repositório) |
| `state/`                     | Cache de listagens e histórico de downloads                |

---

## 🐛 Problemas Comuns

<details>
<summary><strong>macOS bloqueia a app por programador não verificado</strong></summary>

Enquanto a app não estiver assinada/notarizada pela Apple, o macOS pode mostrar uma mensagem a dizer que não conseguiu confirmar se a aplicação contém malware.

Para abrir depois de instalar em `Applications`:

```bash
xattr -dr com.apple.quarantine "/Applications/OPTO Downloader.app"
open "/Applications/OPTO Downloader.app"
```

Também podes tentar abrir com botão direito no Finder e escolher **Abrir**.

</details>

<details>
<summary><strong>.wvd não encontrado</strong></summary>

A app procura o ficheiro `.wvd` nas seguintes localizações, por ordem:

- `secrets/` (pasta do projeto)
- `~/.wvd/`
- Pastas antigas da app

Coloca o ficheiro `.wvd` em qualquer uma dessas localizações.

</details>

<details>
<summary><strong>MPD ou License URL não obtidos</strong></summary>

Confirma que:

- a sessão na OPTO está ativa e válida;
- consegues reproduzir o conteúdo num browser normal;
- a conta possui acesso ao conteúdo pretendido.
</details>

<details>
<summary><strong>ffmpeg, ffprobe ou mp4decrypt em falta</strong></summary>

Executa novamente o instalador da tua plataforma ou instala as ferramentas manualmente e garante que estão disponíveis no PATH.

Verifica o estado das ferramentas no separador **Estado** da interface.

</details>

<details>
<summary><strong>Ficheiro <code>.invalid.mp4</code></strong></summary>

A validação final detetou um ficheiro inválido. Confirma:

- acesso ao conteúdo na tua conta;
- validade do ficheiro `.wvd`;
- disponibilidade de `ffmpeg`, `ffprobe` e `mp4decrypt` durante o processo.
</details>

---

## 🤝 Contribuições

Melhorias são bem-vindas, especialmente em:

- robustez do scraping e resolução via API;
- tratamento de erros;
- experiência de utilização;
- documentação;
- organização do código;
- builds multiplataforma.

Por favor, **não abras issues ou pull requests** contendo conteúdos protegidos, credenciais, tokens, ficheiros `.wvd`, chaves privadas ou ficheiros descarregados.

---

## ☕ Apoiar o Projeto

Este projeto é desenvolvido e mantido em tempo livre. Se te foi útil e quiseres apoiar o desenvolvimento:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/miguelmaster12)

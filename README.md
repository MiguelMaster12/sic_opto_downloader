# SIC OPTO Downloader

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/Status-Active-success)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/miguelmaster12)

Ferramenta experimental para testes pessoais com conteúdos SIC OPTO acessíveis pela própria conta do utilizador.

O projeto abre um perfil Chrome dedicado, captura dados técnicos de reprodução (`MPD`, `License URL`, `PSSH`), usa `pywidevine` com um `.wvd` fornecido pelo utilizador, descarrega os streams e gera um ficheiro `.mp4`.

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

- Download de episódio único
- Download de séries com seleção de episódios
- Cache progressivo de listagens
- Registo de episódios já descarregados
- Perfil Chrome dedicado
- Instalação automática de dependências
- Chrome iniciado minimizado, com áudio mutado e autoplay bloqueado
- Suporte a uBlock Origin Lite no perfil debug, quando instalado
- Configuração persistente
- Suporte para Windows, macOS e Linux

---

## 📋 Requisitos

- Python 3.9 ou superior
- Google Chrome instalado
- Conta SIC OPTO com acesso legítimo ao conteúdo
- Ficheiro `.wvd` pessoal colocado em `secrets/`

> O ficheiro `.wvd` **não é fornecido** por este projeto.

---

## 🚀 Instalação

A forma recomendada de utilização é através dos pacotes disponibilizados na página de [Releases](../../releases).

### 1. Descarregar

Escolhe o pacote correspondente ao teu sistema operativo:

| Sistema Operativo | Ficheiro |
|---|---|
| Windows | `sic-opto-downloader-windows.zip` |
| macOS | `sic-opto-downloader-macos.zip` |
| Linux | `sic-opto-downloader-linux.zip` |

### 2. Extrair

Extrai o conteúdo do ficheiro ZIP para uma pasta à tua escolha.

### 3. Instalar Dependências

**Windows**
```powershell
.\install_windows.bat
# ou
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
```

**macOS**
```bash
chmod +x install_macos.sh run_macos.sh
./install_macos.sh
```

**Linux**
```bash
chmod +x install_linux.sh run_linux.sh
./install_linux.sh
```

### 4. Iniciar

**Windows**
```powershell
.\run_windows.bat
```

**macOS**
```bash
./run_macos.sh
```

**Linux**
```bash
./run_linux.sh
```

---

## 🔑 Como Obter um `.wvd`

Este projeto requer um CDM Widevine L3 em formato `.wvd`.

Tens duas opções:

---

### Opção A — Criar o teu próprio CDM a partir de um dispositivo Android

Este é o método recomendado. O CDM é extraído de um dispositivo ou emulador Android que controlas.

**Guia de referência:**
- [Dumping Your own L3 CDM with Android Studio — VideoHelp Forum](https://forum.videohelp.com/threads/408031-Dumping-Your-own-L3-CDM-with-Android-Studio)

**Passos:**

1. Prepara um ambiente Android próprio (dispositivo físico ou emulador via Android Studio).
2. Segue o guia acima para extrair o CDM.
3. Copia os ficheiros `client_id.bin` e `private_key.pem` para a pasta `secrets/`.
4. Executa o comando para gerar o `.wvd`:

```bash
pywidevine create-device -k "secrets/private_key.pem" -c "secrets/client_id.bin" -t "ANDROID" -l 3 -o "./secrets/"
```

---

### Opção B — Usar ficheiros partilhados por terceiros

Caso não queiras criar o teu próprio, existem ficheiros partilhados publicamente por terceiros:

- [Ready to use CDMs — VideoHelp Forum](https://forum.videohelp.com/threads/413719-Ready-to-use-CDMs-available-here%21)

O ZIP contém os ficheiros `client_id.bin` e `private_key.pem`. Após descarregar:

1. Extrai o `client_id.bin` e o `private_key.pem` para a pasta `secrets/`.
2. Executa o comando para gerar o `.wvd`:

```bash
pywidevine create-device -k "secrets/private_key.pem" -c "secrets/client_id.bin" -t "ANDROID" -l 3 -o "./secrets/"
```

> ⚠️ Usa apenas ficheiros de fontes em que confias. A utilização de CDMs de terceiros é da tua inteira responsabilidade.

---

> 🔒 Nunca partilhes o teu `.wvd`, `client_id.bin`, `private_key.pem`, keys, cookies ou perfil Chrome.

---

## 🛠️ Primeiro Uso

1. Coloca o teu ficheiro `.wvd` em `secrets/`.
2. Inicia a aplicação.
3. Vai à aba **CONFIG**.
4. Confirma o caminho do Chrome.
5. Mantém o perfil Chrome como `chrome-debug-profile`.
6. Abre o Chrome através da aplicação.
7. Faz login na tua conta SIC OPTO.
8. Regressa à aba **DOWNLOAD**.

---

## 📖 Utilização

### Episódio

Cola uma URL de episódio no formato:

```
https://opto.sic.pt/vod/nome-do-episodio/uuid
```

Escolhe a qualidade e a pasta de destino e clica em **INICIAR DOWNLOAD**.

### Série

Cola uma URL de série no formato:

```
https://opto.sic.pt/series/nome-da-serie/uuid
```

Clica em **SÉRIE**, seleciona os episódios pretendidos e confirma.

**Notas:**
- `CANCELAR SCRAPE` interrompe a listagem a qualquer momento.
- Episódios já descarregados aparecem assinalados automaticamente.
- Cache: `state/sic_opto_cache.json`
- Histórico: `state/sic_opto_downloads.json`

---

## ⚙️ Configuração

O ficheiro de configuração encontra-se em:

```
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

---

## 📁 Estrutura do Projeto

```
.
├── v3.py
├── instalar_dependencias.py
├── README.md
├── assets/
├── config/
├── platform/
│   ├── windows/
│   ├── macos/
│   └── linux/
├── scripts/
├── state/
├── secrets/
├── vendor/
└── chrome-debug-profile/
```

---

## 📦 Dependências

O instalador prepara automaticamente:

| Dependência | Tipo |
|---|---|
| `yt-dlp` | Download de streams |
| `requests` | Pedidos HTTP |
| `pywidevine` | Desencriptação Widevine |
| `selenium` | Automação do browser |
| `websocket-client` | Comunicação com o Chrome |
| `ffmpeg` / `ffprobe` | Processamento de média |
| `mp4decrypt` | Desencriptação de ficheiros MP4 |
| uBlock Origin Lite | Bloqueio de anúncios no perfil debug |

> Dependendo do sistema operativo, algumas dependências podem exigir permissões de administrador.

---

## 🐛 Problemas Comuns

<details>
<summary><strong>macOS bloqueia a app por programador não verificado</strong></summary>

Enquanto a app não estiver assinada/notarizada pela Apple, o macOS pode mostrar uma mensagem a dizer que não conseguiu confirmar se a aplicação contém malware.

Para abrir depois de instalar em `Applications`:

```bash
xattr -dr com.apple.quarantine "/Applications/SIC OPTO Downloader.app"
open "/Applications/SIC OPTO Downloader.app"
```

Também podes tentar abrir com botão direito no Finder e escolher **Abrir**.
</details>

<details>
<summary><strong>.wvd não encontrado</strong></summary>

Coloca o ficheiro `.wvd` dentro da pasta:

```
secrets/
```
</details>

<details>
<summary><strong>Chrome não respondeu</strong></summary>

Verifica que:
- o caminho do Chrome está correto na configuração;
- não existem múltiplas instâncias conflitantes;
- o perfil Chrome não está bloqueado por outro processo.
</details>

<details>
<summary><strong>MPD não obtido</strong></summary>

Confirma que:
- tens sessão iniciada na SIC OPTO;
- consegues reproduzir o conteúdo no browser;
- a conta possui acesso ao conteúdo.
</details>

<details>
<summary><strong>ffmpeg, ffprobe ou mp4decrypt em falta</strong></summary>

Executa novamente o instalador da tua plataforma.
</details>

<details>
<summary><strong>Ficheiro <code>.invalid.mp4</code></strong></summary>

A validação final detetou um ficheiro inválido. Confirma:
- acesso ao conteúdo na tua conta;
- configuração correta do ambiente;
- validade do ficheiro `.wvd`;
- disponibilidade dos recursos necessários durante o processo.
</details>

---

## 🧑‍💻 Desenvolvimento

**Verificar sintaxe:**
```bash
python -m py_compile v3.py instalar_dependencias.py
```

**Instalação manual de dependências:**
```bash
python instalar_dependencias.py
```

**Execução manual:**
```bash
python v3.py
```

---

## 🔒 Segurança

Nunca partilhes as seguintes pastas ou ficheiros:

```
.venv/
chrome-debug-profile/
secrets/
state/
vendor/
downloads/
```

Também não deves partilhar: ficheiros `.wvd`, cookies, perfis Chrome, credenciais, chaves privadas ou conteúdos descarregados.

O `.gitignore` já exclui estes caminhos do repositório.

---

## 🤝 Contribuições

Melhorias são bem-vindas, especialmente em:

- instalação multiplataforma;
- robustez do scraping;
- tratamento de erros;
- experiência de utilização;
- documentação;
- organização do código.

Por favor, **não abras issues ou pull requests** contendo conteúdos protegidos, credenciais, cookies, ficheiros `.wvd`, chaves privadas ou ficheiros descarregados.

---

## ☕ Apoiar o Projeto

Este projeto é desenvolvido e mantido em tempo livre. Se te foi útil e quiseres apoiar o desenvolvimento:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/miguelmaster12)

# SIC OPTO Downloader

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python\&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/Status-Active-success)
![Release](https://img.shields.io/github/v/release/MiguelMaster12/sic_opto_downloader)

Ferramenta experimental para testes pessoais com conteúdos SIC OPTO acessíveis pela própria conta do utilizador.

O projeto abre um perfil Chrome dedicado, captura dados técnicos de reprodução (`MPD`, `License URL`, `PSSH`), usa `pywidevine` com um `.wvd` fornecido pelo utilizador, descarrega streams e gera um ficheiro `.mp4`.

> A forma recomendada de instalação é através dos pacotes disponíveis na página de Releases.

---

# Aviso Legal

Este projeto foi desenvolvido para fins de teste, aprendizagem e utilização pessoal com conteúdos aos quais o utilizador possui acesso legítimo.

Não utilizes esta ferramenta para:

* aceder a conteúdos sem autorização;
* contornar subscrições ou restrições de acesso;
* redistribuir conteúdos protegidos;
* partilhar ficheiros descarregados;
* violar termos de serviço da plataforma.

Cada utilizador é responsável pela forma como utiliza a ferramenta.

O projeto não inclui credenciais, contas, conteúdos, ficheiros `.wvd`, nem qualquer mecanismo destinado a obter acesso indevido a conteúdos protegidos.

---

# Funcionalidades

* Download de episódio único.
* Download de séries com seleção de episódios.
* Cache progressivo de listagens.
* Registo de episódios já descarregados.
* Perfil Chrome dedicado.
* Instalação automática de dependências.
* Chrome iniciado minimizado, com áudio mutado e autoplay bloqueado.
* Suporte a uBlock Origin Lite no perfil debug, quando instalado.
* Configuração persistente.
* Suporte para Windows, macOS e Linux.

---

# Requisitos

* Python 3.9 ou superior.
* Google Chrome instalado.
* Conta SIC OPTO com acesso legítimo ao conteúdo.
* Ficheiro `.wvd` pessoal colocado em `secrets/`.

> O ficheiro `.wvd` não é fornecido por este projeto.

---

# Instalação

A forma recomendada de utilização é através dos pacotes disponibilizados na página de Releases.

## 1. Descarregar

Escolhe o pacote correspondente ao teu sistema operativo:

* Windows → `sic-opto-downloader-windows.zip`
* macOS → `sic-opto-downloader-macos.zip`
* Linux → `sic-opto-downloader-linux.zip`

## 2. Extrair

Extrai o conteúdo do ficheiro ZIP para uma pasta à tua escolha.

## 3. Instalar Dependências

### Windows

```powershell
.\install_windows.bat
```

ou

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
```

### macOS

```bash
chmod +x install_macos.sh run_macos.sh
./install_macos.sh
```

### Linux

```bash
chmod +x install_linux.sh run_linux.sh
./install_linux.sh
```

## 4. Iniciar

### Windows

```powershell
.\run_windows.bat
```

### macOS

```bash
./run_macos.sh
```

### Linux

```bash
./run_linux.sh
```

---

# Primeiro Uso

1. Coloca o teu ficheiro `.wvd` em:

```text
secrets/
```

2. Inicia a aplicação.
3. Vai à aba `CONFIG`.
4. Confirma o caminho do Chrome.
5. Mantém o perfil Chrome como `chrome-debug-profile`.
6. Abre o Chrome através da aplicação.
7. Faz login na tua conta SIC OPTO.
8. Regressa à aba `DOWNLOAD`.

---

# Utilização

## Episódio

Cola uma URL de episódio:

```text
https://opto.sic.pt/vod/nome-do-episodio/uuid
```

Escolhe a qualidade e a pasta de destino.

Clica em:

```text
INICIAR DOWNLOAD
```

## Série

Cola uma URL de série:

```text
https://opto.sic.pt/series/nome-da-serie/uuid
```

Clica em:

```text
SÉRIE
```

Seleciona os episódios pretendidos e confirma.

### Notas

* `CANCELAR SCRAPE` interrompe a listagem.
* Episódios já descarregados aparecem assinalados.
* Cache: `state/sic_opto_cache.json`
* Histórico: `state/sic_opto_downloads.json`

---

# Estrutura do Projeto

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
├── README.md
├── config/
├── state/
├── secrets/
├── vendor/
└── chrome-debug-profile/
```

---

# Configuração

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

---

# Dependências

O instalador tenta preparar automaticamente:

* yt-dlp
* requests
* pywidevine
* selenium
* websocket-client
* ffmpeg
* ffprobe
* mp4decrypt
* uBlock Origin Lite

Dependendo do sistema operativo, algumas dependências podem exigir permissões de administrador.

---

# Problemas Comuns

## `.wvd não encontrado`

Coloca o ficheiro `.wvd` dentro da pasta:

```text
secrets/
```

---

## Chrome não respondeu

Verifica que:

* o caminho do Chrome está correto;
* não existem múltiplas instâncias conflitantes;
* o perfil Chrome não está bloqueado por outro processo.

---

## MPD não obtido

Confirma que:

* tens sessão iniciada na SIC OPTO;
* consegues reproduzir o conteúdo no browser;
* a conta possui acesso ao conteúdo.

---

## ffmpeg, ffprobe ou mp4decrypt em falta

Executa novamente o instalador da tua plataforma.

---

## Ficheiro `.invalid.mp4`

A validação final detetou um ficheiro inválido.

Confirma:

* acesso ao conteúdo;
* configuração do ambiente;
* validade do ficheiro `.wvd`;
* disponibilidade dos recursos necessários durante o processo.

---

# Desenvolvimento

Verificar sintaxe:

```bash
python -m py_compile v3.py instalar_dependencias.py
```

Instalação manual:

```bash
python instalar_dependencias.py
```

Execução manual:

```bash
python v3.py
```

---

# Segurança

Não partilhes:

```text
.venv/
chrome-debug-profile/
secrets/
state/
vendor/
downloads/
```

Também não deves partilhar:

* ficheiros `.wvd`;
* cookies;
* perfis Chrome;
* credenciais;
* chaves privadas;
* conteúdos descarregados.

O `.gitignore` já exclui estes caminhos do repositório.

---

# Apoiar o Projeto

Este projeto é desenvolvido e mantido em tempo livre.

Se te foi útil e quiseres apoiar o desenvolvimento:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/miguelmaster12)

---

# Contribuições

Melhorias são bem-vindas, especialmente em:

* instalação multiplataforma;
* robustez do scraping;
* tratamento de erros;
* experiência de utilização;
* documentação;
* organização do código.

Por favor, não abras issues ou pull requests contendo:

* conteúdos protegidos;
* credenciais;
* cookies;
* ficheiros `.wvd`;
* chaves privadas;
* ficheiros descarregados.

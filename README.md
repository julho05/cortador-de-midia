# ✂ Cortador de Mídia

Programa para Windows que corta trechos de áudio e vídeo em poucos cliques, com interface simples em português.
Feito para quem precisa cortar gravações no dia a dia sem instalar nem aprender editores complexos.

## Funcionalidades

- Corta **áudio** (MP3, WAV, M4A, FLAC, OGG...) e **vídeo** (MP4, MOV, MKV, AVI...)
- Início e fim no formato `59:31` ou `1:02:03`, com a duração do corte calculada na hora
- Saída em MP3, WAV, M4A, MP4, no formato original, ou extrair só o áudio de um vídeo
- **Corte preciso** para vídeo (recodifica) ou **corte rápido** (sem recodificar)
- Escolha do nome do arquivo final, sem sobrescrever arquivos existentes
- Barra de progresso e botão para abrir a pasta do arquivo gerado
- Tema claro/escuro acompanhando o Windows
- Executável único: o ffmpeg já vai embutido, não precisa instalar nada

## Como usar

1. Abra o `CortadorDeMidia.exe`
2. Clique em **Escolher arquivo**
3. Informe o **Início** e o **Fim** do trecho que vai ficar
4. Escolha o formato e o nome do arquivo
5. Clique em **Cortar**

O arquivo é salvo na mesma pasta do original, que nunca é alterado.

## Rodando pelo código

Requer Python 3.10+.

```bash
pip install -r requirements.txt
python cortador.py
```

## Gerando o executável

```bash
pip install -r requirements.txt
build.bat
```

O executável é criado em `dist\CortadorDeMidia.exe`.

## Tecnologias

- [Python](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — interface
- [FFmpeg](https://ffmpeg.org/) via [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) — processamento de mídia
- [PyInstaller](https://pyinstaller.org/) — empacotamento em `.exe`

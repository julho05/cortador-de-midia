"""Cortador de Mídia - corta trechos de áudio e vídeo usando ffmpeg."""
import os
import re
import subprocess
import sys
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".wma", ".opus"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m4v", ".webm", ".flv", ".mpg", ".mpeg"}

FORMATOS_AUDIO = ["MP3", "WAV", "M4A", "Original"]
FORMATOS_VIDEO = ["MP4", "Original", "Só áudio (MP3)"]

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# cores (claro, escuro)
COR_FUNDO = ("#F3F4F8", "#16171D")
COR_CARTAO = ("#FFFFFF", "#21232B")
COR_BORDA = ("#E3E5EC", "#2E313B")
COR_SEGMENTO = ("#EEEFF4", "#2A2C35")
COR_TEXTO = ("#1D1F27", "#ECEDF2")
COR_SUAVE = ("#6B7080", "#9095A5")
COR_DESTAQUE = ("#5B5BD6", "#7C7CF0")
COR_DESTAQUE_HOVER = ("#4A4AC4", "#6A6AE0")
COR_SUCESSO = ("#1E9E63", "#3CCB8A")
COR_ERRO = ("#D14343", "#F06C6C")


def caminho_ffmpeg():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "ffmpeg.exe")
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ler_tempo(texto):
    """Converte '59:31', '1:02:03', '3571' ou '59:31,5' em segundos."""
    texto = texto.strip().replace(",", ".")
    if not texto:
        raise ValueError("vazio")
    partes = texto.split(":")
    if len(partes) > 3:
        raise ValueError(texto)
    segundos = 0.0
    for p in partes:
        segundos = segundos * 60 + float(p)
    if segundos < 0:
        raise ValueError(texto)
    return segundos


def formatar_tempo(seg):
    seg = max(0, seg)
    h, resto = divmod(int(round(seg)), 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def obter_duracao(ffmpeg, arquivo):
    proc = subprocess.run([ffmpeg, "-hide_banner", "-i", arquivo],
                          capture_output=True, text=True, errors="replace",
                          creationflags=NO_WINDOW)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not m:
        return None
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def limpar_nome(nome):
    """Remove caracteres que o Windows não aceita em nome de arquivo."""
    nome = re.sub(r'[\\/:*?"<>|]', "", nome).strip().rstrip(".")
    return nome


def nome_saida(entrada, nome, ext):
    pasta = os.path.dirname(entrada)
    nome = limpar_nome(nome) or os.path.splitext(os.path.basename(entrada))[0] + "_cortado"
    destino = os.path.join(pasta, nome + ext)
    n = 2
    while os.path.exists(destino):
        destino = os.path.join(pasta, f"{nome}_{n}{ext}")
        n += 1
    return destino


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=COR_FUNDO)
        self.title("Cortador de Mídia")
        self.resizable(False, False)
        # fixa a largura; a altura acompanha o conteúdo
        ctk.CTkFrame(self, width=560, height=1, fg_color="transparent").pack()
        self.ffmpeg = caminho_ffmpeg()
        self.arquivo = None
        self.duracao = None
        self.eh_video = False
        self.processo = None
        self.ultima_saida = None

        fonte = lambda tam, peso="normal": ctk.CTkFont(family="Segoe UI", size=tam, weight=peso)

        # Cabeçalho
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=28, pady=(24, 16))
        ctk.CTkLabel(topo, text="✂  Cortador de Mídia", font=fonte(24, "bold"),
                     text_color=COR_TEXTO).pack(anchor="w")
        ctk.CTkLabel(topo, text="Corte trechos de áudio e vídeo em poucos cliques",
                     font=fonte(13), text_color=COR_SUAVE).pack(anchor="w")

        # Cartão: arquivo
        cartao_arq = self.cartao()
        self.secao(cartao_arq, "1", "Arquivo")
        linha = ctk.CTkFrame(cartao_arq, fg_color="transparent")
        linha.pack(fill="x", padx=18, pady=(4, 16))
        info = ctk.CTkFrame(linha, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        self.lbl_arquivo = ctk.CTkLabel(info, text="Nenhum arquivo selecionado", anchor="w",
                                        font=fonte(14, "bold"), text_color=COR_TEXTO)
        self.lbl_arquivo.pack(anchor="w")
        self.lbl_duracao = ctk.CTkLabel(info, text="Áudio ou vídeo: MP3, WAV, MP4, MOV...",
                                        anchor="w", font=fonte(12), text_color=COR_SUAVE)
        self.lbl_duracao.pack(anchor="w")
        ctk.CTkButton(linha, text="Escolher arquivo", width=140, height=38, corner_radius=10,
                      font=fonte(13, "bold"), fg_color=COR_DESTAQUE, hover_color=COR_DESTAQUE_HOVER,
                      command=self.escolher).pack(side="right")

        # Cartão: trecho
        cartao_tempo = self.cartao()
        self.secao(cartao_tempo, "2", "Trecho que vai ficar")
        tempos = ctk.CTkFrame(cartao_tempo, fg_color="transparent")
        tempos.pack(fill="x", padx=18, pady=(4, 4))
        tempos.grid_columnconfigure((0, 1, 2), weight=1, uniform="t")
        self.var_inicio = ctk.StringVar(value="0:00")
        self.var_fim = ctk.StringVar()
        self.campo_tempo(tempos, 0, "Início", self.var_inicio, fonte)
        self.campo_tempo(tempos, 1, "Fim", self.var_fim, fonte)
        caixa_res = ctk.CTkFrame(tempos, fg_color="transparent")
        caixa_res.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(caixa_res, text="Resultado", font=fonte(12), text_color=COR_SUAVE).pack(anchor="w")
        self.lbl_resultado = ctk.CTkLabel(caixa_res, text="—", font=fonte(22, "bold"),
                                          text_color=COR_DESTAQUE, height=40)
        self.lbl_resultado.pack(anchor="w")
        ctk.CTkLabel(cartao_tempo, text="Use minutos:segundos (59:31) ou horas:minutos:segundos (1:02:03)",
                     font=fonte(11), text_color=COR_SUAVE).pack(anchor="w", padx=18, pady=(0, 14))
        self.var_inicio.trace_add("write", lambda *_: self.atualizar_resultado())
        self.var_fim.trace_add("write", lambda *_: self.atualizar_resultado())

        # Cartão: formato
        cartao_fmt = self.cartao()
        self.secao(cartao_fmt, "3", "Salvar como")
        self.var_formato = ctk.StringVar(value=FORMATOS_AUDIO[0])
        self.seg_formato = ctk.CTkFrame(cartao_fmt, fg_color=COR_SEGMENTO, corner_radius=10)
        self.seg_formato.pack(fill="x", padx=18, pady=(4, 12))
        ctk.CTkLabel(cartao_fmt, text="Nome do arquivo", font=fonte(12),
                     text_color=COR_SUAVE).pack(anchor="w", padx=18)
        self.linha_nome = ctk.CTkFrame(cartao_fmt, fg_color="transparent")
        self.linha_nome.pack(fill="x", padx=18, pady=(0, 16))
        self.var_nome = ctk.StringVar()
        ctk.CTkEntry(self.linha_nome, textvariable=self.var_nome, height=36, corner_radius=10,
                     font=fonte(13), border_color=COR_BORDA,
                     placeholder_text="ex.: reuniao_cortada").pack(side="left", fill="x", expand=True)
        self.lbl_ext = ctk.CTkLabel(self.linha_nome, text=".mp3", width=50, font=fonte(13, "bold"),
                                    text_color=COR_SUAVE)
        self.lbl_ext.pack(side="right", padx=(8, 0))
        self.botoes_formato = []
        self.montar_formatos(FORMATOS_AUDIO)
        self.var_preciso = ctk.BooleanVar(value=True)
        self.sw_preciso = ctk.CTkSwitch(
            cartao_fmt, text="Corte preciso no vídeo (mais lento)", variable=self.var_preciso,
            font=fonte(12), text_color=COR_TEXTO, progress_color=COR_DESTAQUE)

        # Rodapé: progresso e botões
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=28, pady=(6, 20))
        self.barra = ctk.CTkProgressBar(rodape, height=8, corner_radius=4, fg_color=COR_BORDA,
                                        progress_color=COR_BORDA)
        self.barra.set(0)
        self.barra.pack(fill="x", pady=(0, 8))
        self.lbl_status = ctk.CTkLabel(rodape, text="Escolha um arquivo para começar.",
                                       font=fonte(12), text_color=COR_SUAVE)
        self.lbl_status.pack(anchor="w", pady=(0, 10))
        botoes = ctk.CTkFrame(rodape, fg_color="transparent")
        botoes.pack(fill="x")
        self.btn_cortar = ctk.CTkButton(
            botoes, text="Cortar", height=46, corner_radius=12, font=fonte(15, "bold"),
            fg_color=COR_DESTAQUE, hover_color=COR_DESTAQUE_HOVER, command=self.cortar)
        self.btn_cortar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.btn_pasta = ctk.CTkButton(
            botoes, text="Abrir pasta", width=130, height=46, corner_radius=12, font=fonte(13),
            fg_color="transparent", border_width=1, border_color=COR_BORDA, text_color=COR_TEXTO,
            hover_color=COR_BORDA, command=self.abrir_pasta, state="disabled")
        self.btn_pasta.pack(side="right")
        self.ativar_cortar(False)

        self.protocol("WM_DELETE_WINDOW", self.fechar)

    def cartao(self):
        frame = ctk.CTkFrame(self, fg_color=COR_CARTAO, corner_radius=14,
                             border_width=1, border_color=COR_BORDA)
        frame.pack(fill="x", padx=28, pady=6)
        return frame

    def secao(self, pai, numero, titulo):
        linha = ctk.CTkFrame(pai, fg_color="transparent")
        linha.pack(fill="x", padx=18, pady=(14, 4))
        ctk.CTkLabel(linha, text=numero, width=22, height=22, corner_radius=11,
                     fg_color=COR_DESTAQUE, text_color="#FFFFFF",
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(side="left")
        ctk.CTkLabel(linha, text=titulo, text_color=COR_TEXTO,
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left", padx=8)

    def campo_tempo(self, pai, coluna, rotulo, variavel, fonte):
        caixa = ctk.CTkFrame(pai, fg_color="transparent")
        caixa.grid(row=0, column=coluna, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(caixa, text=rotulo, font=fonte(12), text_color=COR_SUAVE).pack(anchor="w")
        ctk.CTkEntry(caixa, textvariable=variavel, height=40, corner_radius=10, justify="center",
                     font=fonte(18, "bold"), border_color=COR_BORDA).pack(fill="x")

    def montar_formatos(self, formatos):
        for b in self.botoes_formato:
            b.destroy()
        self.botoes_formato = []
        for i, nome in enumerate(formatos):
            b = ctk.CTkButton(self.seg_formato, text=nome, width=60, height=32, corner_radius=8,
                              font=ctk.CTkFont(family="Segoe UI", size=13),
                              command=lambda n=nome: self.selecionar_formato(n))
            b.grid(row=0, column=i, sticky="ew", padx=3, pady=3)
            self.seg_formato.grid_columnconfigure(i, weight=1, uniform="f")
            self.botoes_formato.append(b)
        for i in range(len(formatos), 6):
            self.seg_formato.grid_columnconfigure(i, weight=0, uniform="")
        self.selecionar_formato(formatos[0])

    def selecionar_formato(self, nome):
        self.var_formato.set(nome)
        for b in self.botoes_formato:
            if b.cget("text") == nome:
                b.configure(fg_color=COR_DESTAQUE, hover_color=COR_DESTAQUE_HOVER, text_color="#FFFFFF")
            else:
                b.configure(fg_color="transparent", hover_color=COR_BORDA, text_color=COR_TEXTO)
        if self.arquivo:
            self.lbl_ext.configure(text=self.extensao())

    def ativar_cortar(self, ativo, texto="Cortar"):
        self.btn_cortar.configure(state="normal" if ativo else "disabled", text=texto,
                                  fg_color=COR_DESTAQUE if ativo else COR_BORDA)

    def status(self, texto, cor=COR_SUAVE):
        self.lbl_status.configure(text=texto, text_color=cor)

    def escolher(self):
        exts = " ".join(f"*{e}" for e in sorted(AUDIO_EXT | VIDEO_EXT))
        arquivo = filedialog.askopenfilename(
            title="Escolha o áudio ou vídeo",
            filetypes=[("Áudio e vídeo", exts), ("Todos os arquivos", "*.*")])
        if not arquivo:
            return
        duracao = obter_duracao(self.ffmpeg, arquivo)
        if duracao is None:
            messagebox.showerror("Cortador de Mídia", "Não consegui ler esse arquivo.")
            return
        self.arquivo, self.duracao = arquivo, duracao
        self.eh_video = os.path.splitext(arquivo)[1].lower() in VIDEO_EXT
        self.var_nome.set(os.path.splitext(os.path.basename(arquivo))[0] + "_cortado")
        nome = os.path.basename(arquivo)
        self.lbl_arquivo.configure(text=nome if len(nome) <= 36 else nome[:33] + "...")
        tipo = "🎬  Vídeo" if self.eh_video else "🎵  Áudio"
        self.lbl_duracao.configure(text=f"{tipo}  ·  duração {formatar_tempo(duracao)}")
        self.montar_formatos(FORMATOS_VIDEO if self.eh_video else FORMATOS_AUDIO)
        if self.eh_video:
            self.linha_nome.pack_configure(pady=(0, 10))
            self.sw_preciso.pack(anchor="w", padx=18, pady=(0, 14))
        else:
            self.linha_nome.pack_configure(pady=(0, 16))
            self.sw_preciso.pack_forget()
        self.var_inicio.set("0:00")
        self.var_fim.set(formatar_tempo(duracao))
        self.ativar_cortar(True)
        self.btn_pasta.configure(state="disabled")
        self.barra.set(0)
        self.barra.configure(progress_color=COR_BORDA)
        self.status("Informe o início e o fim e clique em Cortar.")

    def intervalo(self):
        inicio = ler_tempo(self.var_inicio.get())
        fim = ler_tempo(self.var_fim.get())
        if fim <= inicio:
            raise ValueError("O fim precisa ser depois do início.")
        if self.duracao and inicio >= self.duracao:
            raise ValueError("O início passa do fim do arquivo.")
        return inicio, min(fim, self.duracao or fim)

    def atualizar_resultado(self):
        try:
            inicio, fim = self.intervalo()
            self.lbl_resultado.configure(text=formatar_tempo(fim - inicio))
        except ValueError:
            self.lbl_resultado.configure(text="—")

    def extensao(self):
        formato = self.var_formato.get()
        if "MP3" in formato:
            return ".mp3"
        if formato in ("WAV", "M4A", "MP4"):
            return "." + formato.lower()
        return os.path.splitext(self.arquivo)[1].lower()

    def montar_comando(self, inicio, fim):
        formato = self.var_formato.get()
        ext = self.extensao()
        cmd = [self.ffmpeg, "-hide_banner", "-nostats", "-progress", "pipe:1",
               "-ss", f"{inicio:.3f}", "-i", self.arquivo, "-t", f"{fim - inicio:.3f}"]

        if "MP3" in formato:
            codec = ["-vn", "-c:a", "libmp3lame", "-b:a", "128k"]
        elif formato == "WAV":
            codec = ["-vn", "-c:a", "pcm_s16le"]
        elif formato == "M4A":
            codec = ["-vn", "-c:a", "aac", "-b:a", "160k"]
        elif formato == "MP4":
            if self.var_preciso.get():
                codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                         "-c:a", "aac", "-b:a", "160k"]
            else:
                codec = ["-c", "copy"]
        else:  # Original
            if self.eh_video and self.var_preciso.get():
                codec = []  # ffmpeg escolhe os codecs padrão do formato
            else:
                codec = ["-c", "copy"]

        saida = nome_saida(self.arquivo, self.var_nome.get(), ext)
        return cmd + codec + ["-n", saida], saida

    def cortar(self):
        try:
            inicio, fim = self.intervalo()
        except ValueError as e:
            messagebox.showwarning("Cortador de Mídia",
                                   f"Tempo inválido. Use o formato 59:31 ou 1:02:03.\n\n{e}")
            return
        cmd, saida = self.montar_comando(inicio, fim)
        self.ativar_cortar(False, "Cortando...")
        self.btn_pasta.configure(state="disabled")
        self.barra.set(0)
        self.barra.configure(progress_color=COR_DESTAQUE)
        self.status("Cortando... 0%")
        threading.Thread(target=self.executar, args=(cmd, saida, fim - inicio), daemon=True).start()

    def executar(self, cmd, saida, total):
        erro = []
        try:
            self.processo = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                text=True, errors="replace", creationflags=NO_WINDOW)
            threading.Thread(target=lambda: erro.extend(self.processo.stderr), daemon=True).start()
            for linha in self.processo.stdout:
                if linha.startswith("out_time_us="):
                    try:
                        feito = int(linha.split("=")[1]) / 1_000_000
                    except ValueError:
                        continue
                    pct = min(100, feito / total * 100) if total else 0
                    self.after(0, self.progresso, pct)
            codigo = self.processo.wait()
        except OSError as e:
            codigo, erro = -1, [str(e)]
        self.after(0, self.concluido, codigo, saida, "".join(erro[-15:]))

    def progresso(self, pct):
        self.barra.set(pct / 100)
        self.status(f"Cortando... {pct:.0f}%")

    def concluido(self, codigo, saida, erro):
        self.processo = None
        self.ativar_cortar(True)
        if codigo == 0:
            self.barra.configure(progress_color=COR_SUCESSO)
            self.barra.set(1)
            self.ultima_saida = saida
            self.btn_pasta.configure(state="normal")
            self.status(f"✓  Pronto! Salvo como {os.path.basename(saida)}", COR_SUCESSO)
        else:
            self.barra.set(0)
            self.status("✕  Deu erro no corte.", COR_ERRO)
            if os.path.exists(saida):
                try:
                    os.remove(saida)
                except OSError:
                    pass
            messagebox.showerror("Cortador de Mídia", f"Não foi possível cortar o arquivo.\n\n{erro}")

    def abrir_pasta(self):
        if self.ultima_saida and os.path.exists(self.ultima_saida):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self.ultima_saida)])

    def fechar(self):
        if self.processo and self.processo.poll() is None:
            if not messagebox.askyesno("Cortador de Mídia", "Um corte está em andamento. Cancelar e sair?"):
                return
            self.processo.kill()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("system")
    App().mainloop()

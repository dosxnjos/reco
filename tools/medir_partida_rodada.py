"""Bloco B do tools/medir_partida.py: --descobrir e --rodadas (passos 10 a 12 da
Fase 0 do roadmap 2026-11-11-melhoria-reco-em-rust).

Só roda com NENHUM Reco.exe aberto (código 3): com o mutex, o exe novo sairia em
milissegundos e mediria o Reco.Show (reco.py:5201-5211). Cada instância de teste
abre com HF_HUB_OFFLINE=1 só no ambiente do Popen (a checagem de modelo novo falha
calada), é encerrada pelo pid que a ferramenta abriu, e o MP3 dela vai para
temp/medicoes/ (mover é reversível; nada se apaga).
"""
import json
import os
import shutil
import subprocess
import threading
import time

import medir_partida as mp
import medir_partida_win as w

JANELA_LIMITE_S = 60
TOCAR_S = 15


def _abrir_teste() -> subprocess.Popen:
    env = dict(os.environ, HF_HUB_OFFLINE="1")
    return subprocess.Popen([str(mp.EXE)], cwd=mp.EXE.parent, env=env)


def _encerrar(proc: subprocess.Popen) -> None:
    """TerminateProcess só no processo de teste que esta ferramenta abriu."""
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        pass


def _esperar(cond, limite_s: float, passo: float = 0.02):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < limite_s:
        v = cond()
        if v:
            return v
        time.sleep(passo)
    return None


def _recusa_se_aberto() -> int:
    pid = mp.reco_aberto()
    if pid is None:
        return 0
    print(f"Reco já aberto (pid {pid}): o Sair pela bandeja vem antes (passo 9)")
    return 3


def _n_botoes(hwnd, n: int):
    bts = w.botoes_visiveis(hwnd)
    return bts if len(bts) == n else None


# ── passo 10 ────────────────────────────────────────────────────────────────────
def descobrir(_a) -> int:
    if cod := _recusa_se_aberto():
        return cod
    w.dpi_fisico()
    proc = _abrir_teste()
    try:
        hwnd = _esperar(lambda: w.achar_janela(proc.pid), JANELA_LIMITE_S)
        if hwnd is None:
            print(f"janela=nenhuma em {JANELA_LIMITE_S} s; janelas visíveis do pid: "
                  f"{w.janelas_do_pid(proc.pid)}")
            return 7
        bts = _esperar(lambda: w.botoes_visiveis(hwnd), 15) or []
        gravar = ",".join(map(str, bts[0][1])) if bts else "nenhum"
        print(f"janela=TkTopLevel botoes_visiveis={len(bts)} gravar={gravar}")
        return 0 if bts else 7
    finally:
        _encerrar(proc)
        print(f"processo de teste {proc.pid} encerrado")


# ── passos 11 e 12 ──────────────────────────────────────────────────────────────
def _r3(v):
    return None if v is None else round(v, 3)


def _pronta_cond(hwnd):
    """Pronta = alfa 255, ou o Tk tirou o WS_EX_LAYERED depois de o fade começar."""
    viu = {"layered": False}

    def cond():
        layered, a = w.alfa(hwnd)
        if layered:
            viu["layered"] = True
            return "alfa_255" if a == 255 else None
        return "saiu_do_layered" if viu["layered"] else None

    return cond


def _abrir(r: dict, proc, t0: float):
    hwnd = _esperar(lambda: w.achar_janela(proc.pid), JANELA_LIMITE_S)
    if hwnd is None:
        raise RuntimeError(f"janela não apareceu em {JANELA_LIMITE_S} s; "
                           f"visíveis do pid: {w.janelas_do_pid(proc.pid)}")
    r["abrir_visivel_s"] = _r3(time.perf_counter() - t0)
    r["pronta_por"] = _esperar(_pronta_cond(hwnd), 10, 0.005)
    r["abrir_pronta_s"] = _r3(time.perf_counter() - t0) if r["pronta_por"] else None
    time.sleep(5)
    r["ram_repouso_mb"] = round(w.memoria_mb(proc.pid)[0], 1)
    return hwnd


def _tocar(som: dict, parar: threading.Event) -> None:
    """Ruído a −6 dBFS de pico, 48 kHz, no alto-falante padrão (test_gravacao_alinhada.py:79-85)."""
    try:
        import numpy as np
        import soundcard as sc
        x = np.random.default_rng().standard_normal(48000 * TOCAR_S).astype(np.float32)
        x = x / np.max(np.abs(x)) * 0.5
        with sc.default_speaker().player(samplerate=48000, channels=1, blocksize=2048) as pl:
            i = 0
            while not parar.is_set() and i < len(x):
                pl.play(x[i:i + 4800])
                i += 4800
        som["tocou"] = True
    except Exception as e:      # sem saída de áudio: a rodada segue, tocou=false
        som["erro_tocar"] = str(e)


def _ver_arquivo(o: dict, pasta, antes: set, el: float) -> None:
    novos = [p for p in pasta.glob("*_reco_*.mp3") if p.name not in antes]
    if novos:
        o["mp3"], o["criado"], o["tam0"] = novos[0], el, novos[0].stat().st_size


def _tick(o: dict, pid: int, hwnd, ctx: tuple, el: float) -> None:
    pasta, antes, segundos = ctx
    if o["ui"] is None and len(w.botoes_visiveis(hwnd)) == 2:      # Parar e Pausar
        o["ui"] = el
    if o["mp3"] is None:
        _ver_arquivo(o, pasta, antes, el)
    elif o["cresce"] is None and o["mp3"].stat().st_size > o["tam0"]:
        o["cresce"] = el
    if o["mp3"] is not None and not o["trava"]:
        o["trava"] = w.arquivo_preso(o["mp3"])
    if o["ram"] is None and el >= segundos - 2:
        o["ram"] = round(w.memoria_mb(pid)[0], 1)


def _observar(pid: int, hwnd, ctx: tuple, t_clique: float) -> dict:
    o = {"ui": None, "criado": None, "cresce": None, "trava": False, "ram": None,
         "mp3": None, "tam0": None}
    while (el := time.perf_counter() - t_clique) < ctx[2]:
        _tick(o, pid, hwnd, ctx, el)
        time.sleep(0.05)
    return o


def _registrar_gravacao(r: dict, o: dict, som: dict) -> None:
    r["clique_ui_gravando_s"] = _r3(o["ui"])
    r["clique_arquivo_criado_s"] = _r3(o["criado"])
    r["clique_mp3_cresce_s"] = _r3(o["cresce"])
    if o["cresce"] is None:
        r["nao_cresceu_em_s"] = r["segundos"]
    r["ram_gravando_mb"] = o["ram"]
    r["trava_detectada"] = o["trava"]
    r.update(som)
    if o["ui"] is None or o["criado"] is None:
        r["erro"] = "o clique em Gravar não pegou (sem Parar/Pausar ou sem MP3 novo)"


def _gravar(r: dict, proc, hwnd, ctx: tuple, tocar: bool) -> dict:
    bts = _esperar(lambda: _n_botoes(hwnd, 1), 15)
    if not bts:
        raise RuntimeError("repouso sem o botão Gravar visível (1 botão)")
    som, parar = {"tocou": False}, threading.Event()
    th = threading.Thread(target=_tocar, args=(som, parar), daemon=True)
    if tocar:
        th.start()
    t = w.clicar(bts[0][0], proc.pid, hwnd)
    o = _observar(proc.pid, hwnd, ctx, t)
    parar.set()
    if tocar:
        th.join(5)
    _registrar_gravacao(r, o, som)
    return o


def _primeira_vez(conds: dict, t0: float, limite_s: float) -> dict:
    res = dict.fromkeys(conds)
    while None in res.values() and (el := time.perf_counter() - t0) < limite_s:
        for k, cond in conds.items():
            if res[k] is None and cond():
                res[k] = _r3(el)
        time.sleep(0.05)
    return res


def _parar(r: dict, proc, hwnd, mp3) -> None:
    bts = w.botoes_visiveis(hwnd)
    if len(bts) != 2:       # sem Parar e Pausar, o clique cairia no Gravar de novo
        raise RuntimeError(f"estado não é gravando ({len(bts)} botões visíveis); Parar não clicado")
    t = w.clicar(bts[0][0], proc.pid, hwnd)      # Parar é o mais à esquerda (reco.py:3576-3580)
    r.update(_primeira_vez({
        "parar_arquivo_fechado_s": lambda: mp3 is not None and mp3.exists() and not w.arquivo_preso(mp3),
        "parar_ui_parado_s": lambda: len(w.botoes_visiveis(hwnd)) == 3,    # Salvar, Excluir, Reproduzir
    }, t, 30))


def _mover_um(p) -> bool:
    for _ in range(10):         # o processo morto pode demorar a soltar o handle
        try:
            shutil.move(str(p), str(mp.MEDICOES / p.name))
            return True
        except OSError:
            time.sleep(0.5)
    return False


def _mover(r: dict, pasta, antes: set) -> None:
    """Os MP3 que nasceram na rodada saem da pasta do usuário para temp/medicoes/.
    Nunca levanta: o que não sair fica em mp3_nao_movido, e as outras rodadas seguem."""
    for p in [p for p in pasta.glob("*_reco_*.mp3") if p.name not in antes]:
        chave = "mp3_movido" if _mover_um(p) else "mp3_nao_movido"
        r.setdefault(chave, []).append(f"temp/medicoes/{p.name}" if chave == "mp3_movido" else str(p))


def _uma_rodada(i: int, segundos: float, tocar: bool) -> dict:
    cfg = mp.ler_config()
    r = {"rodada": i, "primeira": i == 1, "segundos": segundos, "tocar": tocar,
         "config": {"live": cfg.get("live"), "device": cfg.get("device")},
         "checagem_modelo": "desligada (HF_HUB_OFFLINE=1)"}
    pasta = mp.pasta_saida()
    antes = {p.name for p in pasta.glob("*.mp3")}
    t0 = time.perf_counter()
    proc = _abrir_teste()
    try:
        hwnd = _abrir(r, proc, t0)
        o = _gravar(r, proc, hwnd, (pasta, antes, segundos), tocar)
        _parar(r, proc, hwnd, o["mp3"])
    except (RuntimeError, OSError) as e:
        r["erro"] = str(e)
    finally:
        _encerrar(proc)
        _mover(r, pasta, antes)
    return r


def rodadas(a) -> int:
    if cod := _recusa_se_aberto():
        return cod
    w.dpi_fisico()
    mp.MEDICOES.mkdir(parents=True, exist_ok=True)
    ruins = 0
    for i in range(1, a.rodadas + 1):
        r = _uma_rodada(i, a.segundos, a.tocar)
        linha = json.dumps(r, ensure_ascii=False)
        print(linha, flush=True)
        with open(mp.MEDICOES / "partida.jsonl", "a", encoding="utf-8") as f:
            f.write(linha + "\n")
        ruins += "erro" in r
        time.sleep(3)
    return 7 if ruins else 0

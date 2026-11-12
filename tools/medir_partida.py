"""Mede a partida do Reco de hoje, de fora do processo (Fase 0 do roadmap
2026-11-11-melhoria-reco-em-rust). Só ctypes + stdlib (F0-D1); nada entra no reco.py.

Modos (cada um uma função):
  --ram-viva                    memória e CPU do Reco.exe aberto (só lê)
  --imports [--pipeline]        tempo de processos que só importam (5x; pipeline 1x, GPU)
  --checar-gravando [--pasta]   gravação em curso pela trava do MP3 (código 4)
  --esperar-fechado [--so-esperar]  checa e espera o usuário dar Sair pela bandeja
  --descobrir                   abre um Reco de teste e acha o botão Gravar (HWND)
  --rodadas N --segundos S [--tocar]  partida, gravar e parar com clique real

Nunca fecha o Reco do usuário: --esperar-fechado só checa e espera o Sair; as
instâncias de teste (--descobrir, --rodadas) só rodam com nenhum Reco.exe aberto,
são encerradas pelo pid que a ferramenta abriu, e o MP3 de teste vai para
temp/medicoes/. Códigos: 0 ok, 2 Reco fechado/erro, 3 Reco já aberto,
4 gravação em curso, 5 espera estourou, 6 ocupado (CPU), 7 medição falhou.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import medir_partida_win as w

RAIZ = Path(__file__).resolve().parent.parent
EXE = RAIZ / "dist" / "Reco" / "Reco.exe"
MEDICOES = RAIZ / "temp" / "medicoes"
CONFIG = Path.home() / ".reco_config.json"
PID_SALVO = MEDICOES / "esperar_pid.txt"
JANELA_RECENTE_S = 6 * 3600


def ler_config() -> dict:
    """~/.reco_config.json só como JSON (sem importar o reco, sem gravar nada)."""
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pasta_saida() -> Path:
    """Como o reco.py:98-102 e 2869-2870: output_dir, ou Documents\\Reco se null."""
    d = ler_config().get("output_dir")
    return Path(d) if d else Path.home() / "Documents" / "Reco"


def travados(pasta: Path) -> list[Path]:
    """MP3 da pasta modificados nas últimas 6 h que algum processo segura aberto."""
    agora = time.time()
    recentes = [p for p in pasta.glob("*.mp3") if agora - p.stat().st_mtime < JANELA_RECENTE_S]
    return [p for p in recentes if w.arquivo_preso(p)]


def cpu_pct(pid: int, segundos: float) -> float | None:
    """CPU do processo em `segundos`, em % de um núcleo (GetProcessTimes)."""
    c0, t0 = w.cpu_s(pid), time.perf_counter()
    time.sleep(segundos)
    c1, t1 = w.cpu_s(pid), time.perf_counter()
    if c0 is None or c1 is None:
        return None
    return round((c1 - c0) / (t1 - t0) * 100, 1)


def reco_aberto() -> int | None:
    pids = w.pids_de("Reco.exe")
    return pids[0] if pids else None


# ── passo 2 ─────────────────────────────────────────────────────────────────────
def modo_ram_viva(_a) -> int:
    pid = reco_aberto()
    if pid is None:
        print("Reco não está aberto")
        return 2
    ws, priv = w.memoria_mb(pid)
    cpu = cpu_pct(pid, 5.0)
    print(json.dumps({"pid": pid, "ws_mb": round(ws, 1), "privado_mb": round(priv, 1),
                      "cpu_pct": cpu}))
    return 0 if ws > 0 else 2


# ── passo 3 ─────────────────────────────────────────────────────────────────────
_PIPELINE = """
import json, time, reco
t = time.perf_counter()
tr = reco.make_transcriber()
cfg = reco.load_config()
tr.set_model(cfg.get("model", reco._CFG_DEFAULTS["model"]))
tr.set_device("GPU")
tr._pipeline(None)
print("PIPELINE " + json.dumps({"s": time.perf_counter() - t, "modelo": tr._size,
                                "dispositivo": reco.resolve_device("GPU")}))
"""


def _medidas_import() -> dict:
    py = sys.executable
    return {"import_reco": [py, "-c", "import reco"],
            "import_openvino_genai": [py, "-c", "import openvino_genai"],
            "import_os_dois": [py, "-c", "import reco, openvino_genai"],
            "exe_selftest": [str(EXE), "--selftest"]}


def _cronometrar(cmd: list, vezes: int) -> dict:
    tempos, falhas = [], []
    for _ in range(vezes):
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, timeout=300)
        tempos.append(round(time.perf_counter() - t0, 3))
        if r.returncode != 0:
            falhas.append(r.returncode)
    resto = tempos[1:] or tempos
    return {"primeira_s": tempos[0], "mediana_s": round(statistics.median(resto), 3),
            "vezes_s": tempos, "codigos_ruins": falhas}


def _pipeline_gpu() -> dict:
    env = dict(os.environ, HF_HUB_OFFLINE="1")
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, "-c", _PIPELINE], cwd=RAIZ, env=env,
                       capture_output=True, text=True, timeout=600)
    parede = round(time.perf_counter() - t0, 3)
    linha = [x for x in r.stdout.splitlines() if x.startswith("PIPELINE ")]
    if r.returncode != 0 or not linha:
        return {"erro": (r.stderr or r.stdout)[-400:], "parede_s": parede}
    d = json.loads(linha[-1][len("PIPELINE "):])
    s = round(d.pop("s"), 3)
    return {"primeira_s": s, "mediana_s": s, "vezes": 1, "parede_com_import_s": parede, **d}


def _selftest_txt() -> str:
    p = Path(os.environ.get("TEMP", "."), "reco_selftest.txt")
    try:
        return p.read_text(encoding="utf-8").splitlines()[1]
    except (OSError, IndexError):
        return "sem reco_selftest.txt"


def modo_imports(a) -> int:
    saida = {nome: _cronometrar(cmd, 5) for nome, cmd in _medidas_import().items()}
    saida["exe_selftest"]["selftest"] = _selftest_txt()
    if a.pipeline:
        saida["pipeline_gpu"] = _pipeline_gpu()
    print(json.dumps(saida, ensure_ascii=False))
    ruins = [k for k, v in saida.items() if "erro" in v or v.get("codigos_ruins")]
    return 7 if ruins else 0


# ── passo 4 ─────────────────────────────────────────────────────────────────────
def modo_checar_gravando(a) -> int:
    pasta = Path(a.pasta) if a.pasta else pasta_saida()
    print(f"pasta={pasta}")
    if not pasta.is_dir():
        print("pasta não existe")
        return 2
    presos = travados(pasta)
    for p in presos:
        print(f"em curso: {p.name}")
    if presos:
        return 4
    print("nenhuma gravação em curso")
    return 0


# ── passo 9 ─────────────────────────────────────────────────────────────────────
def _checar_antes_de_sair(pid: int, limiar: float) -> int:
    pasta = pasta_saida()
    for rodada in (1, 2):
        presos = travados(pasta)
        if presos:
            print(f"gravação em curso: {presos[0].name}")
            return 4
        if rodada == 1:
            cpu = cpu_pct(pid, 25.0)        # > ALIGN_DESISTE_S = 20 (reco.py:1492)
            if cpu is None or cpu > limiar:
                print(f"ocupado: cpu={cpu}%")
                return 6
    return 0


def _esperar_sumir(pid: int, limite_s: float) -> int:
    t0 = time.perf_counter()
    while pid in w.pids_de("Reco.exe"):
        if time.perf_counter() - t0 > limite_s:
            print(f"ainda aberto após {limite_s / 60:.0f} min")
            return 5
        time.sleep(2)
    print(f"fechado pid {pid} em {time.perf_counter() - t0:.1f} s")
    return 0


def modo_esperar_fechado(a) -> int:
    pid = reco_aberto()
    if a.so_esperar:
        if pid is None and PID_SALVO.exists():
            pid = int(PID_SALVO.read_text(encoding="utf-8"))
        if pid is None:
            print("Reco não está aberto")
            return 2
        return _esperar_sumir(pid, a.limite_min * 60)
    if pid is None:
        print("Reco não está aberto")
        return 2
    cod = _checar_antes_de_sair(pid, a.limiar_cpu)
    if cod == 0:
        MEDICOES.mkdir(parents=True, exist_ok=True)
        PID_SALVO.write_text(str(pid), encoding="utf-8")
        print(f"pode sair (pid {pid})")
    return cod


# ── passos 10 a 12 (em medir_partida_rodada.py) ───────────────────────────────
def _rodada():
    # rodando como script, este módulo é __main__: o alias evita carregá-lo 2 vezes
    sys.modules.setdefault("medir_partida", sys.modules[__name__])
    import medir_partida_rodada
    return medir_partida_rodada


def modo_descobrir(a) -> int:
    return _rodada().descobrir(a)


def modo_rodadas(a) -> int:
    return _rodada().rodadas(a)


def argumentos(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ram-viva", action="store_true")
    g.add_argument("--imports", action="store_true")
    g.add_argument("--checar-gravando", action="store_true")
    g.add_argument("--esperar-fechado", action="store_true")
    g.add_argument("--descobrir", action="store_true")
    g.add_argument("--rodadas", type=int, metavar="N")
    ap.add_argument("--pipeline", action="store_true", help="com --imports: pipeline_gpu (1x)")
    ap.add_argument("--pasta", help="com --checar-gravando: outra pasta")
    ap.add_argument("--so-esperar", action="store_true", help="com --esperar-fechado")
    ap.add_argument("--limiar-cpu", type=float, default=10.0, help="%% de um núcleo (passo 9)")
    ap.add_argument("--limite-min", type=float, default=8.0, help="espera do --so-esperar")
    ap.add_argument("--segundos", type=float, default=35.0, help="com --rodadas")
    ap.add_argument("--tocar", action="store_true", help="com --rodadas: ruído −6 dBFS 15 s")
    return ap.parse_args(argv)


MODOS = [("ram_viva", modo_ram_viva), ("imports", modo_imports),
         ("checar_gravando", modo_checar_gravando), ("esperar_fechado", modo_esperar_fechado),
         ("descobrir", modo_descobrir), ("rodadas", modo_rodadas)]


def main(argv=None) -> int:
    a = argumentos(argv)
    for nome, fn in MODOS:
        if getattr(a, nome) not in (False, None):
            return fn(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())

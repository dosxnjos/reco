"""Primitivas Win32 (só ctypes) do tools/medir_partida.py.

Processo (pid por tasklist, memória, tempo de CPU), trava exclusiva de arquivo e,
para o Bloco B da Fase 0 do roadmap 2026-11-11-melhoria-reco-em-rust, janela Tk
por EnumWindows, botões nativos por EnumChildWindows, alfa do fade e clique real
por SendInput. Nada aqui fecha ou mexe no Reco aberto: só lê; o clique só sai se
o ponto pertence ao pid que a própria ferramenta abriu.
"""
import csv
import ctypes
import subprocess
import time
from ctypes import wintypes as wt

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

INVALID_HANDLE = ctypes.c_void_p(-1).value
ERROR_SHARING_VIOLATION = 32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x2
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
HWND_TOPMOST = wt.HWND(-1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
WS_EX_TOPMOST = 0x00000008
GA_ROOT = 2
SPI_GETWORKAREA = 0x0030


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CloseHandle.restype = wt.BOOL
k32.GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)] * 4
k32.GetProcessTimes.restype = wt.BOOL
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                            wt.DWORD, wt.DWORD, wt.HANDLE]
k32.CreateFileW.restype = wt.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wt.DWORD]
psapi.GetProcessMemoryInfo.restype = wt.BOOL
u32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
u32.EnumChildWindows.argtypes = [wt.HWND, WNDENUMPROC, wt.LPARAM]
u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
u32.GetWindowThreadProcessId.restype = wt.DWORD
u32.IsWindowVisible.argtypes = [wt.HWND]
u32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
u32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
u32.GetWindowLongW.restype = wt.LONG
u32.GetLayeredWindowAttributes.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD),
                                           ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(wt.DWORD)]
u32.WindowFromPoint.argtypes = [wt.POINT]
u32.WindowFromPoint.restype = wt.HWND
u32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
u32.GetAncestor.restype = wt.HWND
u32.SystemParametersInfoW.argtypes = [wt.UINT, wt.UINT, ctypes.c_void_p, wt.UINT]
u32.SetForegroundWindow.argtypes = [wt.HWND]
u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, wt.UINT]
u32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
u32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
u32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
u32.SendInput.restype = wt.UINT


# ── processo ────────────────────────────────────────────────────────────────────
def pids_de(imagem: str = "Reco.exe") -> list[int]:
    """pids pelo tasklist (saída localizada e em OEM: só vale linha cujo 1º campo é a imagem)."""
    r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {imagem}", "/FO", "CSV", "/NH"],
                       capture_output=True, timeout=30)
    texto = r.stdout.decode("mbcs", errors="replace")
    return [int(row[1]) for row in csv.reader(texto.splitlines())
            if len(row) > 1 and row[0].lower() == imagem.lower() and row[1].isdigit()]


def _abrir(pid: int):
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
    return h or k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)


def memoria_mb(pid: int) -> tuple[float, float]:
    """(working set, privado) em MB; (0, 0) se a chamada falhar."""
    h = _abrir(pid)
    if not h:
        return 0.0, 0.0
    try:
        pmc = PROCESS_MEMORY_COUNTERS_EX()
        pmc.cb = ctypes.sizeof(pmc)
        if not psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            return 0.0, 0.0
        return pmc.WorkingSetSize / 2**20, pmc.PrivateUsage / 2**20
    finally:
        k32.CloseHandle(h)


def cpu_s(pid: int) -> float | None:
    """Tempo de CPU acumulado (núcleo + usuário), em segundos; None se o processo sumiu."""
    h = _abrir(pid)
    if not h:
        return None
    try:
        ft = [wt.FILETIME() for _ in range(4)]
        if not k32.GetProcessTimes(h, *[ctypes.byref(f) for f in ft]):
            return None
        return sum((f.dwHighDateTime << 32 | f.dwLowDateTime) for f in ft[2:]) / 1e7
    finally:
        k32.CloseHandle(h)


# ── arquivo ─────────────────────────────────────────────────────────────────────
def arquivo_preso(caminho) -> bool:
    """True se outro processo segura o arquivo aberto (erro 32 no open exclusivo).
    O handle de teste fecha na hora: nunca segura o arquivo."""
    h = k32.CreateFileW(str(caminho), GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
    if h in (None, INVALID_HANDLE):
        return ctypes.get_last_error() == ERROR_SHARING_VIOLATION
    k32.CloseHandle(h)
    return False


# ── janela (Bloco B) ────────────────────────────────────────────────────────────
def dpi_fisico() -> None:
    """Coordenadas físicas em GetWindowRect/SetCursorPos (per-monitor v2)."""
    try:
        u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)


def _texto(fn, hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    fn(hwnd, buf, 256)
    return buf.value


def pid_da_janela(hwnd) -> int:
    pid = wt.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def retangulo(hwnd) -> tuple[int, int, int, int]:
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def achar_janela(pid: int, classe: str = "TkTopLevel", titulo: str = "Reco"):
    """HWND da janela de topo visível com essa classe e título, do pid; None se não há."""
    achou = []

    def cb(hwnd, _):
        if (u32.IsWindowVisible(hwnd) and pid_da_janela(hwnd) == pid
                and _texto(u32.GetClassNameW, hwnd) == classe
                and _texto(u32.GetWindowTextW, hwnd) == titulo):
            achou.append(hwnd)
            return False
        return True

    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return achou[0] if achou else None


def janelas_do_pid(pid: int) -> list[tuple[str, str]]:
    """[(classe, título)] das janelas de topo visíveis do pid: diagnóstico do --descobrir."""
    achou = []

    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and pid_da_janela(hwnd) == pid:
            achou.append((_texto(u32.GetClassNameW, hwnd), _texto(u32.GetWindowTextW, hwnd)))
        return True

    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return achou


def botoes_visiveis(hwnd) -> list:
    """[(hwnd, (x, y, w, h))] dos filhos de classe Button visíveis, da esquerda para a direita."""
    achou = []

    def cb(filho, _):
        if u32.IsWindowVisible(filho) and _texto(u32.GetClassNameW, filho) == "Button":
            achou.append((filho, retangulo(filho)))
        return True

    u32.EnumChildWindows(hwnd, WNDENUMPROC(cb), 0)
    return sorted(achou, key=lambda b: b[1][0])


def alfa(hwnd) -> tuple[bool, int | None]:
    """(layered?, alfa 0-255 ou None). O Tk pode tirar o WS_EX_LAYERED quando o alfa chega a 1.0."""
    if not u32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_LAYERED:
        return False, None
    key, a, flags = wt.DWORD(), ctypes.c_ubyte(), wt.DWORD()
    if not u32.GetLayeredWindowAttributes(hwnd, ctypes.byref(key), ctypes.byref(a), ctypes.byref(flags)):
        return True, None
    return True, (a.value if flags.value & LWA_ALPHA else 255)


def _ponto_do_pid(x: int, y: int, pid: int) -> bool:
    return pid_da_janela(u32.WindowFromPoint(wt.POINT(x, y))) == pid


def _trazer_para_frente(topo) -> None:
    """Só na janela de teste: SetForegroundWindow costuma falhar vindo de processo de
    fundo, então também a põe em TOPMOST sem ativar (NOMOVE|NOSIZE|NOACTIVATE)."""
    u32.SetForegroundWindow(topo)
    u32.SetWindowPos(topo, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    time.sleep(0.3)


def _centro(hwnd_botao) -> tuple[int, int]:
    x, y, w, h = retangulo(hwnd_botao)
    return x + w // 2, y + h // 2


def quem_cobre(x: int, y: int) -> str:
    """Classe, processo, topmost e retângulo da janela de topo no ponto (sem o título:
    o texto vai para o relatório de um repo público)."""
    raiz = u32.GetAncestor(u32.WindowFromPoint(wt.POINT(x, y)), GA_ROOT)
    pid = pid_da_janela(raiz)
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                       capture_output=True, timeout=30)
    linha = next(csv.reader(r.stdout.decode("mbcs", errors="replace").splitlines() or [""]), [""])
    topmost = bool(u32.GetWindowLongW(raiz, GWL_EXSTYLE) & WS_EX_TOPMOST)
    return (f"classe={_texto(u32.GetClassNameW, raiz)} processo={linha[0] or '?'} pid={pid} "
            f"topmost={topmost} rect={retangulo(raiz)}")


def _area_util() -> tuple[int, int, int, int]:
    r = wt.RECT()
    u32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0)
    return r.left, r.top, r.right, r.bottom


def _mover_para_livre(topo, hwnd_botao, pid: int) -> bool:
    """Leva a janela de teste (só ela) aos cantos da área útil até o botão ficar à mostra."""
    esq, cima, dir_, baixo = _area_util()
    _, _, w, h = retangulo(topo)
    for x, y in ((esq, cima), (dir_ - w, cima), (esq, baixo - h), (dir_ - w, baixo - h)):
        u32.SetWindowPos(topo, HWND_TOPMOST, x, y, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
        time.sleep(0.3)
        if _ponto_do_pid(*_centro(hwnd_botao), pid):
            return True
    return False


def liberar_ponto(hwnd_botao, pid: int, topo=None) -> str:
    """Garante que o centro do botão é do pid de teste: 'direto', 'topmost' ou 'movida'.
    Nunca mexe em janela de outro processo; se nada resolve, recusa (RuntimeError)
    dizendo quem cobre o ponto."""
    if _ponto_do_pid(*_centro(hwnd_botao), pid):
        return "direto"
    if topo:
        _trazer_para_frente(topo)
        if _ponto_do_pid(*_centro(hwnd_botao), pid):
            return "topmost"
        if _mover_para_livre(topo, hwnd_botao, pid):
            return "movida"
    cx, cy = _centro(hwnd_botao)
    raise RuntimeError(f"ponto {cx},{cy} coberto por outra janela ({quem_cobre(cx, cy)}); "
                       "clique recusado")


def clicar(hwnd_botao, pid: int, topo=None) -> float:
    """Clique esquerdo real no centro do botão; devolve o perf_counter do SendInput.
    Recusa (RuntimeError) se o ponto não for do pid aberto pela ferramenta: nunca
    clica em janela de outro processo. Quem chama lê o caminho em `clicar.via`."""
    clicar.via = liberar_ponto(hwnd_botao, pid, topo)
    cx, cy = _centro(hwnd_botao)
    antes = wt.POINT()
    u32.GetCursorPos(ctypes.byref(antes))
    u32.SetCursorPos(cx, cy)
    time.sleep(0.05)
    ev = (INPUT * 2)()
    ev[0].type = ev[1].type = 0     # INPUT_MOUSE
    ev[0].u.mi.dwFlags, ev[1].u.mi.dwFlags = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    enviados = u32.SendInput(2, ev, ctypes.sizeof(INPUT))
    t_clique = time.perf_counter()
    time.sleep(0.25)        # o clique é processado assíncrono: só depois devolve o cursor
    u32.SetCursorPos(antes.x, antes.y)
    if enviados != 2:
        raise RuntimeError(f"SendInput enviou {enviados} de 2 (erro {ctypes.get_last_error()})")
    return t_clique

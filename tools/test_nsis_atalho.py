"""Prova dos hooks do instalador (`app/src-tauri/windows/hooks.nsh`): a instalação silenciosa não deixa atalho na Área
de Trabalho (defeito 5 do teste real, passo 17 da Fase 3, 12/11/2026).

Não instala o Reco Novo nem toca a Área de Trabalho real: compila com o `makensis` do Tauri um instalador mínimo que
faz o que o template do Tauri faz no modo silencioso (`CreateOrUpdateDesktopShortcut` entre os hooks PREINSTALL e
POSTINSTALL), com o caminho do atalho trocado por um arquivo numa pasta temporária (`RECO_ATALHO_DESKTOP`), e roda com
`/S`. Casos:

- com os hooks e sem atalho antes → o atalho NÃO fica;
- com os hooks e um atalho que já existia → ele fica (não é desta instalação);
- controle sem os hooks → o atalho fica (o mínimo reproduz o defeito).

Também confere que o `tauri.conf.json` aponta para o arquivo de hooks e que os hooks desmarcam a caixa "criar atalho"
da página final (o `.nsi` mínimo não compila sem `MUI_FINISHPAGE_SHOWREADME_NOTCHECKED`).

Uso: python tools/test_nsis_atalho.py  →  última linha "nsis-atalho: falhas 0" (saída 0).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TAURI = RAIZ / "app" / "src-tauri"
HOOKS = TAURI / "windows" / "hooks.nsh"


def makensis() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "tauri" / "NSIS"
    for p in (base / "makensis.exe", base / "Bin" / "makensis.exe"):
        if p.is_file():
            return p
    achado = shutil.which("makensis")
    if achado:
        return Path(achado)
    raise SystemExit("makensis não encontrado (o tauri build baixa em %LOCALAPPDATA%\\tauri\\NSIS)")


def nsi(saida: Path, atalho: Path, com_hooks: bool) -> str:
    inclui = f'!include "{HOOKS}"' if com_hooks else ""
    exige = "!ifndef MUI_FINISHPAGE_SHOWREADME_NOTCHECKED\n  !error \"hooks sem a caixa desmarcada\"\n!endif" if com_hooks else ""
    return f"""Unicode true
!include LogicLib.nsh
!define PRODUCTNAME "RecoTesteAtalho"
!define RECO_ATALHO_DESKTOP "{atalho}"
{inclui}
{exige}
Var PassiveMode
OutFile "{saida}"
RequestExecutionLevel user
SilentInstall silent
Section Install
  StrCpy $PassiveMode 0
  !ifmacrodef NSIS_HOOK_PREINSTALL
    !insertmacro NSIS_HOOK_PREINSTALL
  !endif
  ; o que o template do Tauri faz com /S ou /P (installer.nsi, "Create desktop shortcut for silent and passive")
  ${{If}} $PassiveMode = 1
  ${{OrIf}} ${{Silent}}
    CreateShortcut "${{RECO_ATALHO_DESKTOP}}" "$SYSDIR\\notepad.exe"
  ${{EndIf}}
  !ifmacrodef NSIS_HOOK_POSTINSTALL
    !insertmacro NSIS_HOOK_POSTINSTALL
  !endif
SectionEnd
"""


def rodar(pasta: Path, nome: str, com_hooks: bool, atalho_antes: bool) -> bool:
    """Compila e roda o instalador mínimo com /S; devolve se o atalho existe no fim."""
    atalho = pasta / f"{nome}.lnk"
    exe, fonte = pasta / f"{nome}.exe", pasta / f"{nome}.nsi"
    fonte.write_text(nsi(exe, atalho, com_hooks), encoding="utf-8-sig")
    r = subprocess.run([str(makensis()), "/V2", str(fonte)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", check=False)
    if r.returncode != 0:
        raise SystemExit(f"makensis falhou ({nome}):\n{r.stdout[-1500:]}\n{r.stderr[-500:]}")
    if atalho_antes:
        atalho.write_bytes(b"atalho de antes")
    code = subprocess.run([str(exe), "/S"], check=False, timeout=60).returncode
    if code != 0:
        raise SystemExit(f"instalador mínimo {nome} saiu com {code}")
    return atalho.exists()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    falhas = 0

    def conferir(nome: str, ok: bool) -> None:
        nonlocal falhas
        print(("ok    " if ok else "FALHA ") + nome)
        falhas += 0 if ok else 1

    conf = json.loads((TAURI / "tauri.conf.json").read_text(encoding="utf-8"))
    hooks = conf["bundle"]["windows"]["nsis"].get("installerHooks")
    conferir("tauri.conf.json aponta installerHooks para windows/hooks.nsh",
             bool(hooks) and (TAURI / hooks).resolve() == HOOKS.resolve())
    pasta = Path(tempfile.mkdtemp(prefix="reco_nsis_"))
    try:
        conferir("com os hooks, /S sem atalho antes: nenhum atalho na Área de Trabalho",
                 not rodar(pasta, "com_hooks", True, False))
        conferir("com os hooks, /S com atalho de antes: o atalho de antes fica",
                 rodar(pasta, "ja_tinha", True, True))
        conferir("controle sem os hooks, /S: o atalho fica (o mínimo reproduz o defeito)",
                 rodar(pasta, "sem_hooks", False, False))
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    print(f"nsis-atalho: falhas {falhas}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())

"""Teste headless do motor do Reco (`engine/reco_engine`, contrato em docs/PROTOCOL.md).

Sobe o motor como o casco Tauri vai subir (JSON Lines por stdin/stdout, CREATE_NO_WINDOW) e confere o
contrato. Este arquivo só tem as flags e o despacho; as checagens moram em `tools/engine_checks_*.py`.

Uso (Git Bash, na raiz do repo):
    python tools/test_engine_protocol.py                    # padrão: protocolo, ready, ocioso, checagem do
                                                            # modelo, config, dispositivos, biblioteca, extras
    python tools/test_engine_protocol.py --exe engine/dist/reco-engine/reco-engine.exe   # idem, congelado
    python tools/test_engine_protocol.py --conferir-doc     # COMMANDS × tabela do PROTOCOL.md
    python tools/test_engine_protocol.py --transcrever <mp3 do Reco com fala>   # GPU, minutos
    python tools/test_engine_protocol.py --cli <mp3 do Reco com fala>           # CLIs --transcribe/--selftest
    python tools/test_engine_protocol.py --gravar 5 [--concluir] [--saida-real]  # GRAVA (app fechado)
    python tools/test_engine_protocol.py --eof 25           # D11: casco some no meio (GRAVA)
    --lixeira: na rodada padrão, exclui de verdade um item da biblioteca (vai para a Lixeira).

Os modos que gravam abortam se o Reco estiver aberto (mutex `Local\\Reco.SingleInstance`, D7) e tocam
`temp/bench-voz/clip10.wav` no alto-falante. O `~/.reco_config.json` real nunca é escrito: o motor roda
com `USERPROFILE` temporário e o teste confere o sha256 do real no fim.
"""
from __future__ import annotations

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from engine_harness import Falha, RealConfigGuard, check  # noqa: E402


def _args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", help="motor congelado (reco-engine.exe) no lugar do fonte")
    ap.add_argument("--conferir-doc", action="store_true")
    ap.add_argument("--transcrever", metavar="MP3")
    ap.add_argument("--cli", metavar="MP3")
    ap.add_argument("--gravar", type=float, metavar="S")
    ap.add_argument("--concluir", action="store_true")
    ap.add_argument("--saida-real", action="store_true")
    ap.add_argument("--eof", type=float, metavar="S")
    ap.add_argument("--lixeira", action="store_true")
    return ap.parse_args()


def _padrao(a, guard: RealConfigGuard) -> None:
    import engine_checks_config
    import engine_checks_lib
    import engine_checks_modelo
    import engine_checks_proto
    engine_checks_proto.run(a.exe)
    engine_checks_proto.run_shutdown_como_o_casco(a.exe)
    engine_checks_modelo.run_em_voo(a.exe)
    engine_checks_modelo.run_espera_vaga()
    engine_checks_modelo.run_troca_de_pasta()
    engine_checks_modelo.run_consulta_com_prazo()
    engine_checks_modelo.run_ao_vivo_solta_no_fim()
    engine_checks_config.run(guard, a.exe)
    engine_checks_lib.run_library(a.exe, a.lixeira)
    engine_checks_lib.run_extras(a.exe)


def _gravacao(a, guard: RealConfigGuard) -> None:
    import engine_checks_rec
    engine_checks_rec.guardas()            # mutex e clipe ANTES de subir motor ou tocar som
    if a.eof:
        engine_checks_rec.run_eof(a.eof, a.exe)
    if a.gravar and a.concluir:
        import engine_checks_conclude
        engine_checks_conclude.run(a.gravar, a.exe)
    elif a.gravar:
        engine_checks_rec.run_gravar(a.gravar, a.exe, a.saida_real)


def _dispatch(a, guard: RealConfigGuard) -> None:
    if a.conferir_doc:
        import engine_checks_proto
        engine_checks_proto.conferir_doc()
    if a.transcrever:
        import engine_checks_tr
        engine_checks_tr.run_transcrever(a.transcrever, a.exe)
    if a.cli:
        import engine_checks_tr
        engine_checks_tr.run_cli(a.cli, a.exe)
    if a.gravar or a.eof:
        _gravacao(a, guard)
    if not (a.conferir_doc or a.transcrever or a.cli or a.gravar or a.eof):
        _padrao(a, guard)


def main() -> int:
    a = _args()
    guard = RealConfigGuard()
    try:
        _dispatch(a, guard)
        check(guard.intact(), "o sha256 do ~/.reco_config.json real MUDOU")
    except Falha as e:
        print(f"FALHOU: {e}")
        return 1
    except KeyboardInterrupt:
        print("interrompido")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

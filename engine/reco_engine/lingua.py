"""Idioma do motor: os três aceitos (pt, en, pl) e o que cada ponto escolhe por `reco.LANG`.

Espelha o `reco.py` (polonês desde 15/11/2026, PR #7 de Toni Nowak): Whisper no idioma do app quando é pt ou pl,
senão en; resumo IA pelo `PROMPT_RESUMO` do idioma, com en de reserva; prefixo da nota `nota`/`notatka`/`note`.
Recebe o módulo `reco` por argumento (o `cli.py` não passa pelo `boot`).
"""
from __future__ import annotations

LANGS = ("pt", "en", "pl")
_NOTA_PREFIX = {"pt": "nota", "pl": "notatka"}


def whisper_lang(reco) -> str:
    return reco.LANG if reco.LANG in ("pt", "pl") else "en"


def prompt_resumo(reco) -> str:
    return reco.PROMPT_RESUMO.get(reco.LANG, reco.PROMPT_RESUMO["en"])


def nota_prefix(reco) -> str:
    return _NOTA_PREFIX.get(reco.LANG, "note")

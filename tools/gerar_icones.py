"""Rasteriza os SVGs Lucide (+ 2 SVGs próprios) em máscaras PNG para os
botões do Reco (roadmap/2026-08-12-icones-lucide.md).

Cada SVG vira um PNG branco-sobre-transparente (a máscara alfa) — é assim
que `_icon()` em reco.py consegue tingir com a cor do tema em runtime
(Image.new("RGBA", ..., cor).putalpha(mascara.getchannel("A"))).

`assets/icons_src/*.svg` é a fonte (versionada, dev-time); `assets/icons/*.png`
é a saída que entra no bundle do PyInstaller (reco.spec `datas`).

    python tools/gerar_icones.py

Precisa de `cairosvg` (só dependência de dev — nunca entra no .exe).
"""
import re
from pathlib import Path

import cairosvg

RAIZ = Path(__file__).resolve().parent.parent
ICONS_SRC = RAIZ / "assets" / "icons_src"
ICONS_OUT = RAIZ / "assets" / "icons"

# conceito -> (nome do SVG em assets/icons_src/, tamanho em px)
ACAO_20PX = {
    "pausar": ("pause", 20),
    "reproduzir": ("play", 20),
    "transcrever": ("zap", 20),
    "excluir": ("excluir", 20),
    "salvar": ("check", 20),
    "converter_mp3": ("music", 20),
}
INLINE_16PX = {
    "opcoes": ("settings", 16),
    "atualizar": ("refresh-cw", 16),
    "atalho": ("keyboard", 16),
    "nova_versao": ("nova-versao", 16),
    "escolher_arquivo": ("plus", 16),
}

# Exceção deliberada (ver "Exceção deliberada" no roadmap): Lucide não tem
# variante *fill* — gravar/parar usam círculo e quadrado sólidos, feitos à
# mão, mesmo pipeline de máscara dos demais.
SVG_PROPRIOS = {
    "gravar": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="8" fill="white"/></svg>',
        20,
    ),
    "parar": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect x="5" y="5" width="14" height="14" rx="2" fill="white"/></svg>',
        20,
    ),
}

_WHITE_STROKE = re.compile(r'stroke="currentColor"')


def _svg_para_mascara_branca(svg_texto):
    """Força stroke/fill para branco — a cor real entra em runtime via putalpha."""
    return _WHITE_STROKE.sub('stroke="white"', svg_texto)


def gerar():
    ICONS_OUT.mkdir(parents=True, exist_ok=True)
    gerados = []

    for conceito, (nome_svg, tamanho) in {**ACAO_20PX, **INLINE_16PX}.items():
        origem = ICONS_SRC / f"{nome_svg}.svg"
        svg_texto = _svg_para_mascara_branca(origem.read_text(encoding="utf-8"))
        destino = ICONS_OUT / f"{conceito}.png"
        cairosvg.svg2png(
            bytestring=svg_texto.encode("utf-8"),
            write_to=str(destino),
            output_width=tamanho,
            output_height=tamanho,
        )
        gerados.append(destino.name)

    for conceito, (svg_texto, tamanho) in SVG_PROPRIOS.items():
        destino = ICONS_OUT / f"{conceito}.png"
        cairosvg.svg2png(
            bytestring=svg_texto.encode("utf-8"),
            write_to=str(destino),
            output_width=tamanho,
            output_height=tamanho,
        )
        gerados.append(destino.name)

    print(f"{len(gerados)} PNGs gerados em {ICONS_OUT}:")
    for nome in sorted(gerados):
        print(f"  {nome}")


if __name__ == "__main__":
    gerar()

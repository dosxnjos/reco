"""Motor do Reco: servidor JSON Lines em volta do `reco.py` (contrato em docs/PROTOCOL.md).

Fase 2 do roadmap `roadmap/2026-11-11-melhoria-reco-em-rust.md`. O `reco.py` é importado sem mudar uma
linha; este pacote só reimplementa a orquestração que hoje mora nos métodos do `App` (Tk).
"""

# Acompanha a versão do casco (app/src-tauri/tauri.conf.json) a cada instalador: os dois saem juntos (docs/PROTOCOL.md).
__version__ = "0.3.0"

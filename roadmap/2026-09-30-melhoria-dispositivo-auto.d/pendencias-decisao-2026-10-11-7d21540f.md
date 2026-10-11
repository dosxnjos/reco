## Pendências de decisão (execução 2026-10-11)

Só o que é do Gabriel. As decisões técnicas da Fase 0 (limiar do alarme, pausa do
maestro, restauração do `dist/`) estão no relatório, em
[relatorio-fase-0-7d21540f.md](relatorio-fase-0-7d21540f.md).

### 1. Fechar o `Reco.exe` e rodar o build antes de reabrir (dono: gabriel)

- **O que travou:** o app do Gabriel está aberto desde 10/10 21:27 (pid 19760). O
  `build.ps1` desta fase falhou (`PermissionError: [WinError 5]` em
  `dist\Reco\_internal\av\audio\codeccontext.pyd`) e o PyInstaller, antes de falhar,
  **apagou 26 arquivos de `dist/Reco/_internal`** (ícones `assets/icons/*.png`,
  `.pyd` do `aiohttp`, `dist-info` do `attrs`, `av/audio/codeccontext.py/.pxd`).
  Conferido contra `build/reco/COLLECT-00.toc` e **restaurado** a partir das origens
  do próprio TOC (27 cópias; 0 faltando depois). O `dist/` está completo de novo,
  mas com origens de hoje, não bit a bit do build de 19/08.
- **Impacto:** nenhum comportamento muda no exe nesta fase (modo nota é inerte:
  `_start_nota` sem caller; pin e ferramenta não entram no exe).
- **Instrução em 1 linha para o Gabriel:** "antes de abrir o Reco de novo, fecha o
  que está aberto e roda `build.ps1` (ou espera a Fase 1 do Auto, que já faz isso)".
- **O que foi feito no lugar:** nada além da restauração. Não matei o processo (é o
  app em uso dele). A Fase 1.7 tenta o build; se o app ainda estiver aberto, devolve
  `[[ESPERANDO]]`.

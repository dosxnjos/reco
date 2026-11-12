---
titulo: Guardas por caminho do processo: o Medal casa com Reco e o Get-Process por Path demora segundos
data: 2026-11-12
---
**Sintoma:** (1) o guarda do passo 9 da Fase 4, `Get-Process | ? Path -like '*\Reco*\*'`, não vem vazio com todos os
Reco fechados: lista `MedalEncoder.exe` e `crashpad_handler.exe`. (2) No passo 15, `Get-Process | ? Path -eq $exe |
Stop-Process -Force` matou o casco aos 40 s de gravação e o MP3 saiu com 47 s, como se o motor tivesse demorado a ver
o stdin fechar.

**Causa:** (1) o `-like` não diferencia maiúsculas e o gravador do Medal mora em `…\Medal\recorder-<versão>\`, que casa
com `\Reco*\`. (2) o filtro lê o `Path` de todos os processos da máquina: levou 4,7 s numa máquina carregada, e o casco
seguiu gravando nesse tempo. O motor saiu 0,0 s depois de o casco morrer (medido à parte).

**O que fazer:** ler o caminho de cada linha antes de concluir "tem Reco aberto" (ou filtrar por nome `reco`/`Reco` e
pelo caminho exato); para medir D11, cronometrar a partir do fim do `Stop-Process` (ou matar pelo pid já conhecido) e
não atribuir ao motor os segundos do comando.

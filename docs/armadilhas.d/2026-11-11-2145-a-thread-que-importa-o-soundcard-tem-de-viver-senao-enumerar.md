---
titulo: A thread que importa o soundcard tem de viver, senão enumerar dispositivos volta vazio
data: 2026-11-11
---
**Sintoma:** num processo que faz o `import reco` (e portanto o `import soundcard`) numa thread de
trabalho que depois termina, `scan_device_state()` e `resolve_audio_device()` chamados de outra
thread devolvem listas vazias e padrão `None`, **sem exceção**. Só um `print` de
`Error 0x800401f0` (CO_E_NOTINITIALIZED) vai ao console. No motor (`engine/`), `devices.list`
respondia "0 mics, 0 saídas" numa máquina com mic e alto-falante.

**Causa:** o `soundcard` liga o COM do Windows na thread que o importa. Quando essa thread acaba, o
COM é desligado e as chamadas WASAPI das outras threads falham. No app Tk isso nunca aparece: quem
importa é a thread principal, que vive o processo inteiro. Medido na auditoria de 11/11/2026 e
reproduzido pela mutação do `boot.py` (thread do import terminando → `devices.list` vazio).

**O que fazer:** quem importar o `reco` fora da thread principal mantém essa thread viva enquanto o
processo usar áudio. O motor faz o import em `reco_engine/boot.py`, sinaliza o `ready` e deixa a
thread parada num `threading.Event().wait()` (daemon). A rodada padrão de
`tools/test_engine_protocol.py` reprova com "listas vazias (thread do COM?)" se isso regredir.

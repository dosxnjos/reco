---
titulo: `sounddevice`/PortAudio não serve para captura neste hardware (06/2026)
---
**Sintoma.** Antes do Reco existir, o motor de captura (então em
`C:\Dev\mp4wav\gravador.py`) usava `sounddevice`. Três defeitos, todos medidos
na máquina do Gabriel (Realtek + Intel Smart Sound, Win 11, Python 3.14,
sounddevice 0.5.5):

- **O mesmo microfone aparecia 2–4× na lista.** PortAudio expõe cada dispositivo
  físico uma vez por host API (MME, DirectSound, WASAPI, WDM-KS), com nomes
  ligeiramente diferentes — MME trunca em 31 caracteres, WDM-KS acrescenta
  `" 1 ()"`. Deduplicar por nome exato não resolve, porque os nomes divergem.
- **Alto-falante entrava na lista de microfones.** Endpoints de *render* do
  WDM-KS reportam `max_input_channels=2` — falso.
- **Nenhum dispositivo WDM-KS abre** (`PaErrorCode -9999`), incluindo a
  "Mixagem estéreo" que o código antigo escolhia para o áudio do sistema. A
  exceção era engolida no `_rec_sys` e a faixa do sistema saía **vazia, em
  silêncio, sem erro**.

**Causa raiz.** `sounddevice` 0.5.5 **não expõe loopback WASAPI**:
`WasapiSettings` não tem o kwarg `loopback`, e abrir um dispositivo de render
como `InputStream` dá "Invalid number of channels". Sem loopback, só sobrava o
Stereo Mix — que é justamente o que não abre.

**Por isso `soundcard`.** Usa WASAPI exclusivamente: uma entrada por endpoint
(sem duplicata, sem alto-falante virando microfone) e
`sc.get_microphone(speaker.id, include_loopback=True)` dá loopback de verdade,
sem depender de Stereo Mix. Persistir dispositivo pelo `.id` (estável, tipo
GUID) e exibir o `.name`. Capturar as duas fontes a 48000 Hz fixo (nativo aqui)
e reamostrar ao salvar. Os gravadores funcionam em thread daemon sem init
manual de COM.

⚠️ Isso vale ao considerar trocar a lib de captura: `sounddevice` é a escolha
óbvia e mais popular, e **já foi testada e reprovada** neste hardware. Não é
questão de gosto.

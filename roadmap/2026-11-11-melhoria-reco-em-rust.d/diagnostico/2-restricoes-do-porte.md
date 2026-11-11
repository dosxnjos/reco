# Restrições que um porte do Reco para Rust não pode quebrar

**O que foi lido.** Li inteiros: `docs/ARMADILHAS.md` (849/849 linhas), `docs/ARQUITETURA.md` (318), `CLAUDE.md`, o hub `cerebro/projetos/reco.md`, `docs/TOOLS.md` e os roadmaps de modularização (340/340) e dispositivo Auto (506/506). Do roadmap do salto (1312 linhas) li as partes §0–§3 até a Fase D, §5, §6.1–6.2, §7 e §8. Dos roadmaps antieco, ao vivo, modo nota e Mac/Meet li o esqueleto e as seções de estado e fases abertas, não o texto inteiro. As linhas de `reco.py` citadas abaixo vêm do meu próprio grep no HEAD `7c5c1a1`. Os números de linha dos roadmaps estão deslocados.

## (1)+(2) Conquistas a preservar e defeitos que não podem virar régua

### A. Conquistas medidas

| comportamento | número medido / onde | preso a lib Python? |
|---|---|---|
| Formato fixo: 16 kHz estéreo, L=mic, R=sistema, 96 kbps ABR | `reco.py:148-150`; ARQUITETURA:56-61 (128 kbps não fazia efeito: saía ~92) | portável |
| MP3 por container com header Xing no `close()`; ABR, nunca qscale | até 9× de erro de duração sem o header; `global_quality` corta 4-8 kHz (−46/−72 dB). `_open_mp3`/`MP3Writer` `reco.py:738-815` | **PyAV/libmp3lame**. Em Rust é preciso um encoder que escreva o frame LAME/Xing. Lição da casa: `lameenc` foi removido porque não expunha o lametag (ARQUITETURA:42) |
| Resample com estado entre blocos (sem estalo na borda) | `reco.py:771` (swresample) | PyAV. A lógica é portável, mas exige um resampler com estado |
| Encode em streaming numa 3ª thread; o arquivo nasce no `start()`; `stop()` em ~450 ms (antes ~11 s para 20 min) | ARQUITETURA:81-98; `_encode_loop` `reco.py:1834` | portável. Em Rust some o GIL, que é a causa de fundo do overrun |
| Canal que morre vira silêncio e não trava o outro (`_fail`, `_mic_live`) | `reco.py:1726`, `_pump` `:1959-2025` | portável |
| Pausa continua lendo e descarta (lockstep L/R) | `reco.py:1797`, `:1821` | portável |
| Alinhamento em runtime: retém ~10 s (`ALIGN_COLETA_S`, desiste em 20 s), correlação ±0,5 s, reestima a cada 60 s, teto de 50 ms por ajuste | `reco.py:1491-1508`; offset medido de +203 ms e **−399 ms** (o sinal varia); gate da gravação real: pior janela < 10 ms, medido −0,3 ms (TOOLS:27) | lógica portável; usa `scipy.signal.correlate/resample_poly` (`:1527`, `:1897`) |
| Ganho por canal ao vivo, bi-linear 0..1..10×, passo 0,5, não retroativo | `reco.py:2743-2746`; ARQUITETURA:101-110 | portável |
| VAD com limiar adaptativo (percentil 20 × 3, mínimo 0,0035) + agrupamento de 3 s (WER 6,9% contra 9,9%) | `reco.py:668-735`, `:2027` | portável. Ressalva: o limiar é global e zera arquivo comprimido (ARMADILHAS:482) |
| Diarização por dominância de canal, `k_db=15` (`k_db=12` apagou fala real) | `reco.py:961-976` | portável (numpy) |
| AEC `cancel_echo`: mínimos quadrados em blocos de 2 s, 6 taps, Tikhonov e pós-supressão; só na transcrição, MP3 gravado cru | par ERLE×dano 19/08: **+15,5/+6,4/+9,0 dB com dano ≤ 1,2 dB** (+8,7 dB linear, +6,8 dB pós-supressão). Ressalvas de 30/08: número de laboratório (janela contígua; o app concatena retalhos); **2 de 13 com ERLE ≤ 0**, ambas com salto | numpy/scipy STFT (`:1055`). Portável, mas a paridade numérica bit a bit não sai de graça (`np.linalg.solve`, Tikhonov) |
| Defesa anti-loop: compressão zlib > 2,4, n-grama de 1 a 8 palavras > 3×, temperaturas 0,2/0,4/0,6, senão descarta a janela | 221× → 2×; `reco.py:2117-2183` | lógica portável. O `pipe.generate` é **openvino_genai** |
| `no_repeat_ngram_size` ignorado pelo pipeline; o GenAI 2026.2.1 não expõe `compression_factor_threshold`/`logprob_threshold` | ARMADILHAS:15-39 | fato do openvino_genai, vale para qualquer binding |
| Cache de compilação: marca `.compilado-<size>-<device>` + aviso na 1ª vez | NPU **415 s**, iGPU ~10 s (`reco.py:2054-2083`). **Conflito:** desde 25/09 a NPU **quebra** com large-v3-turbo int8 (`roi_end <= max_dim`), e o "NPU 5,5× tempo real" não se repetiu (ARMADILHAS:737-771) | OpenVINO (vale para C++/Rust também) |
| Device AUTO → GPU → NPU → CPU; modelo padrão large-v3-turbo | medido em 29/07; custo por processo GPU 14,6 s / 1,35 GB (ARMADILHAS:760) | OpenVINO |
| Migração de config: `CFG_MIGRACAO=2`, só promove default antigo; a migração 2 é incondicional; só `App.__init__` persiste | `reco.py:173-234`; ARMADILHAS:43, 773 | portável, mas o **formato do `~/.reco_config.json` é contrato** |
| Dispositivo Auto: `auto:console`/`auto:comm`/id; config é a única fonte; id ausente cai no padrão e **nunca devolve id morto** | `reco.py:1382-1470`; resolução no clique ~4+6 ms | **soundcard**: o papel `eCommunications` usa a API privada `mediafoundation._DeviceEnumerator` (por isso o pin 0.4.6). Em Rust é chamada COM direta, o que é mais limpo |
| Instância única pelo mutex `Local\Reco.SingleInstance` + broadcast `Reco.Show` | `reco.py:5204`; ARQUITETURA:155 | portável (Win32) |
| Exclusão vai para a Lixeira (`FOF_ALLOWUNDO`); filesystem é o banco (mp3 + .txt + .resumo.md); resumo por `claude -p --model sonnet` cravado | ARQUITETURA:152, 192-226 | portável |

### B. Defeitos vivos que não podem virar régua de paridade

- **Buffer WASAPI de 22 ms**: `CHUNK=1024` vira `blocksize`, que o soundcard trata como duração do buffer (`reco.py:1472`, `:1788`, `:1812`). Sob carga gera salto de 350-566 ms em **16 de 43 gravações medíveis (37%)**. A recuperação leva ~10 min, em degraus de 50 ms por minuto. A régua é o gate absoluto (pior janela < 10 ms, `varrer_acervo` sem salto), não "igual ao app velho".
- **Rede de segurança do AEC pelo RMS global (×1,05)**: nunca disparou nos casos de ERLE ≤ 0. O conserto desenhado é a régua por bloco (E4b).
- **Duas convenções de `.txt`**: `x.txt` e `x.mp3.txt`. A biblioteca lê só a primeira e deixa 14 de 47 transcrições invisíveis.
- **`cont.streams.audio[0]` sem checar trilha**: vídeo sem som quebra o app (ARMADILHAS:751).
- **Warning de descontinuidade engolido**: `mediafoundation.py:771`, some no exe sem console.

### Armadilhas de captura: artefato do soundcard ou fato do WASAPI?

- **Artefatos do soundcard** (Rust com WASAPI direto se livra deles): `blocksize` amarrado à duração do buffer; timestamp QPC por pacote descartado (`_ffi.NULL`, `mediafoundation.py:699`); zeros fabricados pelo relógio com truncamento de `int()`; warning global por processo; papel 2 só por API privada; `catch_warnings` que não isola por thread (é do Python).
- **Fatos do WASAPI** (o Rust herda): dois relógios de hardware independentes (deriva de −65,8 a +21 ppm; +4,1 ms/min relativo com a caixa muda); offset inicial de buffer entre os streams; modo exclusivo mata o loopback.
- **Suspeita, não verificada**: loopback sem pacote quando nada toca parece ser comportamento do próprio WASAPI. Nesse caso o Rust teria de fabricar o silêncio por conta própria, de preferência pelo QPC. Não confirmei em documentação.
- **Não afirmo** nenhuma capacidade de crate Rust (cpal, wasapi-rs, openvino-rs etc.): não pesquisei.

## (3) Roadmaps em voo diante de uma reescrita

- **Modularização (0/4, nada cortado)**: a reescrita a **torna obsoleta**. Todas as fases tratam de fachada Python, monkeypatch e `import reco`. O que vale reaproveitar é a lista de fronteiras (audio_io / dsp / captura / transcrição / ui) e a régua "mesma saída da linha de base" (Fase 0.2). Existem 23 scripts de `tools/` que importam `reco`: esse acoplamento morre se o motor sair do Python.
- **Salto de alinhamento (só a Fase 0 feita; ordem decidida 0 → A1+A1b → B1+B3 → C1+C2 → B2 → D, §6.1)**: a reescrita **absorve** a correção. Em Rust com WASAPI direto entram por construção o buffer de 1 s com drenagem da cauda (A1b é obrigatória: senão perde até 1 s do fim), a contagem de `DATA_DISCONTINUITY` por stream, o QPC por pacote (B2 melhor do que o desenho) e a ausência de GIL. **Conflita** se as duas frentes andarem juntas, porque A1 no Python é um deploy útil já. **C1/C2** (salto aplicado inteiro, com guardas de janela disjunta e `q ≥ 0,30`) e **E4b** são lógica que se porta igual. **E3a/E3b** (biblioteca) são da UI.
- **Dispositivo Auto**: o hub diz 0/5, mas está **desatualizado**. As Fases 1.1–1.6 estão no código (`CFG_MIGRACAO=2`, `resolve_audio_device`); falta o build da 1.7. A **Fase 2 (vigia de zero exato, regras A/B/C) não existe**: o grep por `zero_seq_s`/`_avisos_dispositivo` volta vazio. A reescrita **absorve**: os limiares medidos (zero desde o início ≥ 60 s; o máximo em gravação boa foi 73 s, o PDI teve 424 s) são a especificação. A Fase 4 (fone QCY) segue válida em qualquer motor.
- **Antieco**: Fases 0–1 feitas. As Fases 2 (AEC adaptativo por sub-banda), 3 (`medir_eco`) e 4 (operação) estão abertas, em prosa. É algoritmo **portável e independente** da UI.
- **Ao vivo**: implementado; falta o teste de 20 min do Gabriel. A reescrita **reabre** o teste, porque a concorrência muda (uma só `pipe.generate` por pipeline, drenar antes da passada final). E o modo ao vivo é suspeito de agravar o overrun (salto §1.7, não medido).
- **Modo nota**: a Fase 1 está commitada (`832527e`), sem UI. As Fases 2–3 são **UI**, ou seja, a reescrita as **absorve** (botão Nota, opção `nota_dir`).
- **Mac/Meet**: as Fases 1, 2 e 4 estão congeladas sem Mac. A reescrita **conflita** com o desenho atual (`MLXTranscriber`, captura em Python). Com Tauri, o porte para Mac fica mais barato na UI, mas a captura (ScreenCaptureKit) e o STT (MLX contra OpenVINO) continuam por plataforma. A Fase 3 (extensão do Meet) é independente.

## (4) Réguas de paridade existentes

**Medem o MP3 ou o `.txt` no disco, então servem para avaliar um binário Rust:**
- `varrer_acervo.py`: pior janela, amplitude e % acima de 50 ms.
- `varrer_silencio.py`: `r_zero_inicio`.
- `medir_aec.py`: par ERLE×dano. Ressalva: escolhe as janelas sozinho, então **não compara antes×depois** sem implementar janelas fixas (E2).
- `varrer_aec.py`, `reparar_duracao.py` (valida o Xing).
- `test_antiloop` e `test_e2e`, pelo critério de saída (repetição ≤ 3×, compressão ≤ 2,4).
- O `.txt` byte a byte contra `tools/transcrever.py` num MP3 curto. Já é a prova usada em 11/11.

**Precisam ser reescritas ou acompanhadas por um harness**, porque mexem direto em `MP3Writer`, `_pump`, `estimar_offset` e `ALIGN_*`:
- `test_encoder.py` (Xing, duração ±0,1 s, L=440 Hz/R=1500 Hz, `close()` < 0,5 s, pareamento).
- `test_alinhamento.py`: **vermelho desde que nasceu**, caso 8 com +352 amostras.
- `test_gravacao_alinhada.py`: toca áudio e mede o gate de 10 ms. Vira teste do motor novo se ganhar uma opção para chamar o executável.
- `test_gravacao_real.py`, `test_relogio_captura.py`, `test_live*`. O `test_live` falha por GPU indisponível, não é gate de latência.
- `bench_final`/`bench_convivencia` (velocidade e latência do vizinho) e `bench_latencia_stt` (0,46 s para 5 s de fala) servem de régua de **desempenho**, e o motor Python precisa delas.

**Falta**: o teste sob carga D1 (`test_gravacao_sob_carga.py`). Sem ele não há baseline que prove que o motor novo resolveu o salto.

## (5) Riscos de perder gravação numa troca de motor

1. **Dois apps lado a lado**: o mesmo mutex/broadcast, os mesmos endpoints e o mesmo `~/.reco_config.json`. O exe antigo aberto regrava os ids se o novo persistir migração antes da hora (ARMADILHAS:773). Escolher um nome de mutex que exclua os dois, ou um config separado com importação.
2. **Os 10 s iniciais retidos** antes de estimar o offset: um crash nesse intervalo perde esses 10 s (`reco.py:1854-1860`).
3. **Cauda descartada no `__exit__`**: até 1 s se o buffer crescer sem drenagem.
4. **Id morto ou endpoint mudo**: grava zeros sem alarme (PDI: 424/424 s). O motor novo precisa nascer com a vigia da Fase 2.
5. **Salto silencioso** se o motor novo também parear por contagem sem contar descontinuidade.
6. **Container não fechado** (kill/crash) gera MP3 sem Xing. Hoje o arquivo parcial é válido mas mente a duração; o remédio é `reparar_duracao`.
7. **Contratos externos**: o coletor de WhatsApp da central chama `Reco/tools/transcrever.py` com `--device GPU` (`central/canais/whatsapp/coletor/src/caminhos.js:12`) e calcula o `.txt` como `midia + ".txt"`. Também são contrato a etiqueta `RECO_TAG` no nome, a convenção `x.txt`/`x.mp3.txt` e o headless `Reco.exe --transcribe`. Trocar o motor sem manter esses pontos quebra a fila do WhatsApp em silêncio.
8. **Nunca `sounddevice`/PortAudio**: já reprovado neste hardware (duplicatas, WDM-KS sem abrir, loopback ausente, faixa vazia sem erro; ARMADILHAS:207-240). Qualquer crate em cima de PortAudio herda isso. Se o cpal no Windows usa WASAPI direto ou não, eu não verifiquei.

**Caminho de menor risco** (minha leitura): trocar primeiro só a UI, com o motor Python atual como processo embutido, no padrão do Lacre. Depois o motor de captura em Rust, avaliado pelas réguas que leem o disco + D1. A transcrição em OpenVINO fica por último, ou não troca.
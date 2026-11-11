# Reco em Rust: Fase 5 — Captura e MP3 em Rust

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: [fase-4](2026-11-11-melhoria-reco-em-rust-fase-4.md) · seguinte: [fase-6](2026-11-11-melhoria-reco-em-rust-fase-6.md) · Base: Reco `7c5c1a1` (2026-11-11)

## Por que esta fase

- A captura de hoje (Python + `soundcard`) pede ao WASAPI um buffer de 22 ms; sob carga o thread perde a vez e o
  WASAPI sobrescreve amostras: salto de 350 a 566 ms em 16 de 43 gravações medíveis (37%).
- Em Rust, com WASAPI direto, entram por construção o buffer de 1 s, a drenagem da cauda, a contagem de
  descontinuidade, o relógio QPC por pacote e a ausência de GIL. Gravar deixa de depender do motor Python.
- O risco é de dado: perder gravação na troca. Por isso a fase mede a linha de base antes, prova com os gates
  que leem o disco e só vira padrão depois de gravações reais em paralelo (sombra) saírem verdes.

## O que ler antes

- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` (D1–D12, em especial D6, D8, D10 e D11; contratos; "O que NÃO fazer").
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\2-restricoes-do-porte.md` (§ A, § B, armadilhas de captura).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\4-ecossistema-rust.md` (§ 1 captura, § 2 MP3, § 5 sinal).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\5-apps-prontos.md` (Anarlog: `CaptureFrame`, `Gap`).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\6-critica-de-completude.md` (V2 joint stereo, V3 ao vivo).
- `C:\Dev\Reco\roadmap\2026-08-21-salto-de-alinhamento-sob-carga.md` § 1.1–1.7, Fase A (A1/A1b) e Fase D (D1, linha 449).
- `C:\Dev\Reco\roadmap\2026-09-30-melhoria-dispositivo-auto.md` § Fase 2 (linhas 279–331: limiares e regras A/B/C).
- `C:\Dev\Reco\docs\ARMADILHAS.md` inteira (gerada); em especial `docs\armadilhas.d\2026-08-30-legado-020-*.md`.
- `C:\Dev\Reco\docs\ARQUITETURA.md` § MP3 por container e § Build; `C:\Dev\Reco\docs\TOOLS.md` (linhas 27 e 29).
- Os mds das Fases 2, 3 e 4 (contrato do motor, build do app novo, tela de Opções, paridade).
- Código: `C:\Dev\Reco\reco.py` linhas 104–129, 210–244, 738–815, 1379–1472, 1491–2016, 2408–2535, 2743–2761, 3765–3800.

## Fase 5 — Captura e MP3 em Rust

**Critério de aceite:**

1. Gravar uma reunião com o PC pesado (muitos programas abertos, processador no talo) e ouvir a própria voz e o
   eco do outro lado juntos do começo ao fim. Se a fase falhar: a partir de algum minuto os dois lados ficam
   meio segundo defasados e a transcrição repete a fala do outro na linha "Eu".
2. Apertar Parar e ter o arquivo na hora, com a duração certa no player e a última frase inteira. Se a fase falhar:
   o arquivo demora a aparecer, o player mostra duração errada (tempo restante pulando) ou a última frase some.
3. Com a captura nova ligada ou desligada nas Opções, o resultado para quem usa é o mesmo (mesmo tipo de arquivo,
   transcrição separada em Eu/Interlocutor, aviso de microfone ou sistema mudo), e desligar a opção volta ao jeito
   antigo sem perder gravação. Se a fase falhar: o arquivo muda de formato, a separação some ou não há volta.

1. [ ] Frescor e pré-condições: conferir que a Fase 4 fechou (relatório no sidecar) e se alguém aplicou A1/A1b no
   Python (`reco.py:1472` `CHUNK = 1024`; `blocksize=CHUNK` em `reco.py:1788` e `:1812`). Anotar o commit no
   relatório da fase: a linha de base do passo 3 vale para esse código. Comandos no Git Bash, a partir de `C:/Dev/Reco`.
   — **prova:** `ls C:/Dev/Reco/roadmap/2026-11-11-melhoria-reco-em-rust.d/; git -C C:/Dev/Reco log --oneline 7c5c1a1..HEAD -- reco.py; grep -c "blocksize=CHUNK" C:/Dev/Reco/reco.py`
   → um relatório da Fase 4 na listagem, a lista de commits (ou vazia) e `2`
   **reprova se:** a contagem der `0` sem nota no relatório (A1 aplicado muda a linha de base) ou a Fase 4 não tiver relatório.

2. [ ] Criar `tools/test_gravacao_sob_carga.py` (novo, até 300 linhas), o D1 desenhado em
   `roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md:449-456`:
   - grava N s (padrão 180) pelos padrões do Windows tocando fala pelo alto-falante, reaproveitando
     `fala_para_tocar`/`toca`/`atraso_do_mp3` de `tools/test_gravacao_alinhada.py:46-117` por import (o `main` é guardado, linha 183);
   - `--carga cpu`: N processos `multiprocessing` em laço (N = núcleos lógicos); `--carga gil`: um thread Python no
     mesmo processo fazendo trabalho puro (reproduz a disputa de GIL do modo ao vivo, § 1.7 do roadmap do salto);
   - `--exe <caminho>`: em vez de `reco.DualRecorder` (`reco.py:1550`), chama `reco-captura.exe gravar` (passo 12);
   - mede o residual por janela de 5 s com `reco.estimar_offset` (`reco.py:1512`) e imprime uma linha final
     `D1 carga=<c> motor=<m> cpu_medio=<%> pior_ms=<x> seg_acima_50ms=<s> maior_trecho_acima_50ms_s=<t> glitches=<g|na> GATE=<PASSOU|REPROVOU>`;
   - `cpu_medio` vem de `GetSystemTimes` por `ctypes` (o `psutil` não está instalado nesta máquina);
   - gate do D1: nenhum trecho acima de 50 ms por mais de 5 s seguidos; glitches podem ser > 0.
   — **prova:** `python tools/test_gravacao_sob_carga.py 30 --carga cpu` → linha `D1 carga=cpu motor=python cpu_medio=<≥ 90> ...` com `GATE=` preenchido
   **reprova se:** a linha não sai, sai sem `GATE=`, ou `cpu_medio` < 90 com `--carga cpu` (a carga não pegou).

3. [ ] Linha de base com o motor Python (sem mudar código): 5 corridas de 180 s com `--carga cpu` e 3 com
   `--carga gil`, notebook na tomada, mesmas caixas e mic. Gravar a tabela das 8 linhas `D1 ...` no relatório da
   fase no sidecar. Regra de leitura (F5-D9): se nenhuma corrida reprovar, o D1 não reproduz o salto nesta máquina
   e a prova de "resolveu" passa a ser só a etapa sombra (passo 20) — dizer isso no relatório, sem afinar a carga
   até reprovar.
   — **prova:** `python tools/test_gravacao_sob_carga.py 180 --carga cpu` (5 vezes) e `python tools/test_gravacao_sob_carga.py 180 --carga gil` (3 vezes) → 8 linhas `D1 ...` coladas no relatório
   **reprova se:** o relatório tiver menos de 8 linhas ou não registrar o commit do passo 1.

4. [ ] Spike S1, MP3, fora do repo (`%TEMP%\reco-spike-mp3`, crate descartável): responder em 1 dia
   - `mp3lame-sys` compila o LAME estático com MSVC (sem DLL ao lado do exe)?
   - `mp3lame-encoder` 0.3 aceita 16 kHz estéreo, `Mode::JointStereo` e ABR com média 96 kbps (se a camada segura
     não expuser ABR, chamar `lame_set_VBR(vbr_abr)` e `lame_set_VBR_mean_bitrate_kbps(96)` pela `-sys`)?
   - `lame_tag_size()` antes do encode e `lame_tag_encode()` no fim, com seek ao início, dão um arquivo que o PyAV
     lê com duração certa? É o que o muxer do ffmpeg faz hoje (`reco.py:727-746`).
   - `lame_tag_encode()` chamado no meio do encode (sem flush) devolve uma tag coerente com os frames até ali? O passo 9
     depende disso (F5-D14); se não, anotar e escrever um cabeçalho `Xing` mínimo à mão (frames + bytes) no lugar.
   Escrever 60 s de tom L=440/R=1500 Hz em `%TEMP%\reco-spike-mp3\t.mp3` e medir com Python.
   - Aviso ao executor: a regra "MP3 sempre por container" do `CLAUDE.md` do Reco proíbe encoder cru. Aqui não se viola:
     o `mp3.rs` escreve a tag `Xing`/`Info` no fechamento (o papel do container), e o passo 23 atualiza a regra no MESMO
     commit que traz o código Rust. Até lá o spike fica fora do repo e o Python continua por `_open_mp3()`.
   — **prova:** `python -c "import av,os;p=os.path.join(os.environ['TEMP'],'reco-spike-mp3','t.mp3');h=open(p,'rb').read(4096);print(round(av.open(p).duration/1e6,2),b'Xing' in h or b'Info' in h)"` → `60.0 True` (±0,1 s)
   **reprova se:** o build pede `libmp3lame.dll`, a duração sai fora de ±0,1 s ou não há `Xing`/`Info`; aí registrar e
   avaliar `lame` via `cc` com fonte vendorizada (F5-D6 "reverte se").

5. [ ] Spike S2, captura, fora do repo (`%TEMP%\reco-spike-wasapi`, `wasapi` 0.27): um programa de 10 s que
   - abre o loopback do padrão em modo compartilhado, com buffer de 1 s, por evento e com autoconversão para 48 kHz f32;
   - com nada tocando, conta pacotes, flags `SILENT` e `DATA_DISCONTINUITY`; depois repete tocando áudio;
   - imprime o `u64QPCPosition` dos 3 primeiros pacotes e o tamanho de buffer concedido;
   - lê o padrão de captura e de saída nos papéis console (0) e comunicação (2) pelo COM cru (`as_immdevice` ou
     `windows`), como `reco.py:1382-1405`, e imprime os ids.
   Comparar os ids com `python -c "import reco;print(reco.default_endpoint_id('speaker',0), reco.default_endpoint_id('speaker',2), reco.default_endpoint_id('microphone',0), reco.default_endpoint_id('microphone',2))"`.
   Este passo decide F5-D5 (fabricar silêncio pelo QPC).
   — **prova:** `cargo run --release --manifest-path "$TEMP/reco-spike-wasapi/Cargo.toml"` (Git Bash) → `mudo: pacotes=<n> silent=<s> | tocando: pacotes=<n> | buffer=48000 | qpc=<3 valores crescentes>` e os 4 ids iguais aos do Python
   **reprova se:** buffer concedido < 48000 frames, QPC zerado, ou ids diferentes dos do `soundcard` (aí o config salvo
   não serve ao Rust e o passo 7 precisa de tradução de id antes de seguir).

6. [ ] Esqueleto da crate própria `app/crates/reco-captura` (F5-D1): `Cargo.toml` (edition 2024, `wasapi` 0.27,
   `mp3lame-encoder`, `rubato`, `rustfft`, `windows`, `serde_json`; `cpal` só anotado como reserva), `src/lib.rs`
   e `src/bin/reco-captura.rs` com o subcomando `versao`. Sem ligar ao `app/src-tauri` ainda: o app segue igual.
   `cargo test` não gera o executável normal: todo passo daqui em diante que chama `C:/pt/release/reco-captura.exe`
   roda antes `cargo build --release --manifest-path C:/Dev/Reco/app/crates/reco-captura/Cargo.toml`.
   — **prova:** `cargo build --release --manifest-path C:/Dev/Reco/app/crates/reco-captura/Cargo.toml && cargo test --release --manifest-path C:/Dev/Reco/app/crates/reco-captura/Cargo.toml && C:/pt/release/reco-captura.exe versao`
   → `test result: ok` e `reco-captura 0.1.0`
   **reprova se:** o binário não aparece em `C:\pt\release` (o `CARGO_TARGET_DIR` desta máquina) ou o build do app novo (Fase 3) quebra.

7. [ ] `src/dispositivo.rs`: porte de `default_endpoint_id` e `resolve_audio_device` (`reco.py:1379-1433`):
   `auto:console`/`auto:comm`/id; enumeração fresca a cada gravação; papel 2 que falhe cai no 0; id salvo que sumiu
   cai no padrão do console com via `ausente`; nunca devolve id morto. Subcomando `dispositivos --json` e `resolver <valor> <kind>`.
   Script novo `tools/paridade_dispositivo.py` (até 80 linhas) compara Rust × Python para os 3 valores e um id inventado.
   — **prova:** `python tools/paridade_dispositivo.py --exe C:/pt/release/reco-captura.exe` → `PARIDADE dispositivo: 8/8 iguais`
   **reprova se:** algum caso diverge, em especial o id inventado devolver ele mesmo (é o silêncio sem alarme do PDI de 29/09).

8. [ ] `src/mp3.rs` + `src/resample.rs` (F5-D6): o arquivo nasce no `start()` com o nome de hoje
   (`gravacao_reco_<data>_<hora>.mp3`, `reco.py:1688-1698`); reserva `lame_tag_size()` bytes no início; resample
   48k→16k com estado entre blocos (`rubato`, como o `swresample` de `reco.py:771-774`); clip em ±1 depois do
   ganho (`reco.py:784-785`); `fechar()` faz flush, escreve a tag no início e fecha; `Drop` fecha se ninguém fechou.
   Subcomando `teste-tom --segundos 60 --saida <arq>` (L=440, R=1500). Em `tools/test_encoder.py` (122 linhas), opção
   `--exe` que roda o bloco [1] (linhas 47-75) sobre o arquivo do Rust, gerado e mantido em `temp/t_rust.mp3`, com os mesmos
   checks. Novo `tools/modo_mp3.py` (até 120 linhas, a medição V2 da crítica tornada ferramenta): aceita arquivos ou pastas e
   imprime por arquivo `<nome> frames=<n> joint=<n> stereo=<n> joint_pct=<%> kbps=<x>` (modo do cabeçalho de cada frame).
   — **prova:** `python tools/test_encoder.py --exe C:/pt/release/reco-captura.exe && python tools/modo_mp3.py temp/t_rust.mp3` → `TUDO OK` e `joint_pct=` ≥ 99
   **reprova se:** falta `Xing`/`Info`, duração fora de ±0,1 s, pico de L ≠ 440 ou de R ≠ 1500 (±15 Hz),
   ou `joint_pct` < 99 (frames em estéreo simples; D8 exige joint stereo).

9. [ ] Arquivo interrompido continua legível e com duração quase certa (F5-D14):
   - `mp3.rs` reescreve a tag no espaço reservado a cada 5 s com o que já foi codificado (seek ao início e volta ao fim);
     com `casco_captura=rust` não há motor para fechar o MP3 quando o casco morre (D11, primeira cláusula), e a Fase 4
     (passo 15) exige `xing=ok` depois de matar o processo;
   - o `teste-tom` ganha `--tempo-real` (alimenta no ritmo do relógio);
   - o `tools/test_encoder.py --exe` ganha `--matar`: esvazia `temp/matar/`, sobe `teste-tom --segundos 600 --tempo-real
     --saida temp/matar/t.mp3`, mata o processo aos 12 s sem fechar, decodifica o parcial com PyAV, confere `Xing`/`Info`
     nos primeiros 4096 bytes e a duração declarada contra a decodificada, e roda `tools/reparar_duracao.py temp/matar`
     (sem `--aplicar`; a ferramenta recebe pasta, não arquivo).
   — **prova:** `python tools/test_encoder.py --exe C:/pt/release/reco-captura.exe --matar` → `OK  arquivo interrompido decodifica`, `OK  parcial tem Xing/Info e duração declarada a até 5 s da real` e `OK  reparar_duracao reconhece o parcial`
   **reprova se:** o PyAV não abre o parcial (bytes reservados quebram o decode), decodifica zero amostras, falta a tag,
   a duração declarada erra por mais de 5 s, ou a linha do `reparar_duracao` sai `ERRO ao ler`.

10. [ ] `src/pareamento.rs`: porte do `_pump` (`reco.py:1959-2016`): pareia por contagem; canal ausente ou morto vira
    silêncio e não trava o outro (`reco.py:1984-1989`, `_fail` em `:1726-1740`); passada final completa o rabo com
    silêncio; ganho por canal 0..1..10× aplicado por bloco, nunca retroativo (`reco.py:2743-2761`, guardado em
    `AtomicU32`); pausa em lockstep por janela de QPC (F5-D11; hoje cada thread descarta sozinho, `reco.py:1797`, `:1821`).
    Seis testes de unidade: os blocos [2] (desalinhados), [3] (canal morto) e [4] (rabo no final) de
    `tools/test_encoder.py:76-117`, mais "canal que morre no meio vira silêncio dali em diante sem travar o outro",
    "pausa corta os dois canais no mesmo instante" e "ganho muda só dali em diante".
    — **prova:** `cargo test --release --manifest-path C:/Dev/Reco/app/crates/reco-captura/Cargo.toml pareamento` → `test result: ok. 6 passed`
    **reprova se:** menos de 6 testes, ou o teste de pausa aceitar diferença de mais de 1 amostra entre os canais.

11. [ ] `src/alinhamento.rs`: porte fiel de `estimar_offset` e da máquina de estados (`reco.py:1491-1547`,
    `:1854-1957`): `ALIGN_*` iguais, decimação por 3, correlação por FFT (`rustfft`), retenção de 10 s, desiste em
    20 s, reestima a cada 60 s, teto de 50 ms por ajuste. Sem C1/C2 do roadmap do salto (F5-D4). Paridade: script novo
    `tools/gerar_pares_alinhamento.py` (até 150 linhas) grava em `temp/pares/` (fora do git; o repo é público, áudio
    de reunião não sobe) 12 pares crus f32 (8 sintéticos com atraso conhecido, de +203 ms a −399 ms, sem eco e com
    um canal mudo; 4 recortados do acervo) e o `esperado.json` do Python. Não usar `tools/test_alinhamento.py` como
    oráculo: está vermelho desde que nasceu (legado-022). — **prova:** `python tools/gerar_pares_alinhamento.py && C:/pt/release/reco-captura.exe paridade-alinhamento temp/pares` → `PARIDADE alinhamento: 12/12 (offset ±1 amostra a 16 kHz, q ±0,01)`
    **reprova se:** qualquer par diverge além da tolerância, ou o par mudo não devolver q = 0.

12. [ ] `src/captura.rs` (um thread por canal, buffer de 1 s, por evento com espera de 100 ms, autoconversão 48 kHz f32,
    loopback estéreo vira mono pela média como `reco.py:1823`) e o subcomando `gravar --segundos N --saida <pasta>
    [--mic <valor>] [--sys <valor>]`, que imprime uma linha JSON final com `arquivo`, `duracao_s`, `parede_s`,
    `stop_ms`, `glitches_mic/sys`, `lacuna_ms_mic/sys`, `silencio_fabricado_s`, `align`. Dentro do thread:
    - conta `DATA_DISCONTINUITY` por canal (ignorando o 1º pacote) e preenche a lacuna com zeros pelo QPC do pacote;
    - flag `SILENT` vira zeros; loopback sem pacote por mais de 40 ms ganha silêncio fabricado pelo QPC com o resto
      fracionário acumulado (F5-D5, se o passo 5 confirmou); pacote que volta corta a sobra fabricada;
    - parar drena a cauda nos dois canais até `GetNextPacketSize == 0` (A1b do roadmap do salto, linhas 316-324);
    - prioridade MMCSS "Pro Audio" com revert (F5-D12); dispositivo invalidado vira canal morto e aviso;
    - captura e encode sob `catch_unwind`; pânico fecha o arquivo pelo `Drop` (F5-D7).
    Em `tools/test_gravacao_real.py` (50 linhas), opção `--exe` que grava pelo binário e aplica o mesmo laudo, e opção
    `--guardar <pasta>` que move o MP3 para a pasta em vez de apagar (o passo 17 usa).
    — **prova:** `python tools/test_gravacao_real.py 30 --exe C:/pt/release/reco-captura.exe` (caixa muda) → `erro` dentro de ±0,05 s, `stop()` < 500 ms, `2 canais` e `OK`
    **reprova se:** o `erro` passa de ±0,05 s (o `OK` da ferramenta aceita até 0,5 s; ~1 s curto = cauda não drenada),
    `stop()` ≥ 500 ms, ou o arquivo não sai com 2 canais.

13. [ ] `src/vigia.rs`: os limiares da Fase 2 de `roadmap/2026-09-30-melhoria-dispositivo-auto.md:279-331` como função
    pura: contadores de zero exato por canal antes do ganho, por blocos (pausa não conta); `zero_desde_inicio_s` e
    `zero_seq_s`; regras A (padrão mudou em Auto), B forte (manual ≠ padrões e sistema zero ≥ 10 s), B suave (sistema
    zero desde o início ≥ 60 s), C (mic zero ≥ 10 s); modo nota só C. O texto do aviso é da interface (Fase 3); a
    crate devolve o código da regra. A regra A consulta o padrão a cada 2 s, fora do thread de captura.
    — **prova:** `cargo test --release --manifest-path C:/Dev/Reco/app/crates/reco-captura/Cargo.toml vigia` → `test result: ok. 12 passed` (5 de contador + os 7 casos obrigatórios das linhas 325-331)
    **reprova se:** o caso (4) "zero desde o início 59 s" alarmar, ou um bloco com 1 amostra ≠ 0 não zerar a sequência.

14. [ ] Canal ao vivo (D10, F5-D8): `src/ao_vivo.rs` abre um named pipe por gravação e manda pares de blocos f32 a
    16 kHz (cabeçalho `u32` com n, depois n de L e n de R), já alinhados e com ganho, como o `on_pair` de hoje
    (`reco.py:2006-2011`). Fila limitada: se o motor não lê, descarta o mais velho; nunca bloqueia a captura. No motor,
    `engine/reco_engine/ao_vivo_pcm.py` (novo, até 200 linhas) lê o pipe e alimenta uma subclasse de `LiveTranscriber`
    (`reco.py:2408`) que troca `_resample_16k` (`:2519-2523`) por identidade e conta a fila a 16 kHz em vez de
    `CAPTURE_SR` (`:2461-2463`, senão a fila de 60 s vira 180 s). `reco.py` não muda. A sonda ganha `--parar-apos <s>`:
    para de ler depois de N s e mantém o pipe aberto até o fim.
    - O módulo mora dentro do pacote (`engine/reco_engine/ao_vivo_pcm.py`), porque o spec do motor congelado só leva o
      pacote; roda por `python -m reco_engine.ao_vivo_pcm` a partir de `engine/`, e põe a raiz do repo no `sys.path`
      fora do PyInstaller como o `__main__.py` da Fase 2 (passo 1) antes de importar `reco`.
    — **prova (Git Bash, o Rust cria o pipe, então sobe primeiro):**
    `C:/pt/release/reco-captura.exe gravar --segundos 20 --saida temp --ao-vivo-pipe reco-teste & sleep 1; (cd engine && python -m reco_engine.ao_vivo_pcm --sonda reco-teste); wait`
    → a sonda imprime `recebidos=<19,5 a 20,5> s por canal, descartes=0`. Repetir com `--sonda reco-teste --parar-apos 2`
    → a linha JSON do `gravar` sai com `parede_s` ≤ 21 e `stop_ms` < 500.
    **reprova se:** com a sonda parada a gravação atrasa ou trava (a fila tem de descartar, nunca bloquear a captura),
    ou a sonda recebe ~60 s (3×, taxa de 48 kHz contada como 16 kHz).

15. [ ] Gate de alinhamento no executável: em `tools/test_gravacao_alinhada.py`, opção `--exe` que troca o
    `DualRecorder` (linhas 132-149) pelo `gravar` do binário, tocando fala como hoje, e com `--exe` grava em
    `temp/gate_exe/` (esvaziada no início; o `temp/` comum tem outros MP3 que sujariam a varredura); depois
    `tools/varrer_acervo.py` nessa pasta.
    — **prova:** `python tools/test_gravacao_alinhada.py 50 --exe C:/pt/release/reco-captura.exe --guardar && python tools/varrer_acervo.py temp/gate_exe --janela 15` → `GATE (|atraso| < 160 amostras = 10 ms): PASSOU` e veredito sem `salto`
    **reprova se:** pior janela ≥ 10 ms, ou `nenhuma janela com correlacao confiavel` (caixa muda: refazer com som, não aceitar).

16. [ ] D1 com o executável contra a linha de base do passo 3: 5 corridas de 180 s com `--carga cpu --exe`
    (a carga `gil` não se aplica ao Rust). Tabela lado a lado no relatório. — **prova:** `python tools/test_gravacao_sob_carga.py 180 --carga cpu --exe C:/pt/release/reco-captura.exe` (5 vezes) → 5 linhas `GATE=PASSOU`, com `glitches=` numérico
    **reprova se:** alguma corrida reprovar, ou `glitches` sair `na` (o contador do passo 12 não chegou ao laudo).

17. [ ] Silêncio e formato: (a) 90 s com a caixa muda e nada tocando; o canal do sistema tem de sair em zero exato,
    que é a assinatura que a vigia e o `tools/varrer_silencio.py` leem; (b) o arquivo real tem o modo e a taxa de hoje
    (V2: joint stereo, ~35 kbps efetivos, não 96). A taxa de um arquivo mudo não foi medida: compara-se com o Python
    gravando nas mesmas condições, não com número fixo.
    — **prova (caixa muda, nada tocando), em sequência:**
    - `rm -rf temp/mudo; python tools/test_gravacao_real.py 90 --exe C:/pt/release/reco-captura.exe --guardar temp/mudo/rust`
    - `python tools/test_gravacao_real.py 90 --guardar temp/mudo/python`
    - `python tools/varrer_silencio.py temp/mudo/rust && python tools/modo_mp3.py temp/mudo/rust temp/mudo/python`
    → `r_zero_inicio=` ≥ 88 no arquivo do Rust, `joint_pct` ≥ 99 nos dois e `kbps` do Rust a até ±30% do Python
    **reprova se:** `r_zero_inicio` baixo no arquivo do Rust (silêncio fabricado não é zero exato ou o encoder deixou
    resíduo), `joint_pct` < 99, ou `kbps` fora de ±30% do Python.

18. [ ] Ligar ao app novo atrás da opção (F5-D2, F5-D10): `app/src-tauri` ganha a dependência por caminho
    `reco-captura = { path = "../crates/reco-captura" }`; o motor (dono do config, D6) passa a responder a chave
    `casco_captura` = `python` | `sombra` | `rust`, padrão `python`.
    - Onde: o padrão mora em `engine/reco_engine/config_cmd.py` (Fase 2, passo 4), não em `_CFG_DEFAULTS` (`reco.py` não
      cresce; o app velho preserva chave desconhecida, `reco.py:216-219`). O prefixo `casco_` já é aceito pelo
      `config.set` (F2-D16), sem lista nova; se a Fase 3 tiver deixado lista fechada de chaves do casco, incluir nela.
    - A tela segue chamando os mesmos comandos (`rec.start`, `rec.pause`, `rec.resume`, `rec.stop`, `rec.set_gain`,
      `state`); o casco os encaminha conforme `casco_captura`, lido pelo `config.get` no início de cada gravação.
    - `python`: tudo vai ao motor, como na Fase 3.
    - `sombra`: o motor grava como hoje (arquivo oficial, e os eventos `state`/`timer`/`level` seguem vindo dele) e o
      Rust grava os mesmos endpoints em `Documents\Reco\sombra\` (a biblioteca do app velho não lista subpasta,
      `reco.py:4495`; conferir que o `library.list` da Fase 2 também não).
    - `rust`: o casco responde ele mesmo aos `rec.*` pela crate e o motor não grava; o fim da gravação passa pelo
      `rec.adotar` do passo 19. Sair no meio da gravação chama o `fechar()` e espera o arquivo fechar (D11, 3ª cláusula).
    - VU vai à tela no máximo a 20 Hz, agregado, nunca um `emit` por bloco. Perfil de release do app em
      `app/src-tauri/Cargo.toml` com `panic = "unwind"` (F5-D7; o Lacre usa `abort`).
    - Recompilar e instalar: `powershell -ExecutionPolicy Bypass -File app\build.ps1` (Fase 3, passo 16; congela o motor
      junto) e instalar o instalador gerado pelo procedimento da Fase 4.
    — **prova:** com `casco_captura=python`, gravar 1 min no app instalado e rodar `python tools/paridade.py <esse mp3>` → `PASSOU`;
    com `sombra`, outra gravação de 1 min e `ls "$USERPROFILE/Documents/Reco/sombra"` → um MP3 com a mesma hora (±3 s)
    **reprova se:** com `python` a régua da Fase 4 reprova ou algo muda para quem usa, ou com `sombra` falta um dos dois arquivos.

19. [ ] Modo `rust` ponta a ponta: o motor adota o MP3 do casco e os eventos passam a sair do casco.
    - Comando novo no motor, `rec.adotar {path, mode?:"rec"|"nota", live?:bool}` (mesmos valores de `mode` do `rec.start` da Fase 2), em `engine/reco_engine/recording.py`
      (Fase 2, passo 6): o arquivo tem de existir, ser `.mp3` e estar na pasta de gravações (ou em `nota_dir` com
      `mode:"nota"`), senão `not_found` ou `bad_args`; com o motor gravando, `busy`.
    - Guarda o caminho como `last_rec` e responde no mesmo formato do `rec.stop` (Fase 2, passo 6): `{path, duration_s,
      auto}`, com a mesma regra de `auto` (`"nota"` no modo nota, `"final_pass"` com `live:true`); estado `stopped`.
      Assim `rec.conclude` (salvar, nota, `final_pass`) segue igual e não responde `not_found`.
    - Com `casco_captura=rust`, o casco chama `rec.adotar` depois do `fechar()` e devolve à tela a resposta dele como se
      fosse a do `rec.stop`; a tela continua no `rec.conclude` de sempre.
    - `state`, `timer`, `level` e `rec.error` passam a sair do casco, nos mesmos formatos da Fase 2 (passo 6); a
      bandeja da Fase 3 (dirigida por esses eventos) passa a segui-los. O retrato do `state` junta a captura (`rec_state`,
      `elapsed_s`) com o resto do motor (`ready`, `transcribing`, `live`, `last_rec`).
    - Quem manda no `state`: o casco do `rec.start` até o `fechar()`; o motor a partir do `rec.adotar` (`stopped`, e
      `idle` depois do `rec.conclude`). O casco não repassa `state` do motor enquanto grava.
    - Motor que cai gravando não para a gravação no modo `rust`: o casco segue gravando e chama `rec.adotar` quando o
      motor volta (D11, segunda cláusula: alarme visível do motor caído, sem esconder que a gravação continua).
    - Propagação: `docs/PROTOCOL.md` ganha a linha do `rec.adotar` e a nota "com `casco_captura=rust`, `state`/`timer`/
      `level`/`rec.error` vêm do casco"; `tools/test_engine_protocol.py` ganha `--adotar`.
    - Mock da Fase 3 (`app/ui/src/mock.ts`): a tela não chama comando novo; o mock responde `casco_captura` no
      `config.get` e, com `rust`, segura o `rec.stop` em `stopping` por ~300 ms (o `fechar()` + `rec.adotar`) antes de
      responder; entra pelo mecanismo de cenário que a Fase 3 tiver, e o `gravar.cjs` (Fase 3, passo 12) roda nos dois.
    - O `--adotar` grava 5 s pelo próprio motor, copia o MP3 com outro nome, adota a cópia e roda
      `rec.conclude {action:"save"}`, que tem de responder o caminho da cópia; depois um caminho inexistente e um fora da pasta.
    - Recompilar e instalar como no passo 18. A gravação de teste com `rust` no app do Gabriel vai à Lixeira depois de
      conferida, e a opção volta a `python` nas Opções: o `rust` só vira uso real no passo 21, depois da sombra.
    — **prova:** `python tools/test_engine_protocol.py --adotar --conferir-doc && node app/ui/tests/gravar.cjs` → `OK adotar: save na cópia, not_found, bad_args`, `nenhum faltando` e `falhas 0`; app instalado em `rust`: 1 min gravado e Salvar → MP3 na biblioteca
    **reprova se:** o `save` responde o arquivo do motor (não adotou), falta `rec.adotar` no doc, o `gravar.cjs` falha com `rust`, a tela fica sem cronômetro, VU ou bandeja, ou o config fica em `rust` ao fim do passo.

20. [ ] Etapa sombra (transição segura): ligar `casco_captura=sombra` pelas Opções no app do Gabriel e juntar 10 gravações
    reais. `tools/comparar_sombra.py` (novo, até 200 linhas) pareia oficial × sombra pela hora do nome (±3 s) e dá,
    por par: duração (±0,1 s entre os dois), veredito do `varrer_acervo`, `r_zero_inicio` dos dois, glitches do Rust,
    e apaga a cópia sombra que passou (dado de reunião não fica duplicado). Par verde = sombra sem `salto`, pior
    janela < 10 ms quando há janela medível, duração ok.
    — **prova:** `python tools/comparar_sombra.py "$USERPROFILE/Documents/Reco"` (Git Bash) → `SOMBRA: 10/10 pares verdes`
    **reprova se:** um par vermelho na sombra; aí não vira padrão, abre-se armadilha e o passo volta ao 12.

21. [ ] Virar padrão e definir a reserva (F5-D3): o padrão da chave `casco_captura` passa a `rust` com migração do
    config do motor (a regra de `CFG_MIGRACAO`, `reco.py:172-208`, vale também para o `engine/`).
    - A migração roda uma vez e troca `casco_captura` ausente, `python` ou `sombra` por `rust`: o config do Gabriel já tem
      `sombra` gravado desde o passo 20, e o valor salvo vence o padrão novo.
    - Marcador próprio do motor (ex.: `_migracao_engine`), nunca subir o `_migracao` que o `reco.py` lê.
    - Ensaio antes do real: `tools/test_engine_protocol.py --migracao` usa o `USERPROFILE` temporário da Fase 2 (passo 4)
      com 4 configs (`casco_captura` ausente, `python`, `sombra`, `rust`) e uma cópia do config real; confere `rust` nos
      quatro, `_migracao` intacto e as outras chaves iguais, byte a byte no valor, às de antes.
    - Backup antes de instalar: `cp ~/.reco_config.json ~/.reco_config.antes-fase5.json` (Git Bash); a volta é copiar de
      volta com o app fechado.
    - O caminho Python continua selecionável por 30 dias e 20 gravações sem incidente; a remoção não é desta fase.
      Data de fim anotada no hub.
    - Recompilar e instalar como no passo 18 antes da prova.
    — **prova:** `python tools/test_engine_protocol.py --migracao && test -s ~/.reco_config.antes-fase5.json && python -c "import json,os;print(json.load(open(os.path.expanduser('~/.reco_config.json'))).get('casco_captura'))"` (depois de abrir o app novo) → `OK migração` e `rust`
    **reprova se:** o ensaio falha, o backup não existe ou está vazio, ou sai `python`/`None` para o Gabriel (a migração não alcançou o config salvo, ARMADILHAS legado-002).

22. [ ] Armadilha nova, só pelo gerador: `python tools/visoes.py novo "WASAPI direto em Rust: o que é fato do WASAPI e o que era artefato do soundcard"`
    e preencher sintoma/causa/o que fazer com o que os passos 5, 12 e 17 mediram (loopback mudo, `SILENT`, 1º pacote
    com descontinuidade, ids iguais ou não, zero exato). Nunca editar `docs/ARMADILHAS.md`.
    — **prova:** `python tools/visoes.py validar` → sem erro, e a entrada aparece no `docs/ARMADILHAS.md` recompilado
    **reprova se:** o arquivo novo não está em `docs/armadilhas.d/` ou o validar acusa frontmatter.

23. [ ] Docs, hub e commit: `README.md` (captura nova e opção `casco_captura`), `docs/ARQUITETURA.md` (seção de captura
    Rust, MP3 com tag LAME em espaço reservado, canal ao vivo, `rec.adotar`), `docs/TOOLS.md` (as ferramentas novas e as
    opções `--exe`, `--adotar`, `--migracao`), `CLAUDE.md` do projeto em 1–3 linhas, no mesmo commit do código Rust (a
    regra "MP3 por container" passa a dizer "tag Xing/Info escrita no fechamento: PyAV no Python, `mp3.rs` no Rust"), linha nova no hub `C:\Dev\cerebro\projetos\reco.md` e nota de
    absorção nos roadmaps do salto e do dispositivo Auto (Fase 2). Commit por pathspec no repo do Reco, sem `-A` e sem
    `--no-verify`; o hub mora em outro repo (`C:\Dev`) e vai num commit próprio lá, também por pathspec.
    Todo `.rs` novo até 500 linhas (F5-D13).
    — **prova:** `wc -l C:/Dev/Reco/reco.py C:/Dev/Reco/app/crates/reco-captura/src/*.rs C:/Dev/Reco/app/crates/reco-captura/src/bin/*.rs && grep -c "reco-captura" C:/Dev/Reco/README.md C:/Dev/Reco/docs/ARQUITETURA.md C:/Dev/Reco/docs/TOOLS.md && git -C C:/Dev/Reco status --short`
    → `reco.py` com 5213, nenhum `.rs` acima de 500, contagem ≥ 1 nos três docs e nada da fase fora do commit
    **reprova se:** arquivo acima de 500 linhas, `reco.py` com mais de 5213 linhas, ou docs sem a menção à captura nova.

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F5-D1 | Crate própria `app/crates/reco-captura` (lib + CLI), dependência de caminho do `app/src-tauri`, sem workspace | testa sem Tauri, dá executável aos gates Python; não mexe no build da Fase 3 | alta | a Fase 3 já tiver workspace (aí entra como membro) |
| F5-D2 | Opção `casco_captura` com três valores e etapa `sombra` antes de `rust` | WASAPI compartilhado aceita dois clientes no mesmo endpoint: a gravação real prova o Rust sem arriscar a oficial | média | a sombra pesar no PC (aí provar com gravações de teste) |
| F5-D3 | Virar padrão com 10 pares sombra verdes; reserva Python por 30 dias e 20 gravações | o salto aparece em 37% das gravações: 10 pares sem salto têm chance baixa (~1%) de ser sorte | média | um incidente na reserva (volta o padrão a `python`) |
| F5-D4 | Alinhamento portado fiel, sem C1/C2; lacuna de descontinuidade preenchida pelo QPC | paridade testável contra o Python; com buffer de 1 s e QPC o salto não deveria nascer | média | a sombra mostrar salto mesmo assim (aí portar C1/C2 com as guardas do roadmap do salto) |
| F5-D5 | Loopback mudo ganha silêncio fabricado pelo QPC, com resto fracionário acumulado | o `soundcard` trunca e perde até 31 ms/min (legado-020); o QPC é comum aos dois canais | média (passo 5) | o loopback mudo entregar pacotes `SILENT` (aí só tratar a flag) |
| F5-D6 | Joint stereo + ABR 96 do LAME, tag LAME própria num espaço reservado no início, sem ID3 | D8; o ID3 de hoje só leva `TSSE=Lavf` e nenhuma ferramenta lê (grep sem achado) | alta | o S1 reprovar o LAME estático (aí LAME vendorizado via `cc`) |
| F5-D7 | Captura sob `catch_unwind` e perfil de release com `panic = "unwind"` | o Lacre usa `abort`: um pânico mataria o app e deixaria o arquivo sem tag | alta | o tamanho do binário pesar (aí captura num processo filho) |
| F5-D8 | Named pipe com pares f32 a 16 kHz, fila limitada com descarte | D10; 128 KB/s cabe folgado; descartar protege a gravação como o `FILA_MAX_S` de hoje | média | o motor não abrir pipe congelado no PyInstaller (aí memória compartilhada) |
| F5-D9 | D1 com duas cargas e regra de leitura fixada antes de rodar | a causa no Python é GIL, e carga externa pode não reproduzir; afinar até reprovar seria viés | alta | — |
| F5-D10 | Chave `casco_captura`, com padrão em `engine/reco_engine/config_cmd.py` (não em `_CFG_DEFAULTS`) | `reco.py` não cresce; D6 dá o config ao motor; o prefixo `casco_` já é aceito (F2-D16) | alta | a Fase 2 já ter os padrões no `engine/` |
| F5-D11 | Pausa por janela de QPC nos dois canais | lockstep de verdade; hoje cada thread vê o evento num instante diferente | média | a janela de QPC errar na pausa curta (aí voltar ao evento por thread) |
| F5-D12 | Prioridade MMCSS "Pro Audio" desde o início | em Rust não há GIL, então a prioridade compra tempo de verdade; custa 10 linhas | média | o D1 do Rust passar igual sem ela e ela causar efeito colateral |
| F5-D13 | Teto de 500 linhas por `.rs`: trava + `wc -l` no passo 23, sem mexer no `tools/tamanho.json` | a Fase 3 (passo 2, F3-D11) põe `.rs`/`.ts` na trava; o `wc -l` cobre se ela não alcançar a crate | alta | a trava ganhar exceção para arquivo gerado (vale a dela) |
| F5-D14 | Tag reescrita a cada 5 s no espaço reservado (confirmada pelo arquiteto; índice, após D12) | com `casco_captura=rust` some a 1ª cláusula do D11; sem isso o parcial perde a duração | média | tag no meio do encode e `Xing` à mão falharem (aí captura em processo filho, F5-D7) |
| F5-D15 | Com `casco_captura=rust`, o motor adota o MP3 por `rec.adotar`; `state`/`timer`/`level`/`rec.error` saem do casco nos formatos da Fase 2 | `rec.conclude` age sobre o `last_rec`, que o motor não teria; tela e bandeja não mudam | média | a Fase 3 preferir a tela chamando a crate direto |

## Premissas não verificadas

- Nomes da API do `wasapi` 0.27 (modo por evento, buffer pedido, autoconversão, `u64QPCPosition` no `GetBuffer`,
  acesso ao `IMMDevice`): lidos só no relatório 4; o passo 5 confirma.
- `mp3lame-encoder` 0.3 expõe ABR e a tag; `mp3lame-sys` compila estático no MSVC (passo 4).
- O PyAV de hoje configura o LAME assim (lembrança do `libavcodec/libmp3lame.c`, não lido aqui): `abr` → `vbr_abr`
  com média do `bit_rate`, joint stereo ligado por padrão, tag do LAME desligada (o muxer escreve o Xing). O passo
  17 mede o resultado, que é o que vale.
- Mesma versão do LAME (3.100) no PyAV e no `mp3lame-sys`.
- O WASAPI marca o 1º pacote com `DATA_DISCONTINUITY` e o loopback mudo não entrega pacote (legado-020 diz que não;
  a crítica V3 pede prova): passo 5.
- O id de endpoint do `soundcard` é a string do `IMMDevice::GetId`, igual à do Rust (passo 5).
- `rubato` 5 tem resampler com estado de razão fixa 3:1; a assinatura exata não foi aberta.
- Contratos das Fases 2–4, lidos nos mds delas na auditoria de 11/11 (ainda não executadas; conferir no código quando
  existir): config em `engine/reco_engine/config_cmd.py` com `config.set` restrito a `_CFG_DEFAULTS` e ao prefixo
  `casco_` (F2-D6, F2-D16); `rec.stop` e os eventos em `engine/reco_engine/recording.py`, `rec.conclude` em
  `engine/reco_engine/conclude.py`; build
  completo em `app\build.ps1` (Fase 3, passo 16), que congela o motor por `engine/build.py`; régua de paridade
  `tools/paridade.py` (Fase 4, passo 4). Em aberto: se o `library.list` da Fase 2 ignora subpasta e se o
  `app/src-tauri/Cargo.toml` da Fase 3 copiou o `panic = "abort"` do Lacre.
- `lame_tag_encode()` no meio do encode, sem flush, dá uma tag coerente com os frames até ali (passo 4; o passo 9 depende).
- O Python do motor congelado abre `\\.\pipe\<nome>` com `open(..., "rb")`.

## O que esta fase NÃO faz

- Não mexe no `reco.py` nem no app Tk (a reserva da Fase 4 continua intacta); não aplica A1/A1b no Python.
- Não porta AEC, VAD, diarização nem transcrição (Fase 6 ou nunca); não porta C1/C2 nem a régua E4b.
- Não muda formato, taxa, modo estéreo nem nomes de arquivo (D8, D6); não muda o `tools/transcrever.py`.
- Não remove o caminho Python de captura (só define a data de fim da reserva).
- Não faz o teste de 20 min do ao vivo (é do Gabriel, abaixo).
- Não muda o `tools/tamanho.json`.

## Pendente (dono: gabriel)

- Usar o app novo nas reuniões com a opção na posição `sombra` até 10 gravações (passo 20): é uso, não decisão;
  a sessão liga a opção e avisa onde ficam as cópias.
- Teste de 20 min do modo ao vivo com a captura nova (card `c361c14c91678` reaberto pelo índice): ação física dele.

## Gatilho que fecha

- Passos 1–23 marcados, com o relatório da fase no sidecar `2026-11-11-melhoria-reco-em-rust.d/` contendo a tabela
  D1 Python × Rust, o resultado dos spikes S1 e S2 e os 10 pares da sombra.
- Verdes: `test_encoder --exe`, paridades de dispositivo e de alinhamento, `test_gravacao_real --exe`,
  `test_gravacao_alinhada --exe`, 5 corridas D1 do Rust, silêncio e formato, `test_engine_protocol --adotar`,
  `--conferir-doc` e `--migracao`, `gravar.cjs` nos dois cenários, `SOMBRA: 10/10`.
- Padrão `casco_captura=rust` no config do Gabriel e data de fim da reserva anotada no hub.
- A Fase 6 pode começar com a captura em Rust como padrão; se a sombra reprovar, a Fase 6 espera.

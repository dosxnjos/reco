# Armadilhas do Reco

Coisas que **parecem** funcionar e não funcionam, com o sintoma que elas produzem
e a causa real. Ler antes de "consertar" qualquer uma delas — várias já custaram
tempo e estão aqui justamente para não custarem de novo.

Padrão herdado do `nomura-bi`. Cada entrada: **sintoma → causa → o que fazer**.

---

## `no_repeat_ngram_size` não faz nada no `WhisperPipeline` (29/07/2026)

**Sintoma:** uma palavra ou frase se repete dezenas de vezes na transcrição
(caso real: `"o que é"` **147 vezes seguidas** num arquivo de 18/07/2026, e
`"que é"` **221 vezes** numa janela de outro). O código *parece* protegido:
havia um `cfg.no_repeat_ngram_size = 4` exatamente para isso.

**Causa:** o atributo **existe** em `WhisperGenerationConfig` — então atribuir
não levanta exceção, e um `try/except` em volta não denuncia nada — mas o
`WhisperPipeline` do `openvino_genai` **o ignora**. Medido: gerando com o
parâmetro desligado e com ele em 4, os textos saem **byte-idênticos**
(2590/2590 e 1427/1427 caracteres).

Pior: o `openvino_genai` 2026.2.1 **não expõe** `compression_factor_threshold`,
`logprob_threshold` nem `condition_on_prev_tokens` — é esse trio que o Whisper de
referência usa para perceber que uma janela degenerou e refazê-la com temperatura
maior. Ou seja, **não existe defesa nenhuma vinda da biblioteca**.

**O que fazer:** a defesa é nossa e vive em `OVTranscriber._degenerado()` +
`_generate_sem_loop()` (`reco.py`). Detecta pela taxa de compressão zlib (> 2,4,
o mesmo limiar do Whisper de referência) e por repetição consecutiva de qualquer
n-grama de 1 a 8 palavras (> 3×), e refaz a janela com temperatura 0,2 → 0,4 →
0,6. Se as três degenerarem, **descarta a janela** — texto ausente é melhor que
147 repetições. Validado: 221× → 2×.
Não reintroduzir `no_repeat_ngram_size` achando que resolve.

---

## Mudar `_CFG_DEFAULTS` é inócuo para quem já abriu o app (29/07/2026)

**Sintoma:** troca-se o default (por exemplo `"model"` de `small` para
`large-v3-turbo`), testa-se numa máquina limpa, funciona — e no computador do
usuário nada muda.

**Causa:** `load_config()` parte dos defaults e depois **deixa o arquivo salvo
sobrescrever** (`cfg.update(json…)`). Isso é o comportamento correto (a escolha
do usuário tem de ganhar), mas significa que qualquer default alterado só alcança
quem **nunca** salvou config. O `~/.reco_config.json` do Gabriel tinha
`"model": "small"` gravado, então a troca de modelo não teria chegado nele.

**O que fazer:** toda mudança de default que **precisa** alcançar usuários
existentes exige uma migração: subir `CFG_MIGRACAO` e tratar o caso em
`_migra_config()`. A migração roda uma vez (marcada em `_migracao` no próprio
JSON) e só promove valores que eram o **default antigo** — uma escolha deliberada
do usuário (ex.: `medium`) é preservada.

---

## A NPU leva ~7 minutos para compilar o modelo na primeira vez (29/07/2026)

**Sintoma:** ao transcrever pela primeira vez com um modelo novo na NPU, o app
fica parado por vários minutos sem sinal de vida. Parece travamento.

**Causa:** é compilação real do grafo para o acelerador. Medido: **415 s** para
`large-v3-turbo` na NPU (contra ~10 s na iGPU). Fica em `CACHE_DIR`
(`_user_data_dir()/ovcache`), então acontece **uma vez por (modelo, device)** —
mas uma vez por combinação, não uma vez na vida.

**O que fazer:** `_pipeline()` marca cada combinação já compilada com um arquivo
`.compilado-<size>-<device>` no cache e mostra um aviso explícito na primeira vez.
Não remover esse aviso; sem ele o usuário mata o app achando que pendurou.

---

## `cancel_echo`: 37 dB no sintético, 3 dB no áudio real (29/07/2026)

**Sintoma:** o cancelamento de eco estava documentado como "~37 dB ERLE
validado", mas o eco da caixa de som continuava audível e a diarização seguia
atribuindo ao usuário falas do interlocutor.

**Causa:** os 37 dB eram reais — em eco **sintético**, linear e invariante no
tempo. A implementação estimava **um** ganho complexo por bin de frequência para
a janela **inteira** de 30 s, o que assume que o caminho acústico é invariante
por 30 s e cabe num único quadro de FFT (64 ms). Numa sala real, medido nas
gravações do próprio Gabriel: **+3,2 dB** e **+3,7 dB**, com acoplamento
caixa→mic de −17,9 dB e −23,7 dB (abaixo de −35 dB seria desprezível).

**O que fazer:** a versão atual usa mínimos quadrados em blocos de 2 s com 6 taps
(~96 ms) + pós-supressão residual, e entrega **+7,2 dB** custando 0,3 dB da voz
do usuário. **Não tentar chegar a 20-40 dB alongando o filtro** — ver a armadilha
seguinte. E sempre medir ERLE em áudio **real**, nunca em eco sintético: é
exatamente esse teste que validou uma implementação que não funcionava.

---

## O teto do AEC é deriva de clock, não o filtro (29/07/2026)

**Sintoma:** melhorar o filtro de eco dá ganhos que estancam por volta de 7 dB,
e a melhora some em gravações longas.

**Causa:** microfone e loopback do sistema correm em **relógios de hardware
independentes**. Medido pelo atraso ótimo de correlação ao longo do arquivo:

| gravação | atraso mic↔loopback | desvio-padrão | deriva |
| --- | --- | --- | --- |
| 5,7 min | 608 amostras (38 ms) | **0** | 0,1 ppm |
| 80 min | 2283 amostras (143 ms) | **2314** | **−65,8 ppm** (≈ −237 ms/h) |

Em gravação curta o alinhamento é estável; em 80 minutos ele passeia centenas de
milissegundos. Nenhum filtro linear acompanha isso sem **reamostragem contínua**
de compensação.

**O que fazer:** aceitar o teto. Passar dele exigiria compensar a deriva *e* a
distorção não-linear da caixa — caro e incerto. Para o objetivo real (diarização
correta), o caminho barato é decidir o locutor por **dominância de energia entre
os canais**, que é robusto a eco residual e não depende de cancelar nada. Fone de
ouvido continua sendo a solução de custo zero que elimina o problema na origem.

---

## `np.linalg.solve` mudou de semântica no numpy 2.x (29/07/2026)

**Sintoma:** `ValueError: solve: Input operand 1 has a mismatch in its core
dimension 0, with gufunc signature (m,m),(m,n)->(m,n)`.

**Causa:** com `A` de forma `(lote, P, P)` e `b` de forma `(lote, P)`, o numpy 1.x
tratava `b` como pilha de vetores; o 2.x trata como matriz e o lote não bate.

**O que fazer:** passar `b[:, :, None]` e tirar a dimensão depois:
`np.linalg.solve(A, b[:, :, None])[:, :, 0]`.

---

## NLMS ingênuo diverge quando a referência silencia (29/07/2026)

**Sintoma:** um AEC adaptativo protótipo devolveu **ERLE de −38 dB** — ou seja,
amplificou o sinal em vez de limpá-lo.

**Causa:** o passo do NLMS é normalizado pela energia da referência
(`e / potência`). Quando o canal do sistema fica em silêncio, a potência tende a
zero, o passo explode e o filtro diverge.

**O que fazer:** usar mínimos quadrados com regularização de Tikhonov relativa à
energia **do próprio bloco** (solução fechada, estável por construção), como está
em `cancel_echo`. E manter a rede de segurança que devolve o áudio original se a
saída sair mais alta que a entrada — um AEC nunca deveria aumentar o sinal.

---

## Medir "impacto em outros apps" com numpy é medir a coisa errada (29/07/2026)

**Sintoma:** um benchmark de convivência acusou combinações rodando **mais
rápido** que a máquina ociosa e o app vizinho **acelerando** durante a
transcrição. Resultado incoerente, descartado.

**Duas causas somadas:**

1. O "vizinho" usava `numpy @ numpy`, que aciona **BLAS multi-thread** e satura
   todos os núcleos. Isso simula um segundo job pesado, não um app interativo — e
   ainda distorce a medida de velocidade do que se está medindo (a iGPU caiu de
   14,9× para 7,2× por causa dele).
2. O baseline "ocioso" é medido com a CPU em **frequência baixa**. Quando a
   transcrição carrega a máquina, o governor sobe o clock e o vizinho fica
   genuinamente mais rápido. O baseline é que estava lento.

**O que fazer:** medir **latência**, não throughput, com um vizinho
single-thread em **processo separado** que acorda periodicamente e faz trabalho
fixo (`temp/vizinho.py`) — é o perfil de um app de interface. E lembrar que esse
teste é puro CPU: ele **não** mede a iGPU disputando com renderização de tela e
vídeo, que é o cenário "transcrever durante reunião com câmera".

## `--diarizar` não prova autoria em gravação feita no alto-falante (03/08/2026)

**Sintoma:** rodamos `transcrever.py --diarizar` numa gravação real para
responder "quem falou esta frase — o Gabriel ou a interlocutora?". A saída veio
com **as duas faixas repetindo o mesmo texto**, deslocadas por uma fração de
segundo: cada frase aparece uma vez em `Interlocutor(es)` e de novo em `Eu`.

**Causa:** a gravação foi feita **sem fone**. O áudio do sistema saiu pelos
alto-falantes e voltou pelo microfone, então o canal do mic contém a fala do
outro lado. O `cancel_echo` entrega ~7 dB de ERLE (ver a armadilha do teto de
deriva de clock acima) — o bastante para melhorar a transcrição, longe do
necessário para **separar** os interlocutores.

**O que a diarização ainda serve nesse caso:** os trechos em que os dois canais
**divergem** continuam válidos e são justamente as trocas reais de turno —
convite num canal, resposta curta no outro. Foi o que permitiu confirmar a
autoria na prática. O que **não** vale é ler cada linha `Eu:` como fala do
Gabriel.

**Regra:** para atribuição de autoria, `--diarizar` só é prova se a gravação foi
feita **com fone**. Sem fone, tratar como indício e confirmar pelo conteúdo
(quem faz o convite, quem responde, quem trata o outro por "você"). E, quando o
objetivo for justamente saber quem disse o quê, gravar de fone.

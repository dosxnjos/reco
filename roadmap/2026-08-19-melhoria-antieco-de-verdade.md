# 2026-08-19 — Antieco de verdade: o que o áudio real diz, e o que fazer

**Alvo:** o cancelamento de eco do Reco (`cancel_echo`, `dominancia_sistema`, o
alinhamento de canais e a métrica `tools/medir_eco.py`).

**Origem:** o Gabriel perguntou por que a gravação de 19/08/2026 11:00 está com
eco, e se o app não tem AEC configurado. A investigação achou três coisas piores
que a pergunta: a métrica do projeto subestima o eco por construção, o AEC atual
destrói a voz do usuário em até 28 dB, e os dois canais do MP3 estão
desalinhados por ~203 ms.

**Arquivo analisado:** `~/Documents/Reco/gravacao_reco_2026-08-19_11-00-54.mp3`
(32,5 min, 16 kHz estéreo, L=mic com ganho 8×, R=loopback com ganho 1×).

**Contexto que muda o regime medido em 29/07:** o `mic_gain` do Gabriel está em
**8,0×** (+18 dB) e isso é **necessidade, não descuido** — o mic dele (array
digital do Intel Smart Sound) entrega voz ~18 dB abaixo do nível do loopback, e
sem o ganho a fala dele fica inaudível ao lado do áudio do PC. Decisão do
Gabriel nesta sessão: **o 8× fica**; a solução tem que ser antieco, não abaixar
o ganho.

---

## 1. O que foi medido (nada aqui é suposição)

Scripts usados (no scratchpad da sessão, portáveis para `tools/` quando a Fase 3
for executada): `eco_stream.py` (métrica atual, em streaming), `analise_eco.py`
(atraso, coerência, três tratamentos), `analise_eco2.py` (estimativa sem viés de
rótulo), `controle2.py` (controle negativo), `aec_honesto.py` (DTD emulado),
`amostras.py` (amostras de escuta).

### 1.1 A métrica do projeto subestima o eco por construção

`tools/medir_eco.py` mede acoplamento só em blocos rotulados `so_sys`:

```python
so_sys = (s >= lim_s) & (m < lim_m * 3)   # PC fala, voce (quase) calado
```

O segundo termo exige que **o mic esteja quase mudo**. Como o eco entra no mic,
todo bloco com eco forte cai em `ambos` e **sai da conta**. Neste arquivo:
`so_sistema=1753`, `so_mic=4401`, **`ambos=11448`** (59% do arquivo), `silêncio=1875`.
A medida é feita nos 9% de blocos onde o eco é mais fraco.

| medida | valor | como foi obtido |
| --- | --- | --- |
| acoplamento pela métrica atual | **−30,9 dB** | `medir_eco.py`, blocos `so_sys` |
| energia do mic explicada pelo loopback | **77% a 93%** | LS 128–320 taps, blocos de 1 s realinhados, janelas de 4 s |
| coerência mic↔loopback (alinhada) | **0,48 a 0,76** | Welch, ref alinhada pelo atraso ótimo |

Controle negativo (mesma estimativa com referência falsa — outro trecho do mesmo
canal, o canal invertido no tempo, ruído branco de mesmo RMS):

```
janela 0.0m   real 90.9% | outro 3.5% | invertido 1.4% | ruido 1.8%
janela 7.0m   real 83.4% | outro 1.5% | invertido 3.6% | ruido 2.0%
janela 22.8m  real 93.4% | outro 5.0% | invertido 5.4% | ruido 1.6%
janela 31.7m  real 76.7% | outro 2.7% | invertido 1.3% | ruido 0.9%
```

Referência falsa explica 1–5% (o esperado por azar com taps/N ≈ 1%); a real
explica 77–93%. **O canal do mic é dominado pelo áudio do PC, não pela voz do
usuário.** O −30,9 dB da métrica atual é artefato de seleção.

⚠️ Os números históricos do projeto (−17,9 / −23,7 / −20,5 / −30,9 dB) herdam o
mesmo viés e **não devem ser citados** como acoplamento real até a Fase 3.

### 1.2 Os dois canais estão desalinhados por ~203 ms

| medida | valor |
| --- | --- |
| atraso mic↔loopback (mediana de 8 janelas) | **3241 amostras = +203 ms** |
| faixa ao longo do arquivo | 2142..3370 amostras (134..211 ms) |
| jitter entre janelas | 385 amostras (24 ms) |
| tendência (deriva de clock) | **+21 ppm** (+76 ms/hora) |

Eco acústico de uma caixa a um metro é ~3 ms. Esses 203 ms são **latência de
buffer** entre os dois streams do WASAPI: os threads do `DualRecorder` sincronizam
o *início* (`threading.Barrier` antes do `__enter__`), mas o loopback entrega o
primeiro bloco com um offset próprio, e o `_pump` pareia por **contagem de
amostras** — então o offset inicial fica gravado para sempre.

Consequências, em ordem de importância:

1. **Percepção.** Acima de ~50 ms o ouvido para de integrar a reflexão como
   reverberação e passa a ouvir **eco separado**. É a causa mais provável da
   queixa original.
2. **O alinhamento do código satura.** `_alinhar_canais` usa `maxlag_s=0.2`
   (= 3200 amostras) e o atraso real chega a **3370**. Nas janelas em que passa
   de 3200, o alinhamento erra e o filtro subtrai sinal que não é eco.
3. **Diarização.** `dominancia_sistema` realinha a cada 30 s e sobrevive, mas
   compara blocos de 100 ms — um alinhamento errado inverte a decisão de quem
   falou.

### 1.3 O `cancel_echo` atual é um supressor, e ele come a voz do usuário

ERLE medido nos blocos `so_sys` × atenuação da voz medida nos blocos `so_mic`:

| janela | ERLE com pós-supressão | dano na voz | ERLE sem pós-supressão | dano na voz |
| --- | --- | --- | --- | --- |
| 0,0 min | +9,8 dB | +1,2 dB | +6,2 dB | +0,9 dB |
| 7,0 min | +16,6 dB | **+17,1 dB** | +10,3 dB | +14,3 dB |
| 17,7 min | +15,0 dB | **+12,4 dB** | +8,4 dB | +10,4 dB |
| 31,7 min | +8,8 dB | **+14,2 dB** | +5,4 dB | +11,6 dB |

E com o teste de double-talk emulado (filtro estimado **só** em blocos far-end-only,
validado fora deles):

| janela | DTD: ERLE in-sample | ERLE out-of-sample | dano na voz | atual: ERLE | dano na voz |
| --- | --- | --- | --- | --- | --- |
| 0,0 min | +4,3 dB | +2,2 dB | **−0,1 dB** | +6,8 dB | +1,8 dB |
| 27,7 min | +7,7 dB | +2,8 dB | **+2,1 dB** | +18,1 dB | **+28,4 dB** |

Leitura:

- O ERLE alto do código atual **é a mesma coisa** que o dano na voz: atenuação
  cega. Onde ele "cancela" 18 dB, ele apaga 28 dB da voz do Gabriel.
- Congelar o filtro fora dos trechos far-end-only **elimina o dano** (−0,1 e
  +2,1 dB), o que prova que a causa é a **ausência de detector de double-talk**
  (DTD) — e 59% deste arquivo é double-talk.
- O roadmap de 29/07 mediu "+7,2 dB de ERLE com 0,3 dB de perda na voz". Aquele
  número não vale mais no regime atual (ganho 8×, atraso 203 ms).

### 1.4 Teto realista de um cancelador linear neste sinal

| tratamento | ERLE |
| --- | --- |
| alinhar + ganho escalar ótimo ("sincronizar") | **−1,1 dB** (não cancela nada) |
| LS 128–320 taps, bloco de 1 s, realinhado (in-sample) | **+6,3 a +11,8 dB** |
| filtro estimado em far-end-only, aplicado adiante (out-of-sample) | **+2,2 a +2,8 dB** |

A queda de ~9 dB (in-sample) para ~2,5 dB (out-of-sample) é o dado mais
importante para a Fase 2: **o caminho de eco muda mais rápido que a janela de
estimativa.** Três causas somadas, todas presentes neste hardware:

1. **O mic tem processamento dinâmico próprio.** É o array digital do *Intel
   Smart Sound*, que aplica AGC/supressão no APO. Medida que revela isso: nos
   blocos `so_sys` o mic fica em −51 dBFS (piso de ruído do arquivo: −63 dBFS),
   mas nas janelas com fala o loopback explica 90% da energia do mic — o ganho
   efetivo do caminho **muda com o conteúdo**, o que nenhum filtro linear
   invariante acompanha.
2. **Deriva de clock**, +21 ppm aqui (era −65,8 ppm em 23/07) — ver a armadilha
   antiga, continua valendo.
3. **Distorção não-linear da caixa**, que é o que sobra depois do filtro.

---

## 2. Decisões

1. **O `mic_gain` 8× fica.** Decisão do Gabriel: é o que nivela a voz dele com o
   áudio do PC. Qualquer proposta que dependa de baixá-lo está fora.
2. **O eco audível no MP3 não é bug de configuração: o AEC nunca rodou no
   arquivo.** `cancel_echo` só é chamado em `OVTranscriber._transcribe_channel`;
   o caminho de gravação (`DualRecorder._pump` → `MP3Writer.feed`) grava cru, por
   decisão de projeto (roadmap 29/07 § 2, decisão 5: "não processar o áudio na
   gravação; limpeza é exportação sob demanda"). Isso **não muda** — mas ganha um
   caminho de exportação limpa (Fase 2.3).
3. **Alinhar os canais NÃO é "processar o áudio"** e entra na gravação: é
   compensação de offset de buffer, não filtragem. Ganho de percepção imediato e
   pré-requisito de qualquer AEC.
4. **ERLE sozinho é métrica proibida daqui pra frente.** Todo número de AEC neste
   projeto passa a ser reportado como par **(ERLE, dano na voz)**, medido
   out-of-sample. Foi um ERLE sem par que fez o AEC atual parecer bom por 3
   semanas.
5. **A meta da Fase 2 é ERLE ≥ 8 dB com dano na voz ≤ 1 dB**, não "20–40 dB". O
   teto medido neste sinal não permite prometer mais sem tratar AGC do mic e
   não-linearidade da caixa.

---

## 3. Fases

### Fase 0 — Parar o dano (barato, primeiro)

**0.1 Alargar a busca de atraso.** `reco.py`, `_alinhar_canais`: `maxlag_s=0.2`
→ `0.5`. Motivo no § 1.2 (o atraso real chega a 3370 amostras e satura o limite
de 3200). Cuidado: `maxlag` maior aumenta o custo da correlação — é FFT, o
impacto é desprezível no caminho offline.
*Pronto quando:* nas 8 janelas do arquivo de 19/08, nenhum atraso ótimo bate no
limite da busca (`|d| < maxlag - 1`).

**0.2 Detector de double-talk no `cancel_echo`.** Hoje o LS por bin roda em todo
bloco de 2 s, com ou sem fala do near-end. Implementar: por bloco, decidir
`far_end_only` (critério Geigel — `max|mic|` contra `max|ref_al|` com margem — ou
razão de energia entre mic e eco estimado do bloco anterior); **atualizar o
filtro só quando `far_end_only`**, reusando `h` do último bloco válido caso
contrário; e **aplicar a pós-supressão residual só em blocos `far_end_only`**.
*Pronto quando:* `dano na voz ≤ 2 dB` em TODAS as janelas medidas em `aec_honesto.py`
(hoje: até +28,4 dB) e o ERLE em far-end-only não cai abaixo de +5 dB.

**0.3 Rede de segurança por bloco.** A atual só compara RMS do arquivo inteiro
(`r_out > r_in*1.05` devolve o original). Trocar por: em cada bloco, se a energia
removida passar de um teto (ex. 12 dB) **e** o bloco não for `far_end_only`,
devolver o bloco original.
*Pronto quando:* nenhum bloco `so_mic` perde mais de 3 dB.

### Fase 1 — Alinhar os canais na gravação

**1.1 Medir o offset no início da gravação.** No `DualRecorder`, depois dos
primeiros ~10 s com energia nos dois canais, estimar o atraso por correlação
(reusar `_alinhar_canais`, com `maxlag_s=0.5`) e **descartar as amostras do canal
adiantado** antes do pareamento no `_pump`. Registrar o offset aplicado no log.
*Pronto quando:* em gravação nova de 3 min com áudio tocando, o atraso medido no
MP3 resultante fica |d| < 160 amostras (10 ms).

**1.2 Reestimar durante a gravação (deriva).** +21 ppm = ~76 ms/hora; numa
reunião de 2 h o alinhamento inicial não serve no fim. Reestimar a cada ~5 min e
corrigir por drop/insert de amostras no canal adiantado (correção inteira basta:
1 amostra a cada ~48 mil).
*Pronto quando:* em gravação de 60 min, o atraso medido em janelas ao longo do
arquivo varia menos de 32 amostras (2 ms).

**1.3 Consertar arquivos antigos** por remux com deslocamento de um canal, no
molde de `tools/reparar_duracao.py` (valida antes de substituir; sem `--aplicar`
só relata).

### Fase 2 — AEC de verdade (offline, adaptativo)

**2.1 Filtro adaptativo por sub-banda com DTD.** STFT como hoje, mas: NLMS
normalizado **por bin** com passo congelado em double-talk (o DTD da Fase 0.2),
comprimento de filtro cobrindo ≥ 200 ms de cauda, realinhamento a cada 0,5 s e
atraso fracionário (interpolação) para a deriva sub-amostral. Nunca substituir o
LS regularizado sem medir: o NLMS ingênuo já divergiu para −38 dB neste projeto
(ver `docs/ARMADILHAS.md`).
*Pronto quando:* **ERLE ≥ 8 dB out-of-sample com dano na voz ≤ 1 dB**, em 3
gravações (19/08 11:00, 19/08 10:22, 18/08 15:16).

**2.2 Compensar o AGC do mic.** O caminho varia com o conteúdo (§ 1.4). Estimar
um ganho lento por bloco (ex. mediana da razão mic/eco_estimado em 2 s) e
normalizar antes do filtro.
*Pronto quando:* a diferença entre ERLE in-sample e out-of-sample cair para menos
de 3 dB (hoje: ~7 dB).

**2.3 Exportar limpo.** Botão/ação na biblioteca que grava
`<nome>_limpo.mp3` com o canal do mic tratado (alinhado + AEC), preservando o
original. Fecha a decisão 5 de 29/07 (limpeza é exportação, não gravação).
*Pronto quando:* o arquivo sai com duração idêntica ao original (header Xing
correto — ver a regra do MP3 por container no `CLAUDE.md`) e o par (ERLE, dano)
da Fase 2.1 é reproduzido no arquivo exportado.

### Fase 3 — Consertar a métrica

**3.1 `tools/medir_eco.py` sem viés.** Rotular far-end-only por **predição**
(bloco em que o loopback explica a maior parte da energia do mic), não por "mic
baixo". Reportar sempre: acoplamento real (energia explicada), ERLE in/out-of-sample
e **dano na voz**.
**3.2 Regravar os números** citados em `CLAUDE.md`, `docs/ARMADILHAS.md` e
`cerebro/projetos/reco.md` com a métrica nova, marcando os antigos como enviesados.
*Pronto quando:* rodar nos 3 arquivos e os números baterem com os deste roadmap
(±1 dB).

### Fase 4 — Origem (custo zero, maior efeito)

Fone de ouvido elimina o acoplamento; baixar o volume da caixa e aproximar o mic
reduz a necessidade dos 8×. Não é engenharia, é operação — mas é o único caminho
que leva o eco a "desprezível" neste hardware.

---

## 4. Descartado e impraticável

- **AEC de 20–40 dB por software neste sinal — impraticável.** Medido: filtro
  estimado em far-end-only generaliza só 2,2–2,8 dB, porque o mic (array do Intel
  Smart Sound) aplica AGC/supressão própria e o caminho muda com o conteúdo.
  Passar de ~10 dB exigiria modelar esse processamento e a distorção da caixa.
  Mantém o veredito de 29/07, agora com a causa medida (antes era atribuído só à
  deriva de clock).
- **"Sincronizar" como solução de eco — descartado como cancelamento, aceito como
  percepção.** Alinhar + ganho escalar ótimo dá **−1,1 dB** de ERLE: não cancela
  nada. Mas os 203 ms são a causa provável da queixa auditiva, então o
  alinhamento entra na Fase 1 pelo motivo certo (percepção e pré-requisito de
  AEC), não como antieco. Hipótese levantada pelo Gabriel nesta sessão; medida e
  reclassificada, não descartada.
- **Baixar o `mic_gain` de 8× — recusado pelo Gabriel** nesta sessão: é o que
  nivela a voz dele com o áudio do PC. Registrado porque foi a primeira proposta
  do agente e está errada em premissa (trata sintoma, cria outro).
- **WebRTC AEC3 em tempo real — segue descartado** (dependência binária no
  PyInstaller, 29/07). Nota nova: se algum dia o AEC for para a **captura**, é a
  rota mais promissora, porque resolve deriva por construção. Reavaliar só nesse
  cenário.
- **Windows Voice Capture DSP (`CLSID_CWMAudioAEC`) — não avaliado, não
  descartado.** É o AEC da plataforma, com acesso aos dois endpoints e
  compensação de deriva nativa. Exigiria reescrever a captura em Media Foundation
  (o `soundcard` abre WASAPI em shared mode sem `SetClientProperties`, portanto
  categoria `Other`, e não pede loopback reference — nenhum AEC de plataforma
  entra hoje). Fica registrado para o Fable rever: é a única rota que poderia
  passar de 10 dB.
- **RNNoise / supressão de ruído — fora de escopo** (é ruído, não eco). Segue
  como em 29/07.
- **Medir com o arquivo inteiro na RAM — impraticável nesta máquina.** O decode
  de 32,5 min (249 MB) estourou memória: a máquina tem **0,4 GB livres de
  15,4 GB**. Toda medição aqui é por janela, via `seek`. Vale para qualquer
  script novo em `tools/`.

---

## 5. Amostras de escuta (geradas em 19/08/2026)

`C:\Dev\Reco\temp\` — 30 s do trecho de 27,5 min do arquivo de 19/08 11:00:

| arquivo | o que é | nível do canal do mic |
| --- | --- | --- |
| `1_original.mp3` | como o Reco gravou | −20,9 dBFS |
| `2_alinhado.mp3` | mesmos canais, 203 ms compensados | −20,9 dBFS |
| `3_alinhado_aec.mp3` | alinhado + LS 160 taps/1 s, sem pós-supressão (−9,5 dB de eco) | −30,4 dBFS |
| `4_atual_aec.mp3` | o `cancel_echo` de hoje | −38,2 dBFS |

A diferença de 7,8 dB entre `3` e `4` no canal do mic é a voz do usuário que o
código atual remove.

---

## 6. Pendente — decisão do Gabriel

- **Ordem de execução.** A recomendação é Fase 0 → 1 → 3 → 2 (parar o dano,
  alinhar, consertar a métrica, e só então o AEC novo — sem métrica confiável a
  Fase 2 não tem como ser validada).
- **Fase 2 vale o custo?** Ganho realista: eco 8–10 dB menor, sem dano na voz.
  Não elimina o eco. Fone elimina. A Fase 2 só se justifica para as gravações em
  que não dá para usar fone.

---
titulo: `medir_eco.py` subestima o eco por construção (19/08/2026)
data: 2026-08-19
---
**Sintoma.** A métrica do projeto reporta acoplamento caixa→mic de −20 a −31 dB
("quase desprezível") em gravações cujo canal de mic é, na verdade, **dominado**
pelo áudio do PC — e o eco continua audível no MP3.

**Causa.** O rótulo de "só o PC falando" exige que o mic esteja quase mudo:

```python
so_sys = (s >= lim_s) & (m < lim_m * 3)
```

Como o eco entra no mic, todo bloco com eco **forte** é reclassificado como
`ambos` e sai da conta. No arquivo de 19/08 11:00: 1753 blocos `so_sistema`
contra **11448 `ambos`** (59% do arquivo). A medida acontece nos ~9% de blocos
onde o eco é mais fraco — é viés de seleção, não medição.

**O que fazer.** Medir por **predição**, não por rótulo de energia: estimar o
caminho de eco por mínimos quadrados (a voz do near-end é descorrelacionada da
referência, então o LS é não-viesado mesmo com fala em cima) e reportar a fração
da energia do mic que a referência explica. Medido assim, no mesmo arquivo:
**77% a 93%** (contra −30,9 dB da métrica antiga). E **sempre rodar o controle
negativo** — a mesma estimativa com referência falsa (outro trecho, canal
invertido, ruído branco) explica 1–5%; sem esse controle não há como distinguir
medição de sobre-ajuste. Números históricos (−17,9 / −23,7 / −20,5 / −30,9 dB)
herdam o viés: não citar como acoplamento real.

⚠️ Este é o viés do **acoplamento**. O mesmo script tem um segundo problema, pior
e independente: os rótulos são por energia **simultânea**, o que com canais
desalinhados troca eco por voz — ver a armadilha seguinte.

---

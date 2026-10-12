---
titulo: `no_repeat_ngram_size` não faz nada no `WhisperPipeline` (29/07/2026)
data: 2026-07-29
---
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

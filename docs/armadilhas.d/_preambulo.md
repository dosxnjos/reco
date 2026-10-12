---
tipo: preambulo
ordem:
  - 2026-07-29-legado-001-no-repeat-ngram-size-nao-faz-nada-no-whisperpipeline-29-07-2
  - 2026-07-29-legado-002-mudar-cfg-defaults-e-inocuo-para-quem-ja-abriu-o-app-29-07-2
  - 2026-07-29-legado-003-a-npu-leva-7-minutos-para-compilar-o-modelo-na-primeira-vez
  - 2026-07-29-legado-004-cancel-echo-37-db-no-sintetico-3-db-no-audio-real-29-07-2026
  - 2026-07-29-legado-005-o-teto-do-aec-e-deriva-de-clock-nao-o-filtro-29-07-2026
  - 2026-07-29-legado-006-np-linalg-solve-mudou-de-semantica-no-numpy-2-x-29-07-2026
  - 2026-07-29-legado-007-nlms-ingenuo-diverge-quando-a-referencia-silencia-29-07-2026
  - 2026-07-29-legado-008-medir-impacto-em-outros-apps-com-numpy-e-medir-a-coisa-errad
  - 2026-08-03-legado-009-diarizar-sem-aec-nao-separa-nada-em-gravacao-no-alto-falante
  - 0000-00-00-legado-010-sounddevice-portaudio-nao-serve-para-captura-neste-hardware
  - 2026-08-12-legado-011-tools-test-live-py-falha-por-gpu-indisponivel-nao-por-regres
  - 2026-08-19-legado-012-medir-eco-py-subestima-o-eco-por-construcao-19-08-2026
  - 2026-08-19-legado-013-rotulagem-por-energia-simultanea-mede-o-oposto-quando-os-can
  - 2026-08-19-legado-014-os-canais-do-mp3-saem-desalinhados-por-200-ms-19-08-2026
  - 2026-08-19-legado-015-print-com-emoji-derruba-script-no-console-desta-maquina-19-0
  - 2026-08-21-legado-016-o-alinhamento-ao-vivo-demora-10-min-para-se-recuperar-de-um
  - 2026-08-21-legado-017-medir-aec-py-nao-compara-antes-depois-as-janelas-mudam-21-08
  - 2026-08-26-legado-018-audio-comprimido-antes-de-transcrever-zera-o-arquivo-inteiro
  - 2026-08-30-legado-019-warnings-catch-warnings-nao-isola-por-thread-nao-serve-para
  - 2026-08-30-legado-020-o-soundcard-fabrica-silencio-pelo-relogio-quando-o-loopback
  - 2026-08-30-legado-021-o-acoplamento-nao-prediz-se-o-cancel-echo-vai-ajudar-ou-pior
  - 2026-08-30-legado-022-tools-test-alinhamento-py-esta-vermelho-desde-que-nasceu-30
  - 2026-08-30-legado-023-relatorio-que-resume-uma-amostra-vazia-inventa-conclusao-30
  - 2026-08-30-legado-024-a-rede-de-seguranca-do-cancel-echo-mede-o-rms-global-e-nunca
  - 2026-08-30-legado-025-o-erle-publicado-do-cancel-echo-mede-um-regime-que-o-app-nao
  - 2026-08-30-legado-026-a-biblioteca-nao-enxerga-as-transcricoes-do-tools-transcreve
  - 2026-09-02-legado-027-ler-200-de-287-linhas-e-declarar-li-a-transcricao-inteira-02
  - 2026-09-25-legado-028-npu-quebra-no-transcrever-py-e-video-sem-som-quebra-o-decode
  - 2026-10-11-legado-029-migracao-de-config-persistida-antes-do-exe-novo-re-arma-o-au
  - 2026-10-11-legado-030-duas-def-de-mesmo-nome-no-reco-py-a-2a-esconde-a-1a-sem-erro
---
# Armadilhas do Reco

Coisas que **parecem** funcionar e não funcionam, com o sintoma que elas produzem
e a causa real. Ler antes de "consertar" qualquer uma delas — várias já custaram
tempo e estão aqui justamente para não custarem de novo.

Padrão herdado do `nomura-bi`. Cada entrada: **sintoma → causa → o que fazer**.

Esta página é **gerada** de `docs/armadilhas.d/` (um arquivo por armadilha) e fica fora do git:
entrada nova é `python tools/visoes.py novo "título do sintoma"`, nunca edição aqui (12/10/2026).

---

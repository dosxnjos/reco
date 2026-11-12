## Relatório de execução — Fase 1 (2026-11-11, sessão 4c65eb01)

> **Parcial:** passos 1 a 11 feitos (o 11 só como conferência da trava, sem commit: quem commita é a sessão
> principal). Passos 12 em diante (publicar, esperar a escolha, podar, armadilha, docs) ficam com a sessão
> principal.

Vitrine: `design/vitrine.html` (abrir no navegador; standalone). Foi publicada como Artifact em 11/11/2026 e o
Gabriel escolheu por ela (A padrão, B e C como skins). Na mesma noite ele decidiu voltar a só HTML, sem Artifact
(com duas contas do Claude, o navegador abre os artefatos de uma só e o link dava 404), e o artefato foi apagado
a pedido dele. Daqui em diante a vitrine se entrega como o `.html` do repo.

Frescor: 0 commits em `reco.py`/`tray.py` desde `7c5c1a1`. O `CLAUDE.md` subiu de 5210 para 5432 bytes
durante a fase (outra frente acrescentou a seção do motor `engine/`); continua abaixo de 5900.

## Provas por passo

| passo | comando | o que veio |
| --- | --- | --- |
| 1 | `git log --oneline 7c5c1a1..HEAD -- reco.py tray.py; ls design; wc -c < CLAUDE.md; ls …/fase-0-relatorio.md` | nenhum commit; `ls: cannot access 'design'`; `5210`; o relatório existe (parcial: Bloco A) |
| 2 | `grep -c "^## " design/PRODUCT.md` | `11` |
| 2 (setup) | `IMPECCABLE_CONTEXT_DIR=design node …/context.mjs > temp/ctx.txt && grep -c NO_PRODUCT_MD temp/ctx.txt` | `0` (antes do PRODUCT.md o mesmo script imprimia `NO_PRODUCT_MD`) |
| 3 | `grep -cE "^### R[0-9]+" DESIGN.md; grep -cE "^- \*\*teste:\*\*" DESIGN.md` | `15` e `15` |
| 4 | laço dos 12 termos | nenhuma linha `FALTA` |
| 4 (tabela) | `grep -cE '^\| ?(1[0-9]\|[1-9]) ?\|' design/DESIGN.md` | `19` |
| 5 | `grep -oE 'data-direcao="[a-c]"' tokens.css \| sort -u \| wc -l; grep -Eic 'seal\|#0f5f73\|#5db6c8\|selo' tokens.css` | `3`; `0` |
| 6 | `node design/montar-vitrine.cjs && grep -Ec '(src\|href)="(https?:)?//' design/vitrine.html; wc -c < design/vitrine.html` | `0`; `116427` (limite 450000) |
| 7 | `node design/testar-anti-pulo.cjs; echo "saída=$?"` | `anti-pulo: 0 diferenças em 23868 medições`, `saída=0` (cerca de 25 s) |
| 8 | `node design/testar-anti-pulo.cjs --sabotar; echo "saída=$?"` | `FALHA escala=1 tela=gravar estado=gravando-ao-vivo … direcao=a área=status base=500,970.56,400,32.38 agora=500,970.56,400,48.56` e outras; `anti-pulo: 1920 diferenças em 23868 medições`; `saída=1` |
| 9 | `node design/testar-contrato.cjs; echo "s=$?"` | 47 linhas `ok`, `contrato: 0 falhas`, `s=0` (cerca de 1 min 35 s) |
| 9 (sabotagem) | `node design/testar-contrato.cjs --sabotar; echo "s=$?"` | `FALHA clique-move [a] gravar/motor-subindo "Nova 2.0" base=587.83,453.56,91.53,26 … apertado=588.74,453.82,89.7,25.48 …`; `contrato: 688 falhas`; `s=1` |

Os números das linhas 7 a 9 são da versão final, depois das correções do passo 10.
| 10 | `ls temp/vitrine-capturas/*.png \| wc -l` | `21` (3 direções × 2 temas na tela Gravar, 14 telas lado a lado e 1 de celular a 390 px) |
| 10 (testes após as correções) | `node design/montar-vitrine.cjs && node design/testar-anti-pulo.cjs && node design/testar-contrato.cjs` | `anti-pulo: 0 diferenças em 23868 medições`, `contrato: 0 falhas`, `s=0` |
| 11 (conferência) | `git add <os 8> && pre-commit run --files <os 8>` e depois `git restore --staged <os 8>` | gitleaks Passed, check-added-large-files Passed, trava-tamanho Passed; nada ficou no stage (`?? design/`) |

Conferências extras: o `montar-vitrine.cjs` é determinístico (mesmo md5 ao rodar de novo); o
`grep -rlE 'C:[\\/]Users|Gabriel dos Anjo[s]|App[D]ata' design` não acha nada; a página a 390 px tem
`scrollWidth` 390 (sem rolagem lateral); nenhum erro de console nas capturas.

## Passo 10: resumo da crítica

Revisão feita por um subagente isolado (a Avaliação A do `impeccable critique`), que leu as 21 capturas e o
código sem ver os testes. O detector do `impeccable` (Avaliação B) rodou uma vez, mas em modo degradado:
faltam os módulos de parser no ambiente, ele cai para regex e acusou 0 achados. Quem cobre contraste,
tokens e emoji é o `testar-contrato.cjs`.

**O que a crítica apontou:** a C tem identidade própria, mas A e B estavam parecidas demais (mesmas abas
sublinhadas, mesma pílula de estado, mesmo controle e densidade, só a cor e a fonte do relógio mudavam).
Na C, o âmbar significava cinco coisas. Pela regra do passo 10, a A, a mais genérica, foi refeita antes de
mostrar.

**O que mudou (uma rodada de correção):**
- **A refeita:** contador num visor rebaixado com contorno coral quando grava, lâmpada com brilho no lugar da
  pílula, abas, botões e seletor em pílula com camadas de tom, medidores finos (5 px), busca em pílula.
- **B separada:** algarismos alinhados no relógio (antes saía "oo:42:17"), traço sob o cronômetro que fica
  vermelho gravando, estado em itálico Sitka, nomes de arquivo em Segoe (não cortam), pauta só no painel do
  texto e escondida atrás de botões.
- **C:** o âmbar ficou só para "gravando" (ponto, contorno do visor, pico, marca). Gravar virou tecla escura
  com ponto âmbar, a aba ativa é marcada em tinta, a faixa de status clara deixou de ser preta e o escuro
  ganhou superfícies mais claras que o visor.
- **Nas três:**
  - a aba bloqueada sem risco (fica o cadeado);
  - fala ao vivo com degradê no topo e "Eu"/"Outros", com cores diferentes;
  - "Preparando" em cinza, não na cor da gravação;
  - botão desabilitado com fundo próprio, sem cara de clicável;
  - erro sem o "Tentar de novo" (repetia o Gravar);
  - Biblioteca sem a coluna Data (está no nome), duração alinhada à direita e altura das linhas que fecha
    em linhas inteiras (8, 7 e 9 por direção);
  - Opções com degradê no fim, para mostrar que rola.

**O que ficou como estava, com motivo:**
- As seis saídas do estado Parado continuam à vista: o Insumo 3 manda tudo visível. "Ouvir" ocupou a vaga
  do secundário e as outras 4 ficaram no painel.
- O texto do status gravando segue o do `reco.py:3877-3896`, porque o teste de texto longo depende dele.
  Mudar a ordem ou tirar o "mic:" fica para a Fase 3, se o Gabriel quiser.
- O "Transcrever" esmaecido durante a transcrição não virou etiqueta.

Recomendação do revisor: C, trazendo da B a fala ao vivo em Sitka. É opinião dele, não decisão.

**Rodada de confirmação** (a única, o mesmo revisor sobre as capturas refeitas). O veredito, nas palavras dele:

1. A e B parecidas demais: **parcial**. "O contorno agora difere [...] Mas as réguas de medidor e ganho
   (trilha fina, risco vermelho, bolinha), a grade do estado Parado e a tela de Opções continuam idênticas."
2. A com cara de molde: **parcial**; "bege + coral" no claro: **não resolvido**.
3. Âmbar da C: **parcial**. "O que ainda pesa é o ponto âmbar dentro do botão Gravar em repouso."
4. Novos: na C o Gravar desabilitado (motor subindo) parecia clicável; na B os botões de Parado e Erro
   ficam deslocados pela calha da margem; a 1ª linha do texto ao vivo ainda aparece cortada na B e na C.

**O que se fez depois do veredito**, só o que era barato e preciso, sem nova rodada de revisão:

- o claro da A passou de bege para grafite claro e frio (o coral ficou só no que grava);
- o Gravar da C em repouso perdeu o ponto âmbar (círculo vazado neutro);
- o Gravar desabilitado da C passou a aparecer apagado, como na A e na B.

**O que ficou aberto, para a sessão principal decidir:**

- medidor próprio da A (em blocos ou ponteiro), para não repetir o fio da B;
- Parado e Opções com a mesma grade nas três;
- a calha da margem na B;
- o corte da 1ª linha do texto ao vivo na B e na C.

A escolha do Gabriel resolve a maior parte: o que não for escolhido sai na poda do passo 14.

## As três direções, em português simples

- **A "Fita".** Parece um gravador de fita moderno: grafite (quente no escuro, frio no claro), um contador grande num visor e
  uma lâmpada laranja-avermelhada que acende quando grava. É a mais parecida com o Reco de hoje, só que
  arrumada. Serve para quem quer continuidade.
- **B "Caderno".** Parece um caderno de linhas: papel branco azulado, tinta azul de caneta, margem vermelha
  e o texto da conversa em letra de livro (Sitka) sobre a pauta. Leve e arejada. Serve para quem quer que o
  texto seja o centro.
- **C "Instrumento".** Parece um aparelho de medição: painel de alumínio, visores pretos embutidos,
  medidores em blocos com escala em dB e um único sinal âmbar que só aparece gravando. Cantos retos, mais
  informação por centímetro. Serve para quem quer ver de relance que os dois canais estão entrando.

## completei:

- **Casca da vitrine pela ferramenta Artifact:** o `montar-vitrine.cjs` gera dois arquivos.
  - `design/vitrine.html`, standalone com doctype, para os testes e para abrir local;
  - `temp/vitrine-publicar.html`, o mesmo conteúdo sem doctype, html, head e body, começando por
    `<title>Vitrine do Reco</title>` e pela meta `claude:viewport-fit-sides`.
  - O gerador recusa a saída se sobrar tag de esqueleto ou se ela não começar por `<title>`.
- **Janela simulada clicável:** abas, Gravar, Parar, Pausar, saídas, Detalhes, busca e ações andam entre os
  estados pelo mesmo `definir()`. O Gabriel testa "clicar e nada se mexer" com o próprio mouse.
- **A própria vitrine não pula:** os botões de estado de cada tela ficam empilhados na mesma célula da
  grade (o grupo inativo some por `visibility`). Trocar de tela não muda a altura dos controles nem empurra
  as janelas. Conferido a 390, 800 e 1400 px: em cada direção, a janela fica na mesma posição nos 27
  estados.
- **O `testar-contrato.cjs` também confere** que todo `<use href>` aponta para um ícone que existe, nos 27
  estados (ícones trocados em tempo de execução, como o cadeado).
- **Ícones da bandeja desenhados:** parado é a marca de dois meios-círculos em traço, gravando é a mesma
  marca cheia. A forma muda, não só a cor (R12).

### Decisões técnicas — Fase 1

| id | decisão | confiança | reverte se |
| --- | --- | --- | --- |
| F1-E1 | Dois arquivos de saída no `montar-vitrine.cjs` (standalone com doctype + `temp/vitrine-publicar.html` sem esqueleto); só o primeiro é versionado | alta | a ferramenta Artifact passar a aceitar página com esqueleto próprio |
| F1-E2 | Três janelas lado a lado (uma por direção, clonadas do mesmo `<template>`), e o controle Direção filtra; os testes medem só a `[data-area=janela]` visível, então a Fase 3 com uma janela usa o mesmo código | média | o `--url` da Fase 3 precisar de outra forma de achar a janela |
| F1-E3 | Cores da casca da vitrine num bloco marcado de `tokens.css` (`--casca-*`, com o contrato de tema do Artifact), para o modelo ficar sem hexadecimal | média | a poda do passo 14 achar melhor mover a casca para fora dos tokens do app |
| F1-E4 | Botão indisponível usa `disabled` (fora do Tab); aba bloqueada usa `aria-disabled` e continua no Tab; o R9 cobra "todo botão visível sem `disabled`" | alta | — |
| F1-E5 | Estado Parado: "Ouvir" na vaga do secundário e as outras 4 saídas no painel (o Insumo 3 dizia 5 no painel); a regra "tudo à vista" vale igual, e a linha de botões não fica com buraco | média | o Gabriel preferir as 5 no painel |
| F1-E6 | Na tela, a fala ao vivo rotula "Eu"/"Outros"; o `.txt` continua com "Eu"/"Interlocutor(es)" do `reco.py` | média | ele querer o mesmo rótulo do arquivo |
| F1-E7 | Biblioteca sem a coluna Data (a data já está no nome do arquivo; vai no `title` da linha); altura da linha calculada para fechar em linhas inteiras (`--lib-linhas` por direção) | média | ele sentir falta da coluna |
| F1-E8 | Ícones Lucide 1.71.0 copiados do pacote `lucide-static` como miolo de `<symbol>` dentro do `montar-vitrine.cjs` (licença ISC num comentário da página); traço e preenchimento vêm do CSS | alta | — |
| F1-E10 | As sombras do modelo usam `rgb(0 0 0 / x)` fora do `tokens.css`; a checagem de hexadecimal não as vê. Ficam como exceção registrada (preto com alfa, igual nos dois temas) | média | a Fase 3 querer sombra por tema (aí vira token `--sombra-*`) |
| F1-E11 | "Detalhes" (painel com o erro inteiro) existe só no `erro` da tela Gravar, como o md pede; nos erros da Biblioteca e do Arquivo, o texto inteiro fica no `title` do status e no cartão da área | média | a Fase 3 trazer erros longos nessas telas (aí o botão vale para todo status de erro) |
| F1-E9 | Um subagente fez só a Avaliação A da crítica; o detector (Avaliação B) rodou no contexto principal e degradado (sem parser, 0 achados) | média | instalar os módulos do detector e rodar de novo |

## Desvios do md

- **Passo 10:** as capturas foram feitas por script Node com Playwright (permitido pela sessão principal),
  não pelo MCP. O servidor `python -m http.server 8765` rodou como tarefa de fundo da ferramenta e foi
  parado ao fim do passo.
- **Passo 11:** sem commit nem push, por ordem da sessão principal. Só a conferência da trava
  (`git add` + `pre-commit run --files` + `git restore --staged`).
- **Skill `impeccable`:**
  - o `concept-seed.mjs` rodou duas vezes e não imprimiu nada (saída 0); as direções vieram fixadas pelo
    roadmap, o que a skill aceita ("brief-pinned beats the roll");
  - não houve página de decisão nem geração de imagem paga (a escolha é a vitrine do passo 12);
  - o DESIGN.md foi escrito no passo 3, como o md manda, e ajustado depois das correções.
- **Uma edição de texto foi feita por Python** (inclusão dos tokens de status da C no `tokens.css`), contra
  a regra da casa. O resultado foi conferido pelo teste de contrato e pelas edições seguintes, feitas por
  `Edit`.
- **Insumo 3, linha 4:** 4 saídas no painel + "Ouvir" no secundário, não 5 no painel (F1-E5).

## Arquivos tocados

- Criados, para o commit da sessão principal (os 8 do passo 11):
  - `design/PRODUCT.md`, `design/DESIGN.md`, `design/tokens.css`, `design/vitrine.modelo.html`;
  - `design/vitrine.html` (gerado), `design/montar-vitrine.cjs`, `design/testar-anti-pulo.cjs`,
    `design/testar-contrato.cjs`.
- Este relatório é um 9º arquivo, fora dos 8 do passo 11: `roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-1-relatorio.md`.
- Fora do git (`temp/`): `temp/vitrine-publicar.html`, `temp/vitrine-capturas/*.png` (21),
  `temp/ctx.txt`, `temp/contrato*.txt`, `temp/sab.txt`, `temp/detect.json`.
- Não tocados: `reco.py`, `tray.py`, `engine/`, `tools/`, o md da fase e o índice.

## Passos 13 e 14b (11/11 22:4x a 12/11 00:40)

- Passo 13: escolha do Gabriel registrada ("opção A, mas gostei das outras duas. acho que dá pra ter opção de
  skin pra implementá-las também"); `grep "Direção escolhida"` e `grep "decidido em"` → 1 linha cada.
- Passo 14 (poda) superado; passo 14b (skins) feito por workflow (implementar → revisor visual + revisor de
  testes → corrigir). A abre por padrão; Opções › Visual troca a skin (`data-acao="skin"`).
- Revisão: 10 achados (2 altos: contraste do seletor Gravação · Nota no escuro; testes que não conferiam a skin
  medida), todos corrigidos. Também: reset de botão com especificidade baixa (`:where`), pauta da B presa ao
  texto, marcador "Eu/Outros" na 1ª linha do ao vivo, camada de tela escondida que roubava clique (bug antigo).
- Provas finais (12/11 00:40, depois de trocar o texto do "motor subindo" de "uns 5 segundos" para "só um
  instante", já que a Fase 0 mediu ≈ 1 s com a máquina livre): `anti-pulo: 0 diferenças em 23868 medições`,
  `contrato: 0 falhas`, sabotagens `anti-pulo=1` e `contrato=1`, `grep -c data-acao="skin"` → 4.
- Mutações da revisão (definir ignorando a direção; botão que se move no hover) reprovam no contrato.

### Decisões técnicas — Fase 1 (14b)

- Visual e Aparência sobem para o topo de Opções na interface real (Fase 3); a vitrine fica com a ordem antiga.
  Motivo: é o que muda a cara do app e quem abre Opções vê sem rolar. Confiança média; reverte se o Gabriel
  preferir os dispositivos no topo (uso mais frequente).
- Sem Artifact (regra da casa desde 11/11): a vitrine se entrega como `design/vitrine.html`.

### Pendências que vão para a Fase 3

- Regra "1ª linha do ao vivo inteira" (`rolarAoVivo`) só existe na vitrine: levar para o app.
- "Transcrição pronta": a fileira de 3 botões corta "Abrir trans…" e "Copiar ca…" nas três skins.

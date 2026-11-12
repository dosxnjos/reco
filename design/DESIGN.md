---
name: Reco
description: Gravador de mesa do Windows (mic + sistema, transcrição local); janela pequena ancorada à bandeja, usada de relance durante a chamada.
status: proposta da Fase 1 (11/11/2026), três direções em escolha; nada aprovado pelo Gabriel ainda
janela:
  largura: 400px
  altura: 560px
  areas-globais: { titulo: 40px, abas: 44px, conteudo: 440px, status: 36px }
tokens: design/tokens.css (fonte única de cor, fonte, raio, densidade e das alturas)
fontes: [Segoe UI Variable, Sitka, Bahnschrift, Cascadia Mono]  # só fontes do Windows (F1-D10)
icones: Lucide 1.71.0 (licença ISC), inline como <symbol> na vitrine
direcoes:
  a: Fita
  b: Caderno
  c: Instrumento
testes: [design/testar-anti-pulo.cjs, design/testar-contrato.cjs]
---

# Reco: design

## Visão geral

**North Star:** um gravador de mesa que some quando trabalha: grava sem cerimônia, mostra o que importa
e nunca se mexe sozinho.

O Reco é usado por segundos, no meio de uma chamada, numa janela de 400 × 560 presa à bandeja. A tela
serve a tarefa (modo Operate): o que muda entre estados é texto, cor e opacidade, nunca tamanho nem
lugar. A identidade mora nos detalhes de cada direção (cor, letra, forma dos medidores), não em
enfeite. Produto e público: [PRODUCT.md](PRODUCT.md). Por que existe: roadmap
`roadmap/2026-11-11-melhoria-reco-em-rust.md` (D4, D5) e o md da Fase 1.

## Princípios

1. **Parado é bonito.** Janela fixa, áreas reservadas, nada aparece empurrando nada.
2. **Tudo à vista.** Cada ação tem botão com texto; nenhuma só no hover, nenhuma navegação por link.
3. **Uma ação principal por estado**, com o verbo do que acontece ("Salvar e copiar caminho").
4. **O motor demora, a tela não.** Espera vira estado com texto, e o Gravar nunca espera a GPU (D12).
5. **O produto é o arquivo.** Caminho, transcrição e pasta sempre a um clique.

## Contrato de tela

As regras valem para a vitrine e para a interface real da Fase 3, que roda os mesmos dois testes com
`--url`. Cada regra diz qual verificação a cobre: `anti-pulo` é `design/testar-anti-pulo.cjs`
(caixas de área), `contrato` é `design/testar-contrato.cjs` (uma linha `ok`/`FALHA` por regra).

### R1 Janela fixa de 400 × 560

Px lógicos (CSS); o WebView2 multiplica pela escala do Windows. Nunca cresce, então a âncora na
bandeja vale sempre. Tokens `--janela-largura` e `--janela-altura`.

- **teste:** anti-pulo, caixa de `janela` igual em toda tela, estado, tema, texto e versão, e igual a
  400 × 560 na linha de base.

### R2 Cada área com altura reservada

Toda área com nome (`data-area`, lista em "Áreas e estados") tem altura explícita por token e
`flex: none`; o conteúdo variável cabe dentro dela ou rola por dentro.

- **teste:** anti-pulo, caixa de cada `data-area` igual à linha de base da direção e escala (as globais
  contra todas as telas, as de tela contra a mesma tela).

### R3 Status em uma linha

A faixa `status` é uma linha só, com reticências; o texto inteiro vai no `title` e, no erro, no painel
de detalhe.

- **teste:** contrato R3, `white-space: nowrap`, `text-overflow: ellipsis` e `overflow: hidden`; com
  texto longo, `scrollWidth > clientWidth` e `title` igual ao texto inteiro.

### R4 Números com largura fixa

Cronômetro, ganho, duração, porcentagem e contagens levam `data-num` e `tabular-nums`.

- **teste:** contrato R4, todo `[data-num]` com `font-variant-numeric` contendo `tabular-nums`.

### R5 Transição só de opacidade e cor

Nada de transição de tamanho, posição ou `transform`. `@keyframes` só com `opacity`.

- **teste:** contrato R5, `transition-property` só com opacity, color, background-color, border-color,
  outline-color, fill e stroke (ou duração 0) em todo elemento; keyframes só com opacity.

### R6 Clique e hover não movem o botão

Sem `transform` nem mudança de borda, padding ou fonte em `:hover` e `:active`; o botão só muda de cor.

- **teste:** contrato R6, caixa de cada botão visível igual antes, com o mouse em cima, apertado
  (`mouse.down`) e depois de soltar.

### R7 Condicional some por opacidade ou visibilidade

Elemento que aparece e some usa `visibility` (com opacidade por cima), nunca `display: none` nem o
atributo `hidden`, que liberam o espaço. Rótulo que muda troca o texto no mesmo elemento.

- **teste:** contrato R7, o `display` calculado de cada elemento da janela é o mesmo em todos os estados
  de todas as telas.

### R8 Área que rola reserva a calha

`overflow: auto` sempre com `scrollbar-gutter: stable`: a barra que aparece não come a largura.

- **teste:** contrato R8, todo elemento com `overflow` `auto` ou `scroll` tem `scrollbar-gutter: stable`.

### R9 Foco visível e tudo pelo Tab

`:focus-visible` com contorno de 2 px ou mais. Botão indisponível usa `disabled` (fora do Tab); aba
bloqueada usa `aria-disabled="true"` e continua no Tab, para o motivo ser lido. Sem `tabindex` móvel.

- **teste:** contrato R9, percorrer a janela com Tab: cada foco tem contorno ≥ 2 px e todo botão visível
  sem `disabled` é alcançado.

### R10 DPI pelo WebView2

Só px lógicos e ícones SVG; nenhum bitmap na janela.

- **teste:** contrato R10, nenhum `<img>` nem `background-image` com png, jpg, gif ou bmp dentro da
  janela; ícones só `<svg>`.

### R11 Claro e escuro pelo sistema, com escolha manual

Sem escolha, a janela segue o sistema; em Opções › Aparência dá para fixar Claro ou Escuro
(`data-tema`), e a escolha vence o sistema.

- **teste:** contrato R11, sem `tema` os fundos de `colorScheme` claro e escuro diferem; com
  `tema=claro|escuro` o fundo é o da escolha, nos dois esquemas do sistema.

### R12 Cor nunca é o único sinal

Todo sinal de estado (`data-sinal`) leva ícone e texto; o ícone da bandeja gravando muda de forma, não
só de cor.

- **teste:** contrato R12, todo `[data-sinal]` tem um `<svg>` e texto não vazio.

### R13 Ícones Lucide, nunca emoji

Ícones Lucide inline (licença ISC citada na vitrine), cada um com `data-lucide`. Nenhum emoji nem
glifo como ícone (hoje há "📄", "⚡", "✓" e "⚠" no `reco.py`).

- **teste:** contrato R13, nenhum `\p{Extended_Pictographic}` no texto visível e todo SVG de ícone com
  `data-lucide` (a marca do Reco leva `data-marca`).

### R14 Movimento reduzido zera tudo

Com `prefers-reduced-motion: reduce`, transições e piscar vão a zero; o ponto de gravação fica aceso.

- **teste:** contrato R14, com `reducedMotion: 'reduce'` todas as durações são 0 e nenhuma animação
  roda.

### R15 Toda ação e toda tela à vista

Navegação por abas (botões `role="tab"`), nenhum link de texto como navegação, nada que só apareça no
hover; fora da barra de título, todo botão tem texto visível.

- **teste:** contrato R15, nenhum `<a>` na janela, abas com `role="tab"`, todo botão fora de `titulo`
  com texto visível, nenhuma regra `:hover` que mude `display`, `visibility` ou `opacity` de outro
  elemento. O mesmo teste cobra o contraste (texto comum ≥ 4,5:1, grande ≥ 3:1) e nenhum hexadecimal
  fora de `tokens.css`.

## Áreas e estados

Nomes fixos, que a Fase 3 reusa (F1-D12):

| tela | áreas |
| --- | --- |
| globais | `janela`, `titulo`, `abas`, `conteudo`, `status` |
| Gravar | `cronometro`, `medidores`, `acoes`, `painel` |
| Biblioteca | `busca`, `lista`, `acoes-lib` |
| Arquivo | `origem`, `acoes-arq`, `progresso` |
| Opções | `opcoes-lista` |

Estados por tela (o teste percorre todos):

- **Gravar:** `motor-subindo`, `pronto`, `gravando`, `gravando-ao-vivo`, `nota-gravando`, `pausado`,
  `parado`, `transcrevendo`, `transcricao-pronta`, `erro`, `erro-detalhe`.
- **Biblioteca:** `vazia`, `lista`, `selecionada`, `transcrevendo-item`, `resumindo`,
  `busca-sem-resultado`, `erro`.
- **Arquivo:** `nada-escolhido`, `escolhido`, `transcrevendo`, `convertendo`, `pronto`, `erro`.
- **Opções:** `normal`, `durante-gravacao`, `dispositivo-ausente`.

Variações globais: tema claro e escuro, texto normal e longo (PT e EN), versão nova sim e não.

- **Motor subindo:** "Gravar" desabilitado com o motivo no status ("Preparando o motor…"). Nada gira: o
  indicador pulsa por opacidade. Dura a partida do motor congelado, `exe_selftest` da Fase 0: ≈ 5,4 s
  (7,4 s na primeira). A GPU nunca segura o Gravar (D12).
- **Erro:** ícone + texto no status, cortado por reticências, e o botão "Detalhes" na própria faixa.
  "Detalhes" abre um painel sobreposto ao `conteudo`, do mesmo tamanho, com o texto inteiro e "Copiar".
  O erro de hoje é cortado em `[:80]`/`[:110]` no `reco.py`; no detalhe ele aparece inteiro.
- **Gravando ou transcrevendo:** a aba Arquivo fica bloqueada com cadeado e o motivo (F1-D7); as outras
  continuam navegáveis, e as ações que disputam o motor ficam desabilitadas com o motivo no status.

## Condutor de estados

Contrato com a Fase 3: a página aceita `?direcao=&tela=&estado=&tema=&texto=&versao=` e expõe
`window.vitrine.definir({direcao, tela, estado, tema, texto, versao})` com os mesmos nomes, mais
`window.vitrine.direcoes`, `telas` e `estados` (objeto tela → lista).

- `direcao`: `a`, `b`, `c` (a vitrine aceita também `todas`, lado a lado; os testes sempre passam uma).
- `tela`: `gravar`, `biblioteca`, `arquivo`, `opcoes`. `estado`: um dos estados da tela.
- `tema`: `sistema`, `claro`, `escuro`. `texto`: `normal`, `longo-pt`, `longo-en`. `versao`: `sim`, `nao`.

A interface real da Fase 3, no modo de backend falso, expõe o mesmo condutor, e os dois testes rodam
contra ela com `--url <endereço>`. Os testes medem a janela visível (`[data-area=janela]` que está
na tela), então a vitrine com três janelas e o app com uma usam o mesmo código.

## Telas

Inventário do Reco de hoje (relatório 1 § 1, 19 linhas) e onde cada função mora. Nada some sem motivo.

| # | funcionalidade de hoje | onde fica |
| --- | --- | --- |
| 1 | janela sem moldura, título arrastável, minimizar e fechar, fade-in | barra de título própria em todas as telas; o fade-in fica (é só opacidade) |
| 2 | VU de mic e de sistema; arrastar o medidor ajusta o ganho 0×–10× | Gravar › `medidores`; o ganho vira controle visível (alça, número "8,0×", setas do teclado), F1-D11 |
| 3 | estados pronto, gravando, pausado, parado, ocupado; cronômetro e ponto piscando | Gravar › `acoes` e `cronometro`; o ponto pisca por opacidade e fica aceso com movimento reduzido |
| 4 | depois de parar, o clique salva e copia o caminho entre aspas; Excluir (Lixeira), Reproduzir; menu de hover com 4 saídas | botão principal "Salvar e copiar caminho" em `acoes`, com "Ouvir" na vaga do secundário; as outras 4 saídas (Salvar e transcrever, Só salvar, Transcrever e apagar o áudio, Excluir para a Lixeira) são botões no `painel`, todas à vista |
| 5 | uma linha de status e o link "Abrir transcrição" | faixa `status` comum às telas; "Abrir transcrição" é botão com vaga fixa no `painel` |
| 6 | Parar da transcrição disparada pela tela de gravar | Gravar › `painel`, variante "transcrevendo", com barra de progresso |
| 7 | ao vivo: painel de 8 linhas e passada final | Gravar › `painel`, variante "ao vivo", rolando por dentro |
| 8 | modo nota, sem entrada hoje | Gravar › seletor "Gravação · Nota" em `acoes` (desenho aqui; ligar é Fase 3) |
| 9 | Opções: entrada, saída (Auto console, Auto comunicação, manual), atualizar dispositivos, pasta, Processar em, idioma, tema, ao vivo, atalho | aba Opções, tudo visível, rolando por dentro; o tema livre sai (F1-D6) |
| 10 | telas por links de texto, bloqueadas durante a gravação | `abas` Gravar, Biblioteca, Arquivo, Opções; a que conflita fica bloqueada com o motivo (F1-D7) |
| 11 | Transcrever: escolher arquivo, Transcrever, Parar, status, Abrir pasta | aba Arquivo, ação "Transcrever", com progresso em % |
| 12 | Biblioteca: busca por nome e conteúdo, lista, Reproduzir, Transcrever, Abrir txt, Resumo IA, Excluir, Abrir pasta, Atualizar, duplo clique toca | aba Biblioteca; as ações saem do hover e ganham rótulo visível |
| 13 | Resumo IA por `claude -p` | Biblioteca › ação "Resumo IA" + estado `resumindo` |
| 14 | Converter para MP3 16 kHz mono 64k | aba Arquivo, ação "Converter para MP3" sobre a mesma origem (F1-D4) |
| 15 | bandeja: hover mostra sem foco, clique fixa, menu nativo, balão, ícone vermelho gravando | fora da janela (casco, Fase 3); aqui só os dois ícones da bandeja, ocioso e gravando, com forma diferente além da cor |
| 16 | atualizações: modelo sozinho, versão nova como link | modelo: mensagem no `status`; versão nova: vaga fixa com ícone na barra de título |
| 17 | i18n PT/EN, frase PT é a chave | Opções › Idioma; o teste roda com texto longo em PT e em EN |
| 18 | atalho Ctrl+Shift+R por `.lnk` | Opções › Atalho de teclado (criar ou remover) |
| 19 | instância única e as CLIs `--selftest`/`--transcribe` | sem tela, de propósito: são contrato (D6, D7), não interface |

**Cortado, com motivo:** o tema livre (cor de fundo e de destaque no seletor de cor). É o que
desencontra combos e lista do resto, e o Gabriel usa o padrão. Entra Opções › Aparência: Sistema ·
Claro · Escuro; as chaves `bg_color` e `accent_color` continuam no config, ignoradas pela interface
nova (F1-D6).

**Ícones da bandeja:** ocioso é a marca do Reco em traço (dois canais, L e R); gravando é a mesma
marca com um disco cheio no canto. A forma muda, não só a cor (R12).

## Direções

Três identidades para o Gabriel escolher na vitrine (`design/vitrine.html`). Mesma estrutura, mesmas
áreas e mesmos testes; mudam paleta, letra, densidade e forma. Cada uma está inteira em
`tokens.css` (bloco `[data-direcao="x"]`, claro e escuro) e nas regras de forma da vitrine.

### A "Fita"

Continuidade com o Reco de hoje, amadurecida. O mundo é o gravador de fita: corpo de grafite quente,
contador grande num visor rebaixado e uma lâmpada de gravação que acende com brilho. O coral de hoje vira
um vermelho-laranja de lâmpada acesa, usado só no que grava (botão Gravar, lâmpada, contorno do visor
gravando). Segoe UI Variable, cronômetro de 44 px em Display, camadas de tom em vez de linhas, abas e
botões em pílula, medidores finos. Escuro é a casa dela; o claro é grafite claro, não creme.

### B "Caderno"

Claro primeiro, papel e tinta, o texto como protagonista. O mundo é o caderno de linhas: papel branco
azulado com pautas, margem vermelha à esquerda do painel, tinta azul de caneta nas ações. Sitka no
cronômetro (algarismos alinhados), nos títulos e no texto da transcrição, Segoe UI nos controles e nos
nomes de arquivo. Mais ar entre as coisas, raios pequenos, botões de contorno, abas sublinhadas a tinta;
gravando, o traço sob o cronômetro fica vermelho. A pauta do painel acompanha a altura da linha do
texto ao vivo e some atrás de botões.
O escuro é o caderno à noite: azul-marinho fundo com tinta clara.

### C "Instrumento"

Console de medição. Painel de alumínio quase monocromático, visores escuros embutidos e um único
sinal âmbar, reservado para "gravando" (ponto, contorno do visor, pico do medidor, marca). Bahnschrift
nos números e rótulos curtos (sem caixa-alta espaçada), Segoe UI no resto. Medidores segmentados com
escala em dB à vista, cantos retos, densidade maior (9 linhas na Biblioteca), abas como teclas de
seletor com um traço que escurece na ativa, teclas escuras para Gravar e Parar.

Nas três, a fala ao vivo rotula "Eu" e "Outros" (o `.txt` continua com os rótulos do `reco.py`).

Direção escolhida: (preencher no passo 13, com as palavras do Gabriel).

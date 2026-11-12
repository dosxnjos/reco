# Reco em Rust: Fase 1 — Identidade visual e contrato de tela

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: [fase-0](2026-11-11-melhoria-reco-em-rust-fase-0.md) · seguinte: [fase-2](2026-11-11-melhoria-reco-em-rust-fase-2.md) · Base: Reco `7c5c1a1` (2026-11-11)

> Toda prova abaixo roda no **Git Bash** (`wc`, `for … do`, `$?` e `<` não funcionam no PowerShell).

## Por que esta fase

- A queixa nº 1 do Gabriel é a janela que "não para de ficar se mexendo" a cada clique, e ele quer o Reco "bonito, que nem o Lacre".
- O Tauri sozinho não impede layout que pula (índice, D4): o que impede é um contrato de tela escrito e testado antes de existir app.
- Esta fase cria a identidade própria do Reco em `design/` (D5), com 2 ou 3 direções numa vitrine para o Gabriel escolher.
- Ela também cria o teste automático que prova que nada muda de tamanho nem de lugar; a Fase 3 roda o mesmo teste contra a interface real.
- Não toca em `reco.py` nem em `tray.py`: o app que o Gabriel usa hoje fica intacto do começo ao fim, sem recompilar.

## O que ler antes

- `C:\Dev\cerebro\projetos\reco.md` (hub; o hook `guarda-escrita` cobra) e `C:\Dev\Reco\CLAUDE.md`.
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` inteiro (D4, D5, D6 e "O que NÃO fazer" valem aqui).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\1-mapa-do-reco-atual.md` § 1 (inventário), § 3 (por que pula), § 4.
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\3-lacre-como-molde.md` § 2, § 4 (última linha, movimento), § 5 (Regra da Vida) e § 6.
- O relatório da Fase 0, `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\fase-0-relatorio.md`:
  - `exe_selftest` e `import_reco` (partida do motor congelado: duração do estado "motor subindo");
  - `abrir_pronta_s` (régua de D12: o app atual pronto para gravar); a decisão D2 (prova da bandeja).
  - `pipeline_gpu` não entra no desenho: Gravar nunca espera a GPU (D12).
- Método (não o visual) do Lacre: `C:\Dev\lacre-wt-design\design\DESIGN.md` (estrutura com frontmatter) e `design\testar-vitrine.cjs` (servidor HTTP local + Playwright).
- `C:\Dev\Reco\roadmap\2026-08-12-melhoria-ux-ui-logica.md` (auditoria F1–F17: o que já foi consertado não pode voltar) e `2026-08-12-icones-lucide.md`.
- `~/.claude/skills/impeccable/SKILL.md` (setup, `reference/new-work.md`, `reference/craft-floor.md`) e a skill `frontend-design:frontend-design`.

## Insumo 1: tamanho da janela (proposta desta fase)

**400 × 560 px lógicos (CSS px), fixos.** O WebView2 multiplica pela escala do Windows (125% vira 500 × 700 físicos).

- **Largura 400.** A janela de hoje tem uns 350 px a 100%:
  - colunas da biblioteca 150+76+56+26 = 308 px (`reco.py:4411-4414`), mais a barra de rolagem e 2×16 de margem (`reco.py:3165`);
  - o texto novo sobe de 8 pt (~10,7 px, `SEG_XS`, `reco.py:94`) para 13–14 px, uns +30%;
  - 4 abas com ícone e rótulo de ~90 px cabem em 400.
- **Altura 560** = título 40 + abas 44 + conteúdo 440 + status 36.
  - A tela mais alta é a Biblioteca: busca 36 + cabeçalho 28 + 8 linhas × 32 + ações 2 × 44 ≈ 410, dentro dos 440.
  - Gravar: medidores 72 + ações 2 × 44 + painel de 8 linhas de texto ≈ 380.
  - Opções passa de 440: rola por dentro, com a calha da barra de rolagem sempre reservada.
- **Cabe ancorada à bandeja:** a menor área útil medida nesta máquina é 2048 × 816 lógicos (monitor principal, 125%, medido em 11/11 com `System.Windows.Forms.Screen`).
  - 560 + 8 de folga cabe com sobra aqui. Num 1366 × 768 a 125% (área útil ~566) cabe sem a folga de 8 (sobram ~6 px). Por isso 560 é o teto.
- Tudo isso vira token único (`--janela-largura`, `--janela-altura` e as alturas de cada área): mudar o tamanho é mudar um número.

## Insumo 2: fontes de movimento de hoje → regra → como o teste pega

Checklist tirado do relatório 1 § 3. Cada elemento que hoje aparece e some ganha um espaço reservado com nome (`data-area`).

| fonte de hoje (código) | regra do contrato | o teste pega por |
| --- | --- | --- |
| janela sem tamanho (`reco.py:2933` só posiciona) e 5 `geometry("")` (`reco.py:3323`, 3467, 3562, 3602, 4338) | janela fixa 400 × 560 | caixa de `janela` igual em toda tela e estado |
| status com `wraplength=300` em 1 a 3 linhas (`reco.py:3269`, 3877-3896) | status em 1 linha, reticências, texto inteiro no tooltip | caixa de `status` igual; `title` = texto inteiro |
| linha de botões diferente por estado (`_set_rec_state`, `reco.py:3565-3602`) | área `acoes` com 2 linhas sempre reservadas | caixa de `acoes` igual em todos os estados |
| link "Abrir transcrição" que aparece (`reco.py:4357`) | vaga fixa no painel; some por opacidade | caixa de `painel` igual |
| Parar da transcrição empacotado sob demanda (`reco.py:4351`, 4343, 4610) | vaga fixa no painel ou nas ações | idem |
| painel ao vivo de 8 linhas (`_live_show`, `reco.py:3317-3323`) | `painel` sempre reservado; vazio mostra texto de estado | caixa de `painel` igual |
| painel de Opções que expande (`_toggle_advanced`, `reco.py:3458`) | Opções é aba, rola por dentro | caixa de `conteudo` igual entre abas |
| troca de tela com Treeview de 8 linhas (`_show_view`, `reco.py:4308`) | `conteudo` de altura fixa em toda aba | idem |
| "Opções" ↔ "Ocultar opções", "Transcrever…" ↔ "← Gravar" (`reco.py:3462`, 4333) | abas com rótulo fixo; a ativa muda só a cor | caixa de cada aba igual |
| link "Nova versão" acrescentado (`_show_app_update`, `reco.py:2956`) | vaga fixa na barra de título; some por opacidade | caixa de `titulo` igual com e sem versão nova |
| nome de dispositivo longo nos combos e no status | reticências + tooltip | modo texto longo no teste |
| janela que cresce para baixo da barra de tarefas (`_anchor_to_tray`, `reco.py:4980`) | não cresce, então a âncora vale sempre | coberto pela janela fixa |
| menu de hover num `Toplevel` novo a cada `<Enter>` (`_make_pop`, `reco.py:3607`) | nenhuma ação só no hover; tooltip é texto extra | teste de contrato: cada ação tem rótulo visível |
| botão que se mexe no clique (Regra da Vida do Lacre, relatório 3 § 5) | clique e hover só mudam cor; nada de `translate`/`scale` | caixa do botão igual antes, durante e depois do clique |

## Insumo 3: cada funcionalidade de hoje → tela nova

Inventário do relatório 1 § 1 (19 linhas). Nada some sem justificativa.

| # | funcionalidade (código de hoje) | onde fica |
| --- | --- | --- |
| 1 | janela sem moldura, título arrastável, minimizar e fechar, fade-in (`reco.py:2853-2941`, `_minimize` 2987, `_fade` 3025) | barra de título própria em todas as telas; fade-in fica (é só opacidade) |
| 2 | VU de mic e de sistema; arrastar o medidor ajusta o ganho 0×–10× com "8,0x" (`VuMeter` 2771, `fmt_gain` 2763) | Gravar › `medidores`; o ganho vira controle visível (alça, número, setas do teclado) |
| 3 | estados pronto, gravando, pausado, parado, ocupado; cronômetro e ponto piscando (`_set_rec_state` 3565, `_tick_timer` 4123, `_blink_dot` 4136) | Gravar › `acoes` e `cronometro`; o ponto pisca por opacidade e fica parado com movimento reduzido |
| 4 | depois de parar: o clique salva e copia o caminho entre aspas (`_conclude_save_and_copy` 4086); Excluir (vai para a Lixeira), Reproduzir; menu de hover com 4 saídas (3247-3251) | botão principal "Salvar e copiar caminho" em `acoes`; as outras 5 saídas viram botões visíveis no `painel` |
| 5 | uma linha de status e o link "Abrir transcrição" (3266-3270, 4357) | faixa `status` comum às telas; "Abrir transcrição" com vaga fixa no `painel` |
| 6 | Parar da transcrição disparada pela tela de gravar (`_rec_show_stop_tr` 4351) | Gravar › `painel`, variante "transcrevendo", com barra de progresso |
| 7 | ao vivo: painel de 8 linhas e passada final (`_live_show` 3317, `_run_live_final_pass` 4005) | Gravar › `painel`, variante "ao vivo" |
| 8 | modo nota, sem entrada hoje (`_start_nota` 3813, sem chamador) | Gravar › seletor "Gravação · Nota" em `acoes` (desenho aqui; ligar é Fase 3) |
| 9 | Opções: entrada, saída (Auto console, Auto comunicação, manual), atualizar dispositivos, pasta, processar em, idioma, tema, ao vivo, atalho (`_build_advanced` 3350-3456) | aba Opções, tudo visível, rolando por dentro; tema livre sai (ver F1-D6) |
| 10 | telas por links de texto, bloqueadas durante gravação (`_build_links` 3325, `_show_view` 4308-4318) | `abas` (Gravar, Biblioteca, Arquivo, Opções); a que conflita com a gravação fica desabilitada com o motivo na aba (F1-D7) |
| 11 | Transcrever: escolher arquivo, Transcrever, Parar, status, Abrir pasta (`_build_transcribe_section` 4264) | aba Arquivo, ação "Transcrever", com progresso em % (o texto "Transcrevendo… {p}%" já existe, `reco.py:2211`) |
| 12 | Biblioteca: busca por nome e conteúdo, lista, Reproduzir, Transcrever, Abrir txt, Resumo IA, Excluir, Abrir pasta, Atualizar, duplo clique toca (4385-4451) | aba Biblioteca; as ações saem do hover (`_lib_action` 4453) e ganham rótulo visível |
| 13 | Resumo IA por `claude -p` (`_lib_resumo` 4663) | Biblioteca › ação "Resumo IA" + estado "resumindo" |
| 14 | Converter para MP3 16 kHz mono 64k (`_build_convert_section` 4726) | aba Arquivo, ação "Converter para MP3" sobre a mesma origem (F1-D4) |
| 15 | bandeja: hover mostra sem foco, clique fixa, menu nativo, balão, ícone vermelho gravando (`tray.py:197-236`, `_init_tray` 4914, `_hover_watch` 5024) | fora da janela (casco, Fase 3); o DESIGN.md define só os dois ícones (ocioso e gravando, com forma diferente além da cor) |
| 16 | atualizações: modelo sozinho, versão nova como link (`_show_app_update` 2956) | modelo: mensagem no `status`; versão nova: vaga fixa com ícone na barra de título |
| 17 | i18n PT/EN, frase PT é a chave (`reco.py:269-512`) | Opções › Idioma; o teste roda com texto longo em PT e em EN |
| 18 | atalho Ctrl+Shift+R por `.lnk` (`_create_shortcut` 4892) | Opções › Atalho de teclado (criar ou remover) |
| 19 | instância única e as CLIs `--selftest`/`--transcribe` (5120-5213) | sem tela, de propósito: são contrato (D6, D7), não interface |

**Cortado, com motivo:** o tema livre (cor de fundo e de destaque no seletor de cor, `_pick_bg` 3523).

- É o que desencontra combos e lista do resto (relatório 1 § 4), e o Gabriel usa o padrão (`bg_color #181A1B`, `accent_color #E0825F`, lido no config em 11/11).
- Entra no lugar "Aparência: Sistema · Claro · Escuro". As chaves `bg_color` e `accent_color` continuam no config, ignoradas pela interface nova (D6: o app velho segue lendo).

## Fase 1 — Identidade visual e contrato de tela

**Critério de aceite:**

- **A.** O Gabriel abre a vitrine por um link e vê 2 ou 3 identidades visuais claramente diferentes. Em cada uma, troca por abas entre Gravar, Biblioteca, Arquivo e Opções e passa por todos os estados.
  - Estados: pronto, gravando com medidores e cronômetro, pausado, parado com as saídas à vista, transcrevendo com progresso, ao vivo, erro e motor subindo.
  - **Se falhar:** só aparece uma identidade, falta um estado, ou alguma tela ou ação só se alcança por link de texto ou por hover.
- **B.** Ao percorrer todos os estados e telas, mesmo com nomes e mensagens enormes, a janela e cada área ficam paradas; os botões não andam quando ele clica.
  - **Se falhar:** a borda de baixo sobe e desce, uma linha de botões se desloca, ou o botão afunda no clique.
- **C.** Depois da escolha dele, só a identidade escolhida continua na vitrine, com o nome que ele aprovou.
  - **Se falhar:** a vitrine segue mostrando as três, ou mistura cores de duas.

1. [x] Conferir frescor, travas e Fase 0. — **prova:** `cd C:/Dev/Reco; git log --oneline 7c5c1a1..HEAD -- reco.py tray.py; ls design; wc -c < CLAUDE.md; ls roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-0-relatorio.md` → nenhum commit; "No such file"; ≤ 5900; o relatório existe
   **reprova se:** `design/` já existe com conteúdo de outra sessão (parar e ler), o `CLAUDE.md` passa de 5900 bytes (sem espaço para o passo 16 sob o teto de 6144) ou falta o relatório da Fase 0 (a fase depende dela; parar).
   - Se `reco.py`/`tray.py` mudaram, reler as linhas citadas neste md antes de seguir.
   - Ler o relatório da Fase 0 (`fase-0-relatorio.md`): partida do motor congelado (`exe_selftest`), `abrir_pronta_s`, e se a bandeja mostra a janela sem roubar o foco (D2).
   - Se a Fase 0 reabriu a D2 (bandeja reprovada no Tauri), o desenho desta fase vale igual: o contrato é de tela, não de framework.
2. [x] Carregar a skill `impeccable`, rodar o setup com o contexto em `design/` e escrever `design/PRODUCT.md` curto. — **prova:** `cd C:/Dev/Reco; grep -c "^## " design/PRODUCT.md` → ≥ 4
   **reprova se:** a contagem dá menos de 4, ou o setup conferido abaixo ainda imprime `NO_PRODUCT_MD`, falha ou não imprime nada.
   - Setup conferido à parte: `cd C:/Dev/Reco && mkdir -p temp && IMPECCABLE_CONTEXT_DIR=design node "$HOME/.claude/skills/impeccable/scripts/context.mjs" > temp/ctx.txt && grep -c NO_PRODUCT_MD temp/ctx.txt` → 0
     - Sem `design/PRODUCT.md` o mesmo comando dá 1 (conferido em 11/11); erro do node não imprime número, e isso também reprova.
   - Setup: `IMPECCABLE_CONTEXT_DIR=design node "$HOME/.claude/skills/impeccable/scripts/context.mjs"`, com cwd `C:\Dev\Reco`.
   - O script procura PRODUCT.md e DESIGN.md na raiz, em `.agents/context/` e em `docs/`; a variável só vale quando esses estão vazios, como no Reco (cabeçalho de `scripts/context.mjs`).
   - Conteúdo do PRODUCT.md: quem usa (o Gabriel, sozinho, em reunião e em ditado), a cena (janela pequena ancorada à bandeja, usada de relance durante uma chamada), o modo `Operate` da skill, o que é sucesso (gravar sem pensar, achar a transcrição, nada se mexe).
   - Sessão sem humano: a entrevista do `reference/init.md` se responde com o índice, o hub e este md, marcando no arquivo "respostas tiradas do roadmap, sem entrevista".
3. [x] Escrever `design/DESIGN.md`: estrutura do Lacre (frontmatter + seções), conteúdo do Reco (detalhe abaixo). — **prova:** `cd C:/Dev/Reco/design; grep -cE "^### R[0-9]+" DESIGN.md; grep -cE "^- \*\*teste:\*\*" DESIGN.md` → os dois números iguais e ≥ 15
   **reprova se:** há regra sem a linha "teste:" (números diferentes) ou menos de 15 regras.
   - Seções: Visão geral com North Star, Princípios, Contrato de tela (R1–R15), Áreas e estados, Condutor de estados, Telas (a tabela do Insumo 3 inteira, com o corte) e Direções.
   - North Star sugerido (o executor refina com a skill): "um gravador de mesa que some quando trabalha: grava sem cerimônia, mostra o que importa e nunca se mexe sozinho".
   - Regras, cada uma com uma linha `- **teste:**` dizendo qual verificação dos passos 7 e 9 a cobre:
     - R1 janela fixa 400 × 560 (Insumo 1); R2 cada área com altura reservada (lista de `data-area` abaixo);
     - R3 status em 1 linha com reticências, texto inteiro em `title` e no detalhe; R4 `tabular-nums` no cronômetro, ganho, duração, % e contagens;
     - R5 transição só de opacidade e cor; R6 clique e hover não movem o botão (sem `transform` em `:hover`/`:active`);
     - R7 elemento condicional some por opacidade ou `visibility`, nunca por `display:none` que libera espaço; R8 área que rola usa `scrollbar-gutter: stable`;
     - R9 foco visível (`:focus-visible`, contorno ≥ 2 px) e tudo alcançável por Tab; R10 DPI pelo WebView2: só px lógicos e ícones SVG, nada de bitmap;
     - R11 claro e escuro pelo sistema, com a escolha manual em Opções; R12 cor nunca é o único sinal (ícone ou texto junto, inclusive no ícone da bandeja);
     - R13 ícones Lucide inline (licença ISC citada), nenhum emoji ou glifo como ícone (hoje há "📄", "⚡", "✓"); R14 movimento reduzido zera transições e piscar.
     - R15 toda ação e toda tela à vista: navegação por abas (botões), nenhum link de texto como navegação, nada que só apareça no hover; fora da barra de título, todo botão tem texto visível.
   - Condutor de estados (contrato com a Fase 3): a página aceita `?direcao=&tela=&estado=&tema=&texto=&versao=` e expõe `window.vitrine.definir({...})` com os mesmos nomes.
     - A interface real da Fase 3, no modo de backend falso, expõe o mesmo condutor, para os dois testes rodarem contra ela com `--url`.
   - Nomes de área fixos, que a Fase 3 reusa: globais `janela`, `titulo`, `abas`, `conteudo`, `status`; Gravar `medidores`, `acoes`, `cronometro`, `painel`.
   - Biblioteca `busca`, `lista`, `acoes-lib`; Arquivo `origem`, `acoes-arq`, `progresso`; Opções `opcoes-lista`.
   - Estados por tela (o teste percorre todos):
     - Gravar: `motor-subindo`, `pronto`, `gravando`, `gravando-ao-vivo`, `nota-gravando`, `pausado`, `parado`, `transcrevendo`, `transcricao-pronta`, `erro`, `erro-detalhe`;
     - Biblioteca: `vazia`, `lista`, `selecionada`, `transcrevendo-item`, `resumindo`, `busca-sem-resultado`, `erro`;
     - Arquivo: `nada-escolhido`, `escolhido`, `transcrevendo`, `convertendo`, `pronto`, `erro`; Opções: `normal`, `durante-gravacao`, `dispositivo-ausente`.
   - Variações globais: tema claro e escuro, texto normal e longo (PT e EN), versão nova sim e não.
   - "Motor subindo": "Gravar" desabilitado com o motivo no status ("Preparando o motor…"); nada gira, o indicador pulsa por opacidade.
     - A duração esperada é a partida do motor congelado (`exe_selftest` do relatório da Fase 0); a GPU nunca segura o Gravar (D12).
   - "Erro": ícone + texto no status cortado por reticências; o botão "Detalhes" abre um painel sobreposto ao `conteudo`, do mesmo tamanho, com o texto inteiro e "Copiar".
   - O erro de hoje é cortado em `[:80]`/`[:110]` (relatório 1 § 4); no detalhe ele aparece inteiro.
4. [x] Conferir o inventário no DESIGN.md (Insumo 3). — **prova:** `cd C:/Dev/Reco; for k in ganho Nota Lixeira "Resumo IA" "Processar em" Atalho Aparência "versão nova" bandeja "instância única" "entre aspas" "ao vivo"; do grep -qi "$k" design/DESIGN.md || echo "FALTA $k"; done` → nenhuma linha
   **reprova se:** aparece qualquer "FALTA …", ou a contagem de linhas numeradas da tabela (abaixo) dá menos de 19.
   - Tabela conferida à parte: `grep -cE '^\| ?(1[0-9]|[1-9]) ?\|' C:/Dev/Reco/design/DESIGN.md` → ≥ 19.
   - A lista cobre as linhas fáceis de esquecer; as 19 linhas da tabela do Insumo 3 também precisam estar lá, uma por funcionalidade, com o número na 1ª coluna.
5. [x] Criar `design/tokens.css` com 2 ou 3 direções, cada uma em claro e escuro (skills e briefs abaixo). — **prova:** `cd C:/Dev/Reco/design; grep -oE 'data-direcao="[a-c]"' tokens.css | sort -u | wc -l; grep -Eic 'seal|#0f5f73|#5db6c8|selo' tokens.css` → 2 ou 3; depois 0
   **reprova se:** só uma direção, ou aparece nome ou cor do Lacre nos tokens (o DESIGN.md pode citar a proibição; por isso fica fora do grep).
   - Skills: `impeccable` (`reference/new-work.md`, modo Operate) e `frontend-design:frontend-design`, para dar a cada direção um ponto de vista próprio.
   - Estrutura: tokens comuns em `:root` (tamanho da janela, alturas das áreas, espaçamentos, raios, durações, fontes);
     - cor por direção em `[data-direcao="a"]`, seletor sem `:root`, para valer no elemento da janela simulada (vitrine) e no `<html>` (app real);
     - escuro por `@media (prefers-color-scheme: dark)` em `[data-direcao="a"]:not([data-tema="claro"])`, e escolha manual por `[data-tema="escuro"]`;
     - nenhum hexadecimal fora deste arquivo (o passo 9 confere no modelo da vitrine).
   - Só fontes do Windows, nada baixado (conferidas em `C:\Windows\Fonts` em 11/11): Segoe UI Variable (`SegUIVar.ttf`), Bahnschrift, Sitka (`SitkaVF.ttf`), Cascadia Mono.
   - Ponto de partida das direções; a skill refina, mas elas precisam diferir em paleta, tipo, densidade e forma:
     - **A "Fita"**: continuidade com o Reco de hoje. Grafite quente e o coral `#E0825F` (`reco.py:44-45`) amadurecidos, cronômetro grande em Segoe UI Variable Display, camadas de tom, raios médios.
     - **B "Caderno"**: claro primeiro, papel e tinta, o texto da transcrição como protagonista. Sitka nos títulos e no painel de texto, destaque azul-tinta ou vermelho de lápis.
     - **C "Instrumento"**: console de medição. Quase monocromática, Bahnschrift nos números e rótulos curtos, medidores com escala visível, um sinal âmbar ou verde, cantos retos.
   - Proibido: teal como cor de ação (matiz entre 170° e 200°) e qualquer valor copiado de `C:\Dev\lacre*` (D5, "O que NÃO fazer").
6. [x] Montar a vitrine standalone `design/vitrine.html` a partir do modelo (detalhe abaixo). — **prova:** `cd C:/Dev/Reco; node design/montar-vitrine.cjs && grep -Ec '(src|href)="(https?:)?//' design/vitrine.html; wc -c < design/vitrine.html` → 0; e um número abaixo de 450000
   **reprova se:** há recurso externo (contagem > 0) ou o arquivo passa de 450 KB (o `check-added-large-files` do pre-commit barra perto de 500 KB).
   - Arquivos: `design/vitrine.modelo.html` + `design/montar-vitrine.cjs` (~80 linhas) geram `design/vitrine.html` (F1-D8).
   - O `montar-vitrine.cjs` embute `tokens.css` dentro de `<style>`; os ícones Lucide vão inline como `<symbol>` SVG, com a licença num comentário.
   - Usar as skills `impeccable` (carregar `reference/craft-floor.md` imediatamente antes de escrever o HTML) e `frontend-design:frontend-design`.
   - Uma janela viva por direção (400 × 560), com estado trocado no mesmo DOM. Quadros estáticos lado a lado não provam a transição.
   - Controles da vitrine em segmentos, fora da janela: Direção, Tela, Estado, Tema, Texto (normal, longo PT, longo EN), Versão nova.
   - A navegação dentro da janela é por abas com ícone e rótulo, nunca por link de texto.
   - Atualização pontual: uma função por componente muda `textContent`/atributos. Nunca refazer a árvore (o `render()` do Lacre está em "O que NÃO fazer").
   - Condutor para o teste (passo 3): `window.vitrine = { direcoes, telas, estados, definir({direcao, tela, estado, tema, texto, versao}) }` e os mesmos nomes na URL.
   - A casca da página (controles, fundo, fora da janela) segue o contrato da ferramenta `Artifact`: cores em `:root` e tema por `data-theme`.
     - Antes de escrever a casca, chamar `Artifact` com `action: quickstart` e `intent: other` (traz o contrato da página e substitui carregar `artifact-design`); o `<title>` é "Vitrine do Reco".
     - A janela simulada usa `data-direcao`/`data-tema` no próprio elemento, então as duas coisas não se cruzam.
   - Texto longo de verdade: o status de `reco.py:3877-3896` com nomes reais de dispositivo e o aviso de ausente, nome de arquivo de 80 caracteres e o cronômetro em `12:34:56`.
   - Medidores animados por timer só para olhar, sem transição CSS no preenchimento.
   - A página precisa caber em celular para ser vista pelo link: abaixo de 440 px de largura, a janela é mostrada com `zoom` reduzido e sem rolagem lateral.
   - Os testes rodam em largura de desktop, onde o zoom não se aplica.
7. [x] Criar `design/testar-anti-pulo.cjs` (até 500 linhas, entra na trava do pre-commit; matriz abaixo). — **prova:** `cd C:/Dev/Reco; node design/testar-anti-pulo.cjs; echo "saída=$?"` → última linha `anti-pulo: 0 diferenças em N medições` (N na casa das dezenas de milhares) e `saída=0`
   **reprova se:** aparece qualquer linha `FALHA <combinação> área=<nome> base=<x,y,l,a> agora=<x,y,l,a>` ou a saída é diferente de 0.
   - Serve `design/` por HTTP local numa porta livre, como o `testar-vitrine.cjs` do Lacre (o Chromium do MCP bloqueia `file://`).
   - Playwright: tentar `PLAYWRIGHT_CORE`, depois `require('playwright-core')`, depois `require('playwright')`, por último `path.join(<saída de npm root -g>, 'playwright')` por `child_process`.
     - É a ordem que a Fase 3 cita; só o último acha o global, porque o Node não procura em `npm root -g` sozinho.
   - Nunca caminho absoluto com o nome do usuário: o repo é público. O Playwright global 1.64 com Chromium abriu nesta máquina em 11/11.
   - Percorre: direção × escala 1, 1,25 e 1,5 (`deviceScaleFactor`) × tema claro e escuro × texto normal, longo PT e longo EN × versão nova sim e não × cada tela × cada estado.
   - Mede `getBoundingClientRect()` de `[data-area=janela]` e de cada `[data-area]` visível, e compara exato (diferença 0).
   - **Linha de base por direção e escala, não por combinação:** tema, texto, versão nova e estado mudam conteúdo, nunca caixa.
     - Assim uma barra de título que cresce com o aviso de versão nova, ou um combo que alarga com nome longo, reprova.
   - Áreas de tela comparam contra a base da mesma tela; as globais (`janela`, `titulo`, `abas`, `conteudo`, `status`) contra a base de todas as telas.
   - Escalas diferentes não se comparam entre si (o arredondamento de subpixel muda).
   - `--url <endereço>` troca a vitrine por outro alvo com o mesmo condutor de estados (a Fase 3 aponta para a interface real).
   - Controle negativo `--sabotar`: injeta em tempo de execução (sem gravar arquivo) uma regra que tira a linha única e a altura reservada do status, mais o status longo real em 3 linhas.
     - A regra é `[data-area=status]{white-space:normal!important;height:auto!important;overflow:visible!important}`.
8. [x] Provar que o teste pega o pulo: rodar o controle negativo. — **prova:** `cd C:/Dev/Reco; node design/testar-anti-pulo.cjs --sabotar; echo "saída=$?"` → linhas `FALHA … área=status …` e `saída=1`
   **reprova se:** a saída é 0 com a sabotagem (o teste não mede o que diz medir; voltar ao passo 7).
9. [x] Criar `design/testar-contrato.cjs` (até 500 linhas) com R3–R15 fora das caixas de área. — **prova:** `cd C:/Dev/Reco; node design/testar-contrato.cjs; echo "s=$?"; node design/testar-contrato.cjs --sabotar; echo "s=$?"` → `contrato: 0 falhas` e `s=0`; depois `FALHA clique-move …` e `s=1`
   **reprova se:** a primeira rodada falha, ou a segunda (com `button:active{transform:scale(.98)}` injetado) sai 0.
   - Mesma resolução do Playwright, mesmo servidor local e mesmo `--url` do passo 7.
   - Verificações, uma linha `ok`/`FALHA` por item:
     - R4: todo `[data-num]` com `font-variant-numeric` contendo `tabular-nums`;
     - R5: em todo elemento, `transition-property` só com opacity, color, background-color, border-color, outline-color, fill, stroke (ou duração 0); `@keyframes` só com opacity;
     - R6: para cada botão visível, a caixa é igual antes, com o mouse em cima, com o botão apertado (`mouse.down`) e depois de soltar;
     - R3: o status tem `nowrap`, `ellipsis`, `overflow:hidden`; com texto longo, `scrollWidth > clientWidth` e `title` igual ao texto inteiro;
     - R7: nenhum elemento condicional muda `display` entre estados; R8: toda área com `overflow:auto|scroll` tem `scrollbar-gutter: stable`;
     - R9: percorrer com Tab; cada foco tem contorno ≥ 2 px e todo botão é alcançado;
     - R10: nenhum `<img>` nem `background-image` com bitmap (png, jpg, gif, bmp) dentro da janela; ícones só `<svg>`;
     - R11: sem `tema`, a janela segue `colorScheme` do Playwright (claro e escuro dão fundos diferentes); com `tema=claro|escuro`, a escolha vence o sistema;
     - R12: todo `[data-sinal]` tem um SVG e texto não vazio; R13: nenhum emoji no texto visível (`\p{Extended_Pictographic}`) e todo SVG de ícone tem `data-lucide`;
     - R14: com `reducedMotion: 'reduce'`, todas as durações são 0 e nada pisca;
     - R15: nenhum `<a>` dentro da janela; abas com `role="tab"`; fora de `titulo`, todo botão com texto visível não vazio; nenhuma regra `:hover` que mude `display`, `visibility` ou `opacity` de outro elemento;
     - contraste: texto comum ≥ 4,5:1 e texto grande ≥ 3:1 contra o fundo opaco mais próximo, nos dois temas de cada direção;
     - tokens: nenhum hexadecimal de cor em `vitrine.modelo.html` (regex `#[0-9a-fA-F]{3,8}\b` fora de `tokens.css`).
10. [x] Revisão visual numa rodada só (`impeccable critique` ou `audit`, capturas pelo Playwright MCP) e correções em lote. — **prova:** `ls C:/Dev/Reco/temp/vitrine-capturas/*.png | wc -l` → ≥ direções × 2
   **reprova se:** faltam capturas (a revisão não aconteceu), qualquer `FALHA` nos testes conferidos abaixo, ou a crítica aponta direções parecidas demais (aí refazer a que ficou genérica antes de mostrar).
   - Testes conferidos à parte, depois das correções: `cd C:/Dev/Reco; node design/montar-vitrine.cjs && node design/testar-anti-pulo.cjs && node design/testar-contrato.cjs; echo "s=$?"` → as duas linhas de 0 e `s=0`.
   - Servir a vitrine em segundo plano: `python -m http.server 8765 --directory C:/Dev/Reco/design` e abrir `http://127.0.0.1:8765/vitrine.html`; parar o servidor ao fim do passo.
   - Capturas de cada direção em claro e escuro em `temp/vitrine-capturas/` (fora do git); no MCP, `browser_set_group_label` antes de `browser_navigate`.
   - O resumo da crítica (o que mudou e o que ficou) vai para o relatório da fase, criado no passo 12.
   - Uma rodada de correção e no máximo uma de confirmação (regra da própria skill `impeccable`).
11. [x] Commitar por pathspec, nunca `git add -A` nem `--no-verify` (comando abaixo). — **prova:** `git -C C:/Dev/Reco status --short design/; git -C C:/Dev/Reco log -1 --stat` → nenhuma linha no status; o último commit lista os 8 arquivos de `design/`
   **reprova se:** a trava de tamanho acusa um `.cjs` acima de 500 linhas, o `check-added-large-files` barra a vitrine, ou sobra arquivo de `design/` fora do commit.
   - `git add design/PRODUCT.md design/DESIGN.md design/tokens.css design/vitrine.modelo.html design/vitrine.html design/montar-vitrine.cjs design/testar-anti-pulo.cjs design/testar-contrato.cjs`.
   - Depois: `git commit -m "<mensagem>" -- <os mesmos 8 caminhos>` (pathspec: não leva o que outra sessão deixou no stage) e `git push`, antes da espera pela escolha do passo 12.
   - Mensagem: "design: identidade do Reco em <N> direções, vitrine e testes anti-pulo".
12. [x] Publicar a vitrine para o Gabriel com a ferramenta `Artifact` e parar. — **prova:** `grep -cE "claude\.ai/(code/)?artifact/" C:/Dev/Reco/roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-1-relatorio.md` → ≥ 1
   **reprova se:** a contagem dá 0, o link (aberto com `Artifact` `action: open`) mostra só uma direção, ou a sessão segue para o passo 13 sem a resposta dele.
   - Publicar `C:\Dev\Reco\design\vitrine.html` (ícone `palette`); o contrato da página já veio do quickstart do passo 6.
   - Sessão nova (a do passo 6 acabou): repetir o quickstart antes de publicar. Se o contrato dele conflitar com a vitrine, adaptar só a casca da página (fora da janela). Se a publicação for recusada, abrir local e registrar o motivo no relatório.
   - Também vale abrir o arquivo local no navegador comum dele (só o Chromium do MCP bloqueia `file://`).
   - Sinal, nunca pergunta (sessão aberta por IA não usa `AskUserQuestion`):
     - `[[DECISAO]] Direção visual do Reco: A "Fita", B "Caderno" ou C "Instrumento"? Vitrine: <link>. Dá para pedir mistura (ex.: cores da A com os medidores da C) | dono: gabriel`.
   - O relatório da fase nasce aqui: criar `roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-1-relatorio.md` com o link, a data e o resumo da crítica do passo 10. O link é privado e só o Gabriel libera.
13. [x] (Depois da resposta) Registrar a escolha em `design/DESIGN.md` e marcar o pendente do índice como decidido. — **prova:** `cd C:/Dev/Reco; grep -n "Direção escolhida" design/DESIGN.md; grep -n "decidido em" roadmap/2026-11-11-melhoria-reco-em-rust.md` → uma linha em cada
   **reprova se:** falta uma das duas linhas, ou a escolha registrada não é a que ele disse.
   - No DESIGN.md, § Direções: "Direção escolhida: <letra e nome> (<data>)", com as palavras dele.
   - No índice, seção "Pendente (decisão do Gabriel)": "decidido em <data>: <direção>".
   - Se ele pediu mistura ou ajuste, refazer os passos 5, 6 e 10 com o pedido e publicar de novo na mesma URL (o `url` anotado no relatório) antes de seguir.
> Atualizado em 2026-11-11: o Gabriel escolheu A como padrão e B e C como skins ("opção A, mas gostei das outras
> duas. acho que dá pra ter opção de skin"). O passo 14 deixou de ser poda e virou o 14b abaixo.

14. ~~Podar: só a direção escolhida fica nos tokens, na vitrine e no teste.~~ Superado pela decisão do Gabriel (skins).
14b. [x] Skins: A padrão, B e C selecionáveis em Opções › Visual, e o acabamento que faltava em B e C. — **prova:** `cd C:/Dev/Reco; node design/montar-vitrine.cjs && node design/testar-anti-pulo.cjs; echo "a=$?"; node design/testar-contrato.cjs; echo "c=$?"; grep -c 'data-acao="skin"' design/vitrine.html` → as duas linhas de 0, `a=0`, `c=0` e ≥ 3
   **reprova se:** o seletor de skin falta (0), algum teste acusa falha, ou uma das sabotagens conferidas abaixo sai 0.
   - Conferido à parte: `for t in anti-pulo contrato; do node design/testar-$t.cjs --sabotar >/dev/null; echo "$t=$?"; done` → `anti-pulo=1`, `contrato=1`.
   - Vitrine: a direção inicial é A ("Fita") e a aba Opções ganha "Visual" com Fita · Caderno · Instrumento; clicar troca a skin daquela janela pelo condutor (`definir({direcao})`).
   - A matriz dos testes continua com as três direções (cada skin contra a própria linha de base).
   - Acabamento das pendências do passo 10 (relatório da Fase 1): a calha da margem da B não pode deslocar botões; a primeira linha do texto ao vivo não pode sair cortada na B e na C; o medidor da A deixa de repetir o fio da B.
   - Sem Artifact (decisão do Gabriel, 11/11: só HTML): entregar `design/vitrine.html` aberto no navegador dele e atualizar o relatório.
15. [x] Registrar a armadilha que gerou a fase, pelo gerador (nunca `Edit` na página gerada). — **prova:** `cd C:/Dev/Reco; python tools/visoes.py validar && ls docs/armadilhas.d | grep -c janela-sem; grep -c "(o que se vê\|(por que acontece" docs/armadilhas.d/*janela-sem*.md` → 1; depois 0
   **reprova se:** a contagem de arquivos não é 1 (nenhum, ou `novo` rodou duas vezes), o `validar` acusa fragmento malformado, ou o esqueleto continua sem preencher (segundo número ≥ 1).
   - Criar uma vez só (não é a prova): `python tools/visoes.py novo "Janela sem tamanho fixo pula a cada clique (Tk e WebView)"`.
   - Uso do `novo` em `tools/visoes.py:13`; ele grava `docs/armadilhas.d/<data>-<HHMM>-<slug>.md` com o esqueleto `**Sintoma:** (o que se vê…)` e `**Causa:** (por que acontece)` (`cerebro/scripts/visoes_projeto.py:276-288`).
   - Preencher o corpo por `Edit` no fragmento recém-criado (ainda não commitado); a página `docs/ARMADILHAS.md` nunca se edita.
   - `docs/armadilhas.d/` é versionado (33 arquivos em `git ls-files` em 11/11); `docs/ARMADILHAS.md` é gerado e está no `.gitignore`.
   - Corpo do fragmento:
     - sintoma: a janela muda de altura e largura a cada clique;
     - causa: toplevel sem tamanho acompanha o conteúdo, mais as 5 chamadas a `geometry("")` (`reco.py:3323, 3467, 3562, 3602, 4338`) e o status com quebra;
     - o que fazer: `design/DESIGN.md` R1–R8 e o teste anti-pulo.
   - 12/11: `validar` com exit 0, `1` arquivo (`2026-11-12-0037-janela-sem-tamanho-fixo-pula-a-cada-clique-tk-e-webview.md`) e `0` esqueleto.
16. [x] Documentar e fechar em 1–3 linhas cada, com caminho (textos abaixo). — **prova:** `cd C:/Dev/Reco; grep -c "design/DESIGN.md" CLAUDE.md README.md docs/_INDICE.md docs/ARQUITETURA.md; wc -c < CLAUDE.md` → ≥ 1 em cada um dos quatro; um número ≤ 6144
   **reprova se:** algum arquivo sem a referência, ou o `CLAUDE.md` passa de 6144 bytes (o `gate-claude-md` barra o commit).
   - Hub conferido à parte: `grep -c "Direção visual\|design/DESIGN.md" C:/Dev/cerebro/projetos/reco.md` → ≥ 1 (o link do roadmap a Fase 0 já pôs; isto só a Fase 1 escreve).
   - Fase 3 conferida à parte: `cd C:/Dev/Reco/roadmap; grep -c "Transcrever, Converter, Gravações" *-fase-3.md; grep -c "testar-contrato.cjs --url" *-fase-3.md` → 0; depois ≥ 1.
   - Os textos:
     - `CLAUDE.md`: "Interface nova segue `design/DESIGN.md`; testes `node design/testar-anti-pulo.cjs` e `testar-contrato.cjs` antes de mexer em tela";
     - `docs/_INDICE.md`: uma linha para `design/` (DESIGN, PRODUCT, tokens, vitrine, testes) e quando ler;
     - `docs/ARQUITETURA.md`: seção curta "Contrato de tela da interface nova" com link, sem copiar as regras.
     - `README.md`: uma linha em "How it works" e em "Como funciona" dizendo que a interface nova está em desenho em `design/DESIGN.md` (a tela de verdade e o print novo vêm na Fase 3).
   - Hub, por `Edit` ancorado: linha no "Estado agora" ("Direção visual escolhida: <nome>", link de `design/DESIGN.md` e do índice) e o roadmap em "Roadmaps em voo".
   - Conferir que o md da Fase 3 está alinhado a esta fase (foi alinhado na revisão do roadmap em 11/11), lendo o passo 13, a tabela de paridade e os passos 12 a 14:
     - abas Gravar, Biblioteca, Arquivo e Opções; os dois testes da Fase 1 com `--url` e diferença 0 (F1-D12); o condutor `?tela=&estado=` com `definir()`; as regras R1–R15.
     - Se algo voltou a divergir (edição posterior), alinhar por `Edit` ancorado no md da Fase 3, registrar no relatório e incluí-lo no commit abaixo.
   - Completar `fase-1-relatorio.md` no sidecar (direção escolhida, provas); fragmento do diário pela skill `consolidar`.
   - Antes do commit, o repo é público: `grep -rlE 'C:[\\/]Users|Gabriel dos Anjo[s]|App[D]ata' C:/Dev/Reco/design C:/Dev/Reco/roadmap/2026-11-11-melhoria-reco-em-rust*` → nada (a régua da Fase 0).
   - Commit no Reco: `git add` e depois `git commit -m "<mensagem>" -- <caminhos>`, com `CLAUDE.md README.md docs/_INDICE.md docs/ARQUITETURA.md design/` e o fragmento novo de `docs/armadilhas.d/`;
     - mais `roadmap/2026-11-11-melhoria-reco-em-rust.md`, este md, `roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-1-relatorio.md` e, só se foi preciso realinhar, o md da Fase 3. Depois `git push`.
   - Commit no C:\Dev: `git -C C:/Dev add cerebro/projetos/reco.md <fragmento do diário> <páginas geradas>` e `git -C C:/Dev commit -m "<mensagem>" -- <os mesmos caminhos>`.
   - 12/11: `CLAUDE.md:1 README.md:2 docs/_INDICE.md:1 docs/ARQUITETURA.md:1`, `CLAUDE.md` com 5746 bytes; hub com "Direção visual" escolhida. Fase 3 (só registro; o md é de outra frente): `0` e `2`, alinhada; tem `casco_skin` e `data-direcao`.

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F1-D1 | Janela fixa de 400 × 560 px lógicos (Insumo 1) | cabe a Biblioteca de 8 linhas e o painel ao vivo; cabe ancorada na menor área útil medida (816) | média | a Fase 3 mostrar tela que não cabe, ou o Gabriel achar pequena (muda um token) |
| F1-D2 | Barra de título própria, sem a moldura do Windows, como hoje (`reco.py:2859`) | mantém a cara atual e o tamanho exato da janela | média | a Fase 3 achar problema de arrastar ou minimizar com `decorations: false` |
| F1-D3 | Uma faixa de status no mesmo lugar em toda tela, com o texto da tela ativa; erro inteiro no detalhe | hoje são 4 status, cada um num lugar, todos com quebra | alta | o Gabriel sentir falta de status por seção |
| F1-D4 | Arquivo: uma origem escolhida, duas ações (Transcrever, Converter para MP3) | hoje são duas escolhas separadas (`_tr_sel`, `_cv_sel`) para o mesmo gesto | média | o uso mostrar que ele converte e transcreve arquivos diferentes em sequência |
| F1-D5 | Saídas de "parado" todas visíveis no painel; o clique principal continua salvar e copiar o caminho entre aspas | ação escondida no hover era um dos achados; o atalho de hoje (commit `7c5c1a1`) não muda | alta | — |
| F1-D6 | Tema livre sai; entra Aparência Sistema · Claro · Escuro; chaves antigas ficam no config, ignoradas | o tema livre desencontra os widgets; o Gabriel usa o padrão | alta | ele pedir cor própria (aí vira escolha entre variantes da direção, não seletor de cor) |
| F1-D7 | Gravando ou transcrevendo, a aba que conflita fica desabilitada com o motivo nela (ícone + texto) | mantém o bloqueio de hoje (`reco.py:4310-4318`) sem esconder o motivo; é o que a Fase 3 (passo 13) prevê | média | o Gabriel quiser navegar gravando e a Fase 2 provar que o motor aguenta |
| F1-D8 | Vitrine gerada (`vitrine.modelo.html` + `tokens.css` → `vitrine.html`), versionada | tokens numa fonte só e vitrine standalone ao mesmo tempo | alta | o gerador virar peso (aí `tokens.css` copiado à mão, com teste de igualdade) |
| F1-D9 | Testes em Node com o Playwright na ordem do passo 7 (o global de `npm root -g` por último); sem `package.json` no Reco nesta fase | não cria dependência nova no repo antes de existir `app/` | média | a Fase 3 criar `app/package.json` (aí a dependência vai para lá) |
| F1-D10 | Só fontes do Windows, nada embutido nem baixado | app offline e vitrine leve; as 4 famílias existem nesta máquina | alta | a direção escolhida precisar de fonte própria (aí embutir com licença) |
| F1-D11 | Ganho vira controle visível (alça, número, setas), sem gesto escondido no VU | o único indício hoje é o cursor (`reco.py:2780`) | alta | — |
| F1-D12 | Nomes de `data-area`, de estado e o condutor de estados (URL + `definir`) fixados no DESIGN.md; os testes aceitam `--url` | a Fase 3 roda os mesmos dois testes contra a interface real no modo de backend falso | alta | — |

## Pendente (dono: gabriel)

- ~~**Escolher a direção visual** na vitrine (passo 12)~~ decidido em 11/11: A "Fita" padrão, B "Caderno" e C "Instrumento" como skins (passo 13).
- **Junto, se quiser:** o contrato tira todo movimento do clique (D4). Se depois de ver a vitrine ele quiser que o botão reaja com movimento, basta dizer; D4 reverte por pedido dele.

## Premissas não verificadas

- ~~**O relatório da Fase 0 ainda não existe**~~ existe e fechou em 12/11 (`exe_selftest` ~1 s livre, 5,4 s carregada; `abrir_pronta_s` 1,515 s; D2 confirmada). Texto original: (o md da Fase 0 promete `fase-0-relatorio.md` no sidecar, passo 15 dele). Desta fase ele alimenta duas coisas:
  - `exe_selftest` (partida do motor congelado), que define a duração esperada do estado "motor subindo", e `abrir_pronta_s`, a régua de D12;
  - a prova da bandeja (mostrar a janela sem roubar o foco), que afeta só a âncora, não o desenho.
- **`C:\Dev\lacre-wt-design` é worktree de PR em rascunho** e pode sumir. Dele só se usa o método; se sumir, o relatório 3 § 2 e § 5 descreve o suficiente.
- **Os `.rs` do Lacre e da Guarita não foram abertos:** esta fase não precisa deles (nada de Rust aqui).
- **Limite do `check-added-large-files`:** suposto o padrão de 500 KB do `pre-commit-hooks` v6 (o `.pre-commit-config.yaml` não passa `--maxkb`).
- **Tamanho de hoje (~350 px):** estimado pelo código (colunas, margens, `wraplength`), não medido na tela; o app não foi aberto para não regravar o config.
- **Fontes na página publicada:** quem abrir o link fora do Windows (celular, Mac) vê fontes de reserva; a escolha deve ser feita no Windows.
- **Área útil de outras máquinas:** só esta foi medida; 1366 × 768 a 125% fica com ~6 px de folga.

## O que esta fase NÃO faz

- Não mexe em `reco.py`, `tray.py`, `build.ps1` nem no executável; não há o que recompilar.
- Não cria `app/` nem `engine/`, nem escreve Rust ou TypeScript de produto: a vitrine é HTML de demonstração.
- Não copia nada do Lacre (`styles.css`, `tokens.css`, teal `--seal`, selo, Regra da Vida, `render()` que refaz a árvore).
- Não decide a bandeja, o atalho global nem a janela sem foco: isso é da Fase 3, com a prova da Fase 0.
- Não liga o modo nota: só desenha onde o botão fica.
- Não troca o print nem os recursos do README público (só uma linha apontando o desenho, passo 16); isso vem com a tela real na Fase 3.
- Não deixa a Fase 3 com outra navegação: esta fase decide uma aba "Arquivo" (F1-D4) e chama de "Biblioteca" a aba de gravações; o md da Fase 3 já segue essa navegação, e o passo 16 confere que continua assim.

## Gatilho que fecha

- `node design/testar-anti-pulo.cjs` e `node design/testar-contrato.cjs` saem com 0, só com a direção escolhida.
- As versões `--sabotar` dos dois saem com 1.
- `design/DESIGN.md` tem "Direção escolhida" com as palavras do Gabriel, e o índice marca o pendente como decidido.
- Commits por pathspec feitos, docs e hub atualizados, md da Fase 3 conferido como alinhado às abas, aos testes e ao condutor desta fase (passo 16), relatório no sidecar.
- Só então a Fase 3 pode começar (ela também depende da Fase 2).

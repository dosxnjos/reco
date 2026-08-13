# Plano — ícones Lucide substituindo emoji nos botões (2026-08-12)

## Entendimento do pedido

O Gabriel notou, ao conferir o app pós-roadmap de UX/UI/lógica, que os
"ícones" dos botões (⬤ ⬛ ❚❚ ▶ ⚡ ✕ ✓ ⚙ ↺ ⌨ ⬆ ＋ 🎵) são inconsistentes entre
si: alguns caem na fonte `Segoe UI Symbol` (mono, vetorial), outros em
`Segoe UI Emoji` (bitmap colorido, sem anti-aliasing real) — a mistura é o
que ele quer resolver. Pedido: trocar por um icon set de verdade, baixado e
empacotado no app. Decisão já tomada na conversa: **Lucide** (MIT/ISC,
stroke-based, o mesmo family usado em boa parte de app moderno).

Fora do escopo deste plano: redesenho de layout, paleta de cores nova, ou
qualquer coisa em `docs/ARMADILHAS.md`/pipeline de transcrição — só a troca
de glifo por ícone vetorial nos pontos que hoje usam emoji como
texto de botão/link.

## O que NÃO muda (guardrails)

- **Tema custom continua funcionando.** O Gabriel escolhe cor de fundo/
  destaque livremente (`colorchooser`, `apply_theme`) — os ícones têm que
  acompanhar isso, não vir com cor fixa gravada no PNG. Mesma armadilha do
  F13 desta sessão (`_link` congelando `SUBTLE` no default-arg): resolver a
  cor **no momento do uso**, nunca uma vez só.
- **Bilíngue PT/EN e `tools/check_i18n.py` continuam intactos.** Ícone não é
  string traduzível; texto ao lado do ícone (quando existir) continua
  passando por `t()`/`tf()` normalmente.
- **`build.ps1`/PyInstaller continuam de um comando só**, sem dependência
  nova pesada no app **empacotado** — só o que já roda hoje (`Reco.exe`
  onedir, ~835 MB).
- **Nenhum ícone novo desliga o app se faltar.** Se um PNG não existir por
  algum motivo, cai num fallback (o texto/emoji antigo), nunca crash.

## Abordagem / arquitetura

**Vendorizar SVG, rasterizar em dev-time, tingir em runtime.** Três camadas:

1. **Fonte (dev-time, não vai pro `.exe`):** baixar os `.svg` do Lucide
   (`raw.githubusercontent.com/lucide-icons/lucide/main/icons/<nome>.svg`,
   licença ISC — permite embutir) pros 11 conceitos com ícone Lucide, salvos
   em `assets/icons_src/*.svg` (fonte de verdade, versionada; pasta separada
   da `assets/icons/` de saída DE PROPÓSITO — só a de saída entra no bundle).
   ⚠️ O Lucide renomeou a família `*-circle` para `circle-*`: o nome vigente
   é `circle-arrow-up` (`arrow-up-circle` dá **404**). Os 11 nomes da tabela
   abaixo foram testados contra o raw em 12/08/2026 — todos HTTP 200.
   ⬤/⬛ não vêm do Lucide (ver exceção abaixo): são 2 SVGs de uma linha
   embutidos como string no próprio `gerar_icones.py`.
2. **Máscara (dev-time, script novo `tools/gerar_icones.py`):** cada SVG vira
   um **PNG branco-sobre-transparente** (a máscara alfa) — 20px pros 8
   conceitos de ação (⬤ ⬛ ❚❚ ▶ ⚡ ✕ ✓ 🎵) e 16px pros 5 inline (⚙ ↺ ⌨ ⬆ ＋)
   — via `cairosvg` (confirmado instalável e funcional nesta máquina). As
   máscaras PNG vão em `assets/icons/*.png` e **essas sim** entram no bundle
   (`reco.spec` `datas`, mesmo padrão do `logo/logo_symbol_1x1.ico`).
   `cairosvg` fica só como dependência de **dev** (script em `tools/`, não
   importado por `reco.py`) — não precisa lidar com a fama de PyInstaller +
   Cairo DLL sofrendo pra empacotar, porque nunca vai dentro do `.exe`.
3. **Tinta (runtime, `reco.py`):** função `_icon(nome, cor, tamanho) ->
   ImageTk.PhotoImage`, cacheada em dict por `(nome, cor, tamanho)`. Abre a
   máscara PNG com `Pillow` (já presente no venv, `12.2.0` — só falta entrar
   em `requirements.txt` explicitamente) e recolore via
   `Image.new("RGBA", ..., cor); .putalpha(mascara.getchannel("A"))`. Troca
   de tema (`apply_theme`/`_rebuild_ui`, que já destrói e recria tudo)
   simplesmente pede a cor nova — o cache velho fica órfão e não atrapalha
   (chaves diferentes).

**Exceção deliberada — ⬤ Gravar e ⬛ Parar não usam ícone Lucide.** Motivo:
Lucide é 100% *stroke* (contorno), sem variante preenchida — usar o contorno
pros dois símbolos mais universais de gravação/parada (círculo e quadrado
**sólidos**) quebraria a convenção que todo app de gravação usa.
**Correção de premissa (auditoria de 12/08):** hoje eles NÃO são canvas — são
glifos de texto em `_btn` (`reco.py:2825-2827`; o único `tk.Canvas` do
arquivo é o `VuMeter`, `reco.py:2423`). Mantê-los como texto preservaria a
inconsistência que motivou este plano justamente nos dois botões mais
visíveis do app. Solução: o próprio `gerar_icones.py` rasteriza dois SVGs de
uma linha escritos à mão (`<circle cx="12" cy="12" r="8" fill="white"/>` e
`<rect x="5" y="5" width="14" height="14" rx="2" fill="white"/>`, viewBox
24×24), embutidos como string no script — mesmíssimo pipeline de máscara +
tintura dos demais, zero caso especial no runtime.

## Mapa de substituição (13 conceitos)

| hoje (emoji) | conceito | ícone Lucide | tamanho |
| --- | --- | --- | --- |
| ⬤ | gravar | `record` (SVG próprio, círculo `fill`) | 20 |
| ⬛ | parar | `stop` (SVG próprio, quadrado `fill`) | 20 |
| ❚❚ | pausar | `pause` | 20 |
| ▶ | reproduzir/continuar | `play` | 20 |
| ⚡ | transcrever | `zap` | 20 |
| ✕ | excluir | `trash-2` (ver Decisões) | 20 |
| ✓ | salvar | `check` | 20 |
| ⚙ | opções | `settings` | 16 |
| ↺ | atualizar (dispositivos/biblioteca) | `refresh-cw` | 16 |
| ⌨ | atalho de teclado | `keyboard` | 16 |
| ⬆ | nova versão disponível | `circle-arrow-up` | 16 |
| ＋ | escolher arquivo | `plus` | 16 |
| 🎵 | converter para MP3 | `music` | 20 |

⚠️ **Fora do escopo: o "✓" de célula da biblioteca** (`reco.py:4005` e
`reco.py:4066`, coluna "tem .txt" do Treeview). `ttk.Treeview` só aceita
imagem na coluna `#0` — célula de coluna comum é texto e ponto. Esse ✓ fica
como está e **não conta** como pendência no grep do passo 4.

Pontos de uso confirmados por grep em `reco.py` — **~30 ocorrências vivas**
cobrindo os 13 conceitos (inclui a view "Biblioteca" da outra sessão,
`_lib_action`, que também usa ▶/⚡/✕/↺): view gravar (`_build_recording`),
view transcrever, view converter, view biblioteca, links de opções/atalho/
atualização, menu do ⚡, tooltip de hover, e os rótulos dinâmicos de
`_btn_label` (`reco.py:4373-4382`).

## Decisões e trade-offs

- **`trash-2` em vez de `x` pro Excluir.** O glifo atual (✕) é um X genérico;
  `trash-2` (lata de lixo) comunica "isto é destrutivo/vai pra Lixeira" com
  mais clareza — e a Fase 1.2 desta sessão já trocou o `unlink()` por
  `SHFileOperationW` (Lixeira de verdade), então o ícone passa a bater com o
  comportamento real. Custo: é a única troca que muda o *significado* visual,
  não só o traço — vale confirmar com o Gabriel antes de executar (pergunta
  aberta no fechamento deste plano, não decidida sozinho).
- **Dois tamanhos fixos (16/20px), não escala por DPI.** Renderizar só nesses
  dois tamanhos evita borrão de upscale (Tk não escala `PhotoImage`
  suavemente) sem precisar decidir uma matriz DPI× tamanho agora. Se ficar
  pequeno/grande num monitor específico, é ajuste de valor, não de
  arquitetura — YAGNI até incomodar.
- **Pillow vira dependência real do app** (estava só transitivo). Baixo
  risco: é uma das libs mais testadas com PyInstaller que existe. ⚠️ **MAS o
  `reco.spec` hoje EXCLUI o PIL de propósito** (`excludes=[..., 'PIL', ...]`,
  linha ~57 — herança de quando era lib transitiva indesejada). Sem tirar
  `'PIL'` dos excludes, o exe empacota **sem Pillow** e, por causa do
  fallback silencioso deste plano, o sintoma é o pior possível: ícones
  perfeitos no dev, emoji antigo no `Reco.exe`, zero erro. Além disso,
  `PIL.ImageTk` precisa de `PIL._tkinter_finder` como hiddenimport —
  armadilha clássica de PyInstaller + ImageTk.
- **`cairosvg` nunca entra no `.exe`** — só gera os PNGs uma vez, no
  desenvolvimento. Se o Gabriel trocar de máquina de dev, `pip install
  cairosvg` de novo resolve; não é dependência de quem só usa o app.

## Passos

1. [ ] **Baixar os SVGs Lucide** (`play`, `pause`, `zap`, `trash-2`, `check`,
   `settings`, `refresh-cw`, `keyboard`, `circle-arrow-up` ⚠️ (nome novo —
   `arrow-up-circle` dá 404), `plus`, `music`) em `assets/icons_src/*.svg`
   via `curl` (raw.githubusercontent.com; os 11 nomes testados com HTTP 200
   em 12/08/2026). — **prova:** `ls assets/icons_src/*.svg | wc -l` → 11.
2. [ ] **`tools/gerar_icones.py`:** roda `cairosvg` sobre os 11 SVGs de
   `assets/icons_src/` **+ os 2 SVGs próprios embutidos no script**
   (`record`/`stop`, círculo e quadrado com `fill` — ver exceção acima),
   produzindo máscara branca-sobre-transparente em `assets/icons/*.png`:
   20px pros 8 conceitos de ação (`record`, `stop`, `pause`, `play`, `zap`,
   `trash-2`, `check`, `music`) e 16px pros 5 inline (`settings`,
   `refresh-cw`, `keyboard`, `circle-arrow-up`, `plus`). — **prova:**
   `python tools/gerar_icones.py && ls assets/icons/*.png | wc -l` → **13**
   (8 + 5; nenhum conceito sai em dois tamanhos — o ✓ de 16px caiu do escopo
   junto com a célula do Treeview).
3. [ ] **`_icon(nome, cor, tamanho)` em `reco.py`:** abre a máscara com
   Pillow, recolore, cacheia em dict, devolve `ImageTk.PhotoImage` (guardar
   referência viva — armadilha clássica do Tk, `PhotoImage` sem referência
   forte vira lixo e o botão fica em branco). Fallback: se a máscara não
   existir (ou o `import PIL` falhar), `_icon` devolve `None` e o **caller**
   mantém o `text=` com o glifo antigo — o branch fica no ponto de uso, não
   escondido dentro de `_icon`. — **prova:** `python -c "import
   reco; im = reco.App.__new__(reco.App); print(type(im))"` não é suficiente
   (precisa de Tk root); prova real é rodar o app e ver os ícones — manual
   (ver risco abaixo).
4. [ ] **Trocar os pontos de uso dos 13 conceitos** (~30 ocorrências vivas,
   ver mapa) de `text="⚡"` / `t("⚡  Transcrever")` pra
   `image=self._icon(...)` (+ `compound="left"` nos que têm ícone-mais-texto,
   ex. "⬛  Parar"). ⚠️ Tirar o emoji da string **muda a CHAVE de tradução**
   ("⚡  Transcrever" → "Transcrever"): atualizar o `_TR_EN` inteiro em
   paralelo (`reco.py:271-430`) e os rótulos dinâmicos de `_btn_label`
   (`reco.py:4373-4382`). O ✓ de célula do Treeview fica como texto (fora do
   escopo, ver mapa). — **prova (dupla):** (a) `python tools/check_i18n.py`
   verde; (b) `grep -n "⚡\|✕\|✓\|⚙\|↺\|⌨\|⬆\|＋\|🎵\|❚❚\|▶\|⬤\|⬛" reco.py`
   só deve sobrar no ✓ do Treeview e em comentários/docstrings que documentam
   a troca, não em `text=`/`t(...)` de botão vivo — conferir manualmente cada
   ocorrência restante.
5. [ ] **`reco.spec`:** (a) ⚠️ **REMOVER `'PIL'` da lista `excludes`**
   (linha ~57 — sem isso o exe sai sem Pillow e todos os ícones caem no
   fallback em silêncio); (b) adicionar `PIL.Image`, `PIL.ImageTk` e
   `PIL._tkinter_finder` aos `hiddenimports`; (c) adicionar
   `('assets/icons', 'assets/icons')` aos `datas` (só a pasta de saída — a
   `assets/icons_src/` NÃO entra). `requirements.txt` ganha `Pillow`
   explícito. — **prova:** `powershell -ExecutionPolicy Bypass -File
   build.ps1` verde, `dist/Reco/_internal/assets/icons/` com os 13 PNGs, e
   **abrir o `dist\Reco\Reco.exe` e ver os ícones vetoriais** (não o emoji do
   fallback) — é o único jeito de pegar Pillow faltando dentro do bundle.
6. [ ] **Checar tema custom:** trocar cor de destaque em Opções (manual) e
   confirmar que os ícones tingidos acompanham (não ficam com a cor antiga
   presa). — manual, mesma razão do F13: é exatamente o bug que esse plano
   promete não reintroduzir.
7. [ ] **Screenshot + docs:** recapturar `docs/screenshot.png` com os ícones
   novos; se `trash-2` for aprovado, atualizar qualquer menção a "✕" em
   `CLAUDE.md`/`README.md`. — **prova:** `git log -1 --stat
   docs/screenshot.png` mostra a troca.
8. [ ] **Commit + consolidar:** um commit (ou um por etapa grande, a critério
   de quem executar), roadmap fechado, diário do dia atualizado.

## Riscos / o que pode dar errado

- **Nada disso é automatizável de ponta a ponta.** Assim como o roadmap
  anterior desta sessão, qualidade visual de ícone só se confirma olhando —
  os passos 3, 4, 5 e 6 têm componente de prova manual declarado, não por
  preguiça, mas porque Tk não compensa automatizar (mesma régua do roadmap
  de UX/UI já fechado). A exceção nova: o passo 4 ganhou uma prova
  automatizável de verdade (`tools/check_i18n.py`), porque a troca mexe nas
  chaves de tradução.
- **O fallback silencioso pode mascarar Pillow ausente NO EXE** — no dev
  tudo funciona e no bundlado tudo volta pro emoji sem nenhum erro (o
  `reco.spec` exclui `'PIL'` hoje). É por isso que tirar o PIL dos
  `excludes` é item explícito do passo 5, e a prova dele exige abrir o
  `Reco.exe` e OLHAR os ícones, não só listar os PNGs no `_internal/`.
- **`cairosvg` pode exigir Cairo instalado no Windows** dependendo de como o
  pip resolveu a wheel nesta máquina (testado e funcionou aqui, mas se a
  execução for noutra máquina de dev, confirmar `pip install cairosvg`
  antes de rodar `tools/gerar_icones.py`).
- **Pergunta em aberto pro Gabriel, não decidida sozinho:** `trash-2` no
  lugar do ✕ pro Excluir — se ele preferir manter `x` puro (mudança mais
  conservadora), trocar só uma linha da tabela antes do passo 1.
- **Ícone sem referência viva vira botão em branco** (armadilha comum do
  `tk.PhotoImage` — o GC coleta a imagem se nada segura uma referência
  Python). Guardar em `self._icon_cache` (dict de instância), não variável
  local de função.

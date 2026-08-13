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
   licença ISC — permite embutir) pros ~13 conceitos usados hoje, salvos em
   `assets/icons/lucide_src/*.svg` (fonte de verdade, versionada).
2. **Máscara (dev-time, script novo `tools/gerar_icones.py`):** cada SVG vira
   um **PNG branco-sobre-transparente** (a máscara alfa) em dois tamanhos —
   16px (ícones inline: ⚙ ↺ ⌨ ⬆) e 20px (botões de ação: ▶ ❚❚ ⚡ ✕ ✓ 🎵) — via
   `cairosvg` (confirmado instalável e funcional nesta máquina). As máscaras
   PNG vão em `assets/icons/*.png` e **essas sim** entram no bundle
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

**Exceção deliberada — ⬤ Gravar e ⬛ Parar continuam desenhados na mão**, não
viram ícone Lucide. Motivo: Lucide é 100% *stroke* (contorno), sem variante
preenchida — usar o contorno pros dois símbolos mais universais de
gravação/parada (círculo e quadrado **sólidos**) quebraria a convenção que
todo app de gravação usa. Um retângulo/oval `tk.Canvas` preenchido, tingido
com a cor do tema, já é nítido e não precisa de ícone nenhum — mantém o que
já funciona bem hoje.

## Mapa de substituição (13 conceitos)

| hoje (emoji) | conceito | ícone Lucide | tamanho |
| --- | --- | --- | --- |
| ⬤ | gravar | *(mantém — canvas desenhado)* | — |
| ⬛ | parar | *(mantém — canvas desenhado)* | — |
| ❚❚ | pausar | `pause` | 20 |
| ▶ | reproduzir/continuar | `play` | 20 |
| ⚡ | transcrever | `zap` | 20 |
| ✕ | excluir | `trash-2` (ver Decisões) | 20 |
| ✓ | salvar / marca de "tem .txt" | `check` | 20 / 16 |
| ⚙ | opções | `settings` | 16 |
| ↺ | atualizar (dispositivos/biblioteca) | `refresh-cw` | 16 |
| ⌨ | atalho de teclado | `keyboard` | 16 |
| ⬆ | nova versão disponível | `arrow-up-circle` | 16 |
| ＋ | escolher arquivo | `plus` | 16 |
| 🎵 | converter para MP3 | `music` | 20 |

Pontos de uso confirmados por grep em `reco.py` (inclui a view "Biblioteca"
da outra sessão, `_lib_action`, que também usa ▶/⚡/✕/↺): view gravar
(`_build_recording`), view transcrever, view converter, view biblioteca,
links de opções/atalho/atualização, menu do ⚡, tooltip de hover.

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
  risco: é uma das libs mais testadas com PyInstaller que existe; ainda assim
  entra explícito em `requirements.txt` e o build precisa confirmar que o
  `reco.spec` não precisa de hook extra (checar `collect_data_files`/
  `hiddenimports` pro Pillow, capaz de já vir de outro pacote).
- **`cairosvg` nunca entra no `.exe`** — só gera os PNGs uma vez, no
  desenvolvimento. Se o Gabriel trocar de máquina de dev, `pip install
  cairosvg` de novo resolve; não é dependência de quem só usa o app.

## Passos

1. [ ] **Baixar os SVGs Lucide** (`play`, `pause`, `zap`, `trash-2`, `check`,
   `settings`, `refresh-cw`, `keyboard`, `arrow-up-circle`, `plus`, `music`)
   em `assets/icons/lucide_src/*.svg` via `curl` (raw.githubusercontent.com,
   já confirmado acessível nesta sessão). — **prova:** `ls
   assets/icons/lucide_src/*.svg | wc -l` → 11.
2. [ ] **`tools/gerar_icones.py`:** script que roda `cairosvg` sobre cada SVG
   em `assets/icons/lucide_src/`, produz máscara branca-sobre-transparente em
   16px e 20px (os ícones de 16 só pros 5 conceitos inline; os de 20 pros 6
   de ação — ver tabela) em `assets/icons/*.png`. — **prova:**
   `python tools/gerar_icones.py && ls assets/icons/*.png | wc -l` → 17
   (11 conceitos, 6 só em 20px + 5 só em 16px = confirmar contagem exata ao
   escrever o script).
3. [ ] **`_icon(nome, cor, tamanho)` em `reco.py`:** abre a máscara com
   Pillow, recolore, cacheia em dict, devolve `ImageTk.PhotoImage` (guardar
   referência viva — armadilha clássica do Tk, `PhotoImage` sem referência
   forte vira lixo e o botão fica em branco). Fallback pro texto/emoji atual
   se o arquivo da máscara não existir. — **prova:** `python -c "import
   reco; im = reco.App.__new__(reco.App); print(type(im))"` não é suficiente
   (precisa de Tk root); prova real é rodar o app e ver os ícones — manual
   (ver risco abaixo).
4. [ ] **Trocar os 13 pontos de uso** (tabela acima) de `text="⚡"` /
   `t("⚡  Transcrever")` pra `image=self._icon(...)` (+ `compound="left"`
   nos que têm ícone-mais-texto, ex. "⬛ Parar"). Manter ⬤/⬛ como estão
   (canvas). — **prova:** `grep -n "⚡\|✕\|✓\|⚙\|↺\|⌨\|⬆\|＋\|🎵\|❚❚\|▶" reco.py`
   só deve sobrar nos `_TR_EN`/comentários/docstrings que documentam a
   troca, não em `text=`/`t(...)` de botão vivo — conferir manualmente cada
   ocorrência restante.
5. [ ] **`reco.spec`:** adicionar `assets/icons/*.png` aos `datas`, mesmo
   padrão de `logo/logo_symbol_1x1.ico`. `requirements.txt` ganha `Pillow`
   explícito. — **prova:** `powershell -ExecutionPolicy Bypass -File
   build.ps1` verde, `dist/Reco/_internal/assets/icons/` (ou equivalente,
   conferir onde o PyInstaller coloca) com os PNGs presentes.
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
  os passos 3, 4 e 6 têm prova manual declarada, não por preguiça, mas
  porque Tk não compensa automatizar (mesma régua do roadmap de UX/UI já
  fechado).
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

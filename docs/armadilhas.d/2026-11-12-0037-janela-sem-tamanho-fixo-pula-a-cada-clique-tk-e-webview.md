---
titulo: Janela sem tamanho fixo pula a cada clique (Tk e WebView)
data: 2026-11-12
---
**Sintoma:** a janela do Reco muda de altura e de largura a cada clique (Gravar, Parar, abrir um painel,
status que quebra em mais linhas), e o botão em que se ia clicar de novo sai do lugar. Foi a queixa que
abriu o roadmap Reco em Rust (11/11/2026: "uma interface que não para de ficar se mexendo sempre que eu
clico em um botão").

**Causa:** o toplevel do Tk não tem tamanho fixo e acompanha o conteúdo (`pack` com conteúdo variável), e
há 5 chamadas a `geometry("")` que reencaixam a janela de propósito (`reco.py:3323, 3467, 3562, 3602,
4338`). Somam-se o status com quebra de linha, botões que somem e aparecem e painéis que abrem. Trocar de
toolkit não resolve sozinho: numa WebView (Tauri) o mesmo acontece com área sem altura reservada, texto que
quebra, número sem `tabular-nums` ou `transform` no clique.

**O que fazer:** seguir o contrato de tela `design/DESIGN.md` R1–R8 (janela fixa de 400 × 560, área com
altura reservada, status em uma linha com reticências, números de largura fixa, transição só de opacidade
e cor, clique que não move o botão, condicional por opacidade, calha reservada) e rodar
`node design/testar-anti-pulo.cjs` (e `testar-contrato.cjs`) antes de mexer em tela; o `--sabotar` dos dois
tem de sair com 1.

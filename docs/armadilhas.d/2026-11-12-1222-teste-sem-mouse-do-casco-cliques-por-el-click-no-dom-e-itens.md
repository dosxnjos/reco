---
titulo: Teste sem mouse do casco: cliques por el.click no DOM e itens da bandeja por WM_COMMAND
data: 2026-11-12
---
**Sintoma:** o teste real do app novo precisa clicar na janela e no menu da bandeja, mas o dono está usando o
computador: `SendInput` mexe no cursor dele, o clique do Playwright (`page.click`) dispara `pointerdown`, que
chama `window_pin` e toma o foco, e abrir o app sem `--oculto` (ou o item Abrir) faz `mostrar_fixada` e rouba o
foreground. Abrir o menu da bandeja por mensagem também rouba o foco (`TrackPopupMenu` traz o casco à frente).

**Causa:** foco e cursor são do usuário; qualquer caminho que passe pela entrada real ou por `set_focus` interfere
no que ele estiver digitando.

**O que fazer:** abrir o casco instalado com `--oculto` e `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=<porta>`
(a página do release é `http://tauri.localhost/`, não o `localhost:1430` do Vite), conectar com
`chromium.connectOverCDP` e clicar por `page.evaluate(() => el.click())`: dispara só o `click`, sem `pointerdown`.
Itens da bandeja sem abrir o menu: `PostMessageW(<janela tray_icon_app do pid>, WM_COMMAND, id, 0)`. O muda 0.20
numera os itens a partir de 1000 na ordem de criação (`muda/src/platform_impl/windows/mod.rs:42`): no
`bandeja.rs:127-130`, Gravar 1000, Pausar 1001, Abrir 1002 (mostra e foca: evitar), Sair 1003. Se o
`bandeja.rs` mudar a ordem ou criar outro item de menu antes, os ids andam: conferir com o Gravar (1000) antes
de mandar o Sair.

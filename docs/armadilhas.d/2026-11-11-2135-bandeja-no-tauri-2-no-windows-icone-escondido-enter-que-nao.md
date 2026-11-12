---
titulo: Bandeja no Tauri 2 no Windows: ícone escondido, Enter que não chega e posicionador do macOS
data: 2026-11-11
---
**Sintoma:** no spike da bandeja (Fase 0 do Reco em Rust), o hover no ícone nunca mostrava a janela
(`enter=nunca`), mesmo com o `icone_rect` caindo dentro da barra de tarefas. Quando aparecia, a janela nascia
em cima da barra, metade fora da tela, e às vezes não sumia ao tirar o mouse.

**Causa:** são cinco coisas distintas, medidas em 11/11/2026 (Windows 11, escala 125%):

- Ícone novo nasce escondido no menu "^" e o `TrayIcon::rect()` devolve o rect do botão "^", não o do ícone.
  As coordenadas são as mesmas antes e depois de promover: "rect dentro da barra" não prova nada.
- `SetCursorPos` sobre o ícone não gera o `Enter` (4 de 4); `SendInput` com movimento em passos gera.
- `Position::TrayBottomCenter` do `tauri-plugin-positioner` 2.4.0 usa `y = tray_y` (barra de menus do macOS,
  no alto da tela): no Windows a janela cai sobre a barra.
- O `Leave` do `tray-icon` 0.25.1 só se arma num `Move` depois do `Enter`: pode não chegar nunca.
- Janela comum rouba o foco ao nascer mesmo escondida, e o `Focused(true)` do tao chega sem foco real
  quando a janela é `focusable(false)`.

**O que fazer:**

- Promover o ícone pelo `IsPromoted=1` em `HKCU\Control Panel\NotifyIconSettings\<id>` (entrada do exe, que
  nasce depois da 1ª execução) ou pedir ao usuário para fixá-lo; em teste, simular o mouse por `SendInput`.
- Ancorar a janela pelo rect do ícone (como `_anchor_to_tray` do `reco.py`), não pelo positioner.
- Esconder por polling do cursor iniciado no `Enter`, não pelo `Leave`.
- Criar a janela com `focused(false)` + `focusable(false)` e mostrar com `show()`; no clique que fixa,
  `set_focusable(true)` antes de `set_focus()`. Nada de lógica em cima do evento `Focused`.
- Evidência e as outras pegadinhas (bordas invisíveis da janela sem moldura, `Win32_Security` no
  `windows-sys`): `roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-0-relatorio.md` § passos 6 a 8.

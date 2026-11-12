---
titulo: App velho sem mouse: o Tk ignora clique por mensagem; Gravar e Parar pelo menu da bandeja
data: 2026-11-12
---
**Sintoma:** com o dono usando a máquina (sem `SendInput`), o ensaio da volta (Fase 4, passo 16) precisa gravar 30 s
no `Reco.exe` velho. `BM_CLICK` e `WM_LBUTTONDOWN/UP` postados no `Button` "Gravar" não fazem nada: a tela segue com 1
botão e nenhum MP3 nasce. Os links de Opções do velho ("Remover/Criar atalho") também não respondem.

**Causa:** o Tk monta o evento de clique a partir do estado real do mouse (botão de fato pressionado), não da mensagem;
clique sem o mouse físico é descartado. O menu da bandeja do velho (`tray.py`) usa `TrackPopupMenu` com
`TPM_RETURNCMD`, então `WM_COMMAND` na janela do ícone também não aciona nada (o do casco novo aciona).

**O que fazer:** abrir o menu por mensagem e escolher por tecla postada no próprio menu, sem tocar o teclado físico:
`PostMessageW(<RecoTrayWindow do pid>, WM_APP+1, 0, WM_RBUTTONUP)` abre o menu (itens `Gravar · Abrir · Sair`;
gravando, `Parar · Pausar · Abrir · Sair`); na janela `#32768` visível, `WM_KEYDOWN`/`WM_KEYUP` `VK_DOWN` e depois
`VK_RETURN` escolhem o 1º item. Conferir o 1º item por `MN_GETHMENU` + `GetMenuStringW` antes do Enter e mandar
`VK_ESCAPE` se não for o esperado. O menu abre no ponto do cursor e o velho toma a frente (interrupção visual curta).
O atalho do passo 16 e) se refaz pelo equivalente por script dos campos de `reco.py:4902-4908`.

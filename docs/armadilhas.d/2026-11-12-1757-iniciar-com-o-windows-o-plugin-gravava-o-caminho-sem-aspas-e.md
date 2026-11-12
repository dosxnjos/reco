---
titulo: Iniciar com o Windows: o plugin gravava o caminho sem aspas e deixava a marca do StartupApproved (consertado no casco)
data: 2026-11-12
---
**Sintoma:** com o `tauri-plugin-autostart`, ligar "Iniciar com o Windows" gravava em `HKCU\…\CurrentVersion\Run` o valor
`Reco` = `C:\Users\<nome com espaço>\AppData\Local\Reco\reco.exe --oculto`, **sem aspas** (caminho sem aspas clássico: o
Windows tenta `C:\Users\<primeira palavra>.exe` antes do exe certo, e um `.exe` plantado ali subiria no lugar). Desligar
apagava o `Run`, mas deixava `Reco` em `HKCU\…\Explorer\StartupApproved\Run`. Visto no passo 13 da Fase 4 (12/11/2026),
no instalador `84EE1142`, que é o app instalado hoje: **o instalado ainda tem o defeito** até a próxima reinstalação.

**Causa:** o plugin passa `current_exe()` cru ao `auto-launch` 0.6.0, que monta `format!("{} {}", caminho, args)`
(`windows.rs:77`), e o `disable()` dele só apaga o `Run`. O plugin não deixa trocar o caminho (o `build()` crava o
`current_exe`), então não há como corrigir "por cima" dele.

**O que fazer:** o casco não usa mais o plugin. O `app/src-tauri/src/autostart.rs` grava o valor à mão como
`"<exe>" --oculto` (`valor_run`) e desligar apaga o `Run` **e** a marca do `StartupApproved`; na partida, um valor
antigo diferente (já ligado) é regravado com aspas. Não voltar ao `tauri-plugin-autostart`. Os testes
(`cargo test … autostart`) rodam numa chave só de teste, `HKCU\Software\RecoTeste`, e a apagam no fim; nunca testar no
`Run` real do dono. No Git Bash, `reg query`/`reg delete` precisam de `MSYS_NO_PATHCONV=1` (senão o `/v` vira caminho).

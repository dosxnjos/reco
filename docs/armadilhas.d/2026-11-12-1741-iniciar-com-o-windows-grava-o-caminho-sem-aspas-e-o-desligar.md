---
titulo: Iniciar com o Windows grava o caminho sem aspas e o desligar deixa a marca do StartupApproved
data: 2026-11-12
---
**Sintoma:** ligar "Iniciar com o Windows" no app novo grava em `HKCU\…\CurrentVersion\Run` o valor `Reco` =
`C:\Users\<nome com espaço>\AppData\Local\Reco\reco.exe --oculto`, **sem aspas**. Desligar apaga esse valor, mas deixa
`Reco` (`02 00…`, habilitado) em `HKCU\…\Explorer\StartupApproved\Run`.

**Causa:** o `auto-launch` 0.6.0 (dependência do `tauri-plugin-autostart` 2.7.0) monta o valor com
`format!("{} {}", app_path, args)` (`windows.rs:77`) e só escreve a marca do Gerenciador de Tarefas ao ligar; o
`disable` remove só o valor do `Run`. Sem aspas, o Windows tenta `C:\Users\<primeira palavra>.exe` e segue até achar o
exe: funciona, mas um `.exe` plantado num desses nomes subiria no lugar.

**O que fazer:** no casco, passar ao plugin o caminho já entre aspas (ou gravar o valor à mão); depois de desligar,
apagar a marca com `reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" /v Reco /f`
(no Git Bash, com `MSYS_NO_PATHCONV=1`, senão o `/v` vira caminho). A subida no boot com o valor sem aspas ainda não
foi vista (pendente de reiniciar).

---
titulo: Desligar o iniciar com o Windows do casco deixa a marca no StartupApproved
data: 2026-11-12
---
**Sintoma:** depois de ligar e desligar o "iniciar com o Windows" do casco (`definir_autostart`), o
`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "Reco Novo"` já não acha nada, mas
`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run` continua com o valor
`Reco Novo` (`REG_BINARY 02 00 …`, a marca de "habilitado" do Gerenciador de Tarefas). Visto na verificação
manual do passo 10 da Fase 3 (12/11/2026).

**Causa:** o `tauri-plugin-autostart` usa o `auto-launch` 0.6.0. O `enable()` grava o `Run` **e** o
`StartupApproved\Run` (`src/windows.rs:74-97`); o `disable()` só apaga o `Run` (`:133-145`). Sem o `Run`, o
Windows não abre nada, então a sobra é inofensiva, mas a máquina não volta a como estava.

**O que fazer:** depois de um teste que liga o autostart, apagar também a sobra
(`reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" /v "Reco Novo" /f`).
Se a sobra incomodar no app de verdade, o `definir_autostart(false)` do `atalho.rs` pode apagar o mesmo valor.

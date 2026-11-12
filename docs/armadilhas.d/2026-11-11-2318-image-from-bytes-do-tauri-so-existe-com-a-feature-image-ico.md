---
titulo: Image from_bytes do Tauri só existe com a feature image-ico
data: 2026-11-11
---
**Sintoma:** no casco (`app/src-tauri`), `tauri::image::Image::from_bytes(include_bytes!("../icons/tray_rec.ico"))`
não compila: `E0599 no associated function or constant named from_bytes found for struct Image`. O
compilador sugere `new_owned`/`from_icon_resource`, o que leva a decodificar o `.ico` à mão.

**Causa:** no Tauri 2 (2.12.5), `from_bytes` e `from_path` só existem com a feature `image-ico` (ou
`image-png`) do crate `tauri`. A Guarita e o spike da Fase 0 não precisaram dela porque usam o
`default_window_icon()`; a bandeja do Reco troca entre dois ícones (`tray_idle.ico` e `tray_rec.ico`).

**O que fazer:** `tauri = { version = "2", features = ["tray-icon", "image-ico"] }` no
`app/src-tauri/Cargo.toml`. Os dois `.ico` vão embutidos no binário (`include_bytes!`) e o ícone só é
trocado quando muda de cor (`bandeja::atualizar`), não a cada `timer`.

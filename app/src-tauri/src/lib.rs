//! Casco do Reco (Fase 3): sobe o motor Python e liga comandos e eventos à interface.

pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("erro ao montar o Reco");
}

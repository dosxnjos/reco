use std::path::PathBuf;

/// `bundle.resources` leva `../../engine/dist/reco-engine/` (o onedir do PyInstaller, Fase 2) para dentro do
/// app. O tauri-build recusa rodar se esse caminho não existe, o que travaria o `cargo check` e o debug (que
/// sobe o motor do fonte com `python -m reco_engine`). Então (molde: Lacre, `src-tauri/build.rs`):
/// - debug: cria a pasta vazia (fora do git) se o motor ainda não foi congelado;
/// - release: falha alto, porque instalador sem motor não serve para nada.
fn ensure_engine_resource() {
    let manifest = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let dir = manifest
        .join("..")
        .join("..")
        .join("engine")
        .join("dist")
        .join("reco-engine");
    // o build script roda no host: perguntar ao cargo o SO do *alvo*
    let target_windows = std::env::var("CARGO_CFG_TARGET_OS")
        .map(|os| os == "windows")
        .unwrap_or(false);
    let exe = dir.join(if target_windows { "reco-engine.exe" } else { "reco-engine" });
    println!("cargo:rerun-if-changed={}", exe.display());

    let release = std::env::var("PROFILE").map(|p| p == "release").unwrap_or(false);
    if release && !exe.exists() {
        panic!(
            "motor congelado não encontrado em {}: rode antes `python engine/build.py` (Fase 2)",
            exe.display()
        );
    }
    if !dir.exists() {
        std::fs::create_dir_all(&dir).expect("criar a pasta de recurso do motor");
    }
}

fn main() {
    ensure_engine_resource();
    tauri_build::build()
}

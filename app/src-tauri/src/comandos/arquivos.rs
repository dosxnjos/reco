//! Comandos de arquivo: copiar o caminho entre aspas, abrir e revelar (só o que é do Reco, F3-D9), escolher
//! arquivo ou pasta e abrir link externo (só http/https; molde: Lacre `commands.rs:214-229`).

use std::path::Path;

use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_clipboard_manager::ClipboardExt;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

/// Áudio e vídeo que o Reco abre ou converte (`reco.py:153-154`), mais as saídas de texto dele.
const EXTENSOES_DO_RECO: &[&str] = &[
    "mp3", "wav", "m4a", "ogg", "opus", "flac", "aac", "wma", // áudio
    "mp4", "mkv", "mov", "avi", "webm", "m4v", "wmv", "flv", "ts", // vídeo
    "txt", "md", // transcrição, nota e resumo
];
const AUDIO: &[&str] = &["mp3", "wav", "m4a", "ogg", "opus", "flac", "aac", "wma"];
const VIDEO: &[&str] = &["mp4", "mkv", "mov", "avi", "webm", "m4v", "wmv", "flv", "ts"];

/// O caminho entre aspas duplas, como `_copiar_caminho` (`reco.py:4073-4080`): cola inteiro mesmo com espaço.
pub fn entre_aspas(caminho: &str) -> String {
    format!("\"{caminho}\"")
}

/// Grava `"<caminho>"` no clipboard. Usado pelo comando e pelo Rust (nota pronta, F3-D4).
pub fn copiar_caminho<R: Runtime>(app: &AppHandle<R>, caminho: &str) -> Result<(), String> {
    app.clipboard().write_text(entre_aspas(caminho)).map_err(|e| e.to_string())
}

/// `Ok` para pasta existente ou arquivo de extensão do Reco; recusa executável, atalho e o resto (F3-D9).
pub fn abrivel(caminho: &Path) -> Result<(), String> {
    if caminho.is_dir() {
        return Ok(());
    }
    let ext = caminho.extension().and_then(|e| e.to_str()).map(str::to_ascii_lowercase).unwrap_or_default();
    if EXTENSOES_DO_RECO.contains(&ext.as_str()) {
        Ok(())
    } else {
        Err(format!("refused: extensão não permitida: {}", caminho.display()))
    }
}

/// Só http/https com host.
pub fn url_web(url: &str) -> Result<tauri::Url, String> {
    let parsed = tauri::Url::parse(url.trim()).map_err(|e| format!("invalid url: {e}"))?;
    match parsed.scheme() {
        "http" | "https" if parsed.host_str().is_some() => Ok(parsed),
        _ => Err("refused: só links http/https".into()),
    }
}

#[tauri::command]
pub fn copy_path<R: Runtime>(app: AppHandle<R>, path: String) -> Result<(), String> {
    copiar_caminho(&app, &path)
}

#[tauri::command]
pub fn open_path<R: Runtime>(app: AppHandle<R>, path: String) -> Result<(), String> {
    abrivel(Path::new(&path))?;
    app.opener().open_path(&path, None::<&str>).map_err(|e| e.to_string())
}

/// Mostra o arquivo selecionado no Explorer (ou abre a pasta).
#[tauri::command]
pub fn reveal_path<R: Runtime>(app: AppHandle<R>, path: String) -> Result<(), String> {
    let p = Path::new(&path);
    abrivel(p)?;
    if p.is_dir() {
        return app.opener().open_path(&path, None::<&str>).map_err(|e| e.to_string());
    }
    app.opener().reveal_item_in_dir(p).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn open_external<R: Runtime>(app: AppHandle<R>, url: String) -> Result<(), String> {
    let url = url_web(&url)?;
    app.opener().open_url(url.as_str(), None::<&str>).map_err(|e| e.to_string())
}

/// Diálogo nativo de escolher arquivo, com a janela como pai. `kind`: `audio` (só áudio) ou `midia` (áudio e
/// vídeo, para Transcrever e Converter). Devolve o caminho ou `None` se cancelou.
#[tauri::command]
pub async fn pick_file<R: Runtime>(app: AppHandle<R>, kind: String) -> Result<Option<String>, String> {
    let exts: Vec<&str> = match kind.as_str() {
        "audio" => AUDIO.to_vec(),
        "midia" => AUDIO.iter().chain(VIDEO).copied().collect(),
        outro => return Err(format!("bad_args: kind desconhecido: {outro}")),
    };
    let mut d = app.dialog().file().add_filter("Áudio e vídeo", &exts);
    if let Some(w) = app.get_webview_window(crate::hover::JANELA) {
        d = d.set_parent(&w);
    }
    let (tx, rx) = tokio::sync::oneshot::channel();
    d.pick_file(move |p| {
        let _ = tx.send(p);
    });
    let escolhido = rx.await.map_err(|_| "diálogo fechou sem resposta".to_string())?;
    Ok(escolhido.and_then(|p| p.into_path().ok()).map(|p| p.to_string_lossy().into_owned()))
}

#[tauri::command]
pub async fn pick_folder<R: Runtime>(app: AppHandle<R>) -> Result<Option<String>, String> {
    let mut d = app.dialog().file();
    if let Some(w) = app.get_webview_window(crate::hover::JANELA) {
        d = d.set_parent(&w);
    }
    let (tx, rx) = tokio::sync::oneshot::channel();
    d.pick_folder(move |p| {
        let _ = tx.send(p);
    });
    let escolhido = rx.await.map_err(|_| "diálogo fechou sem resposta".to_string())?;
    Ok(escolhido.and_then(|p| p.into_path().ok()).map(|p| p.to_string_lossy().into_owned()))
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn caminho_copiado_vai_entre_aspas_duplas() {
        assert_eq!(entre_aspas(r"C:\Users\G A\Reco\2026-11-11 reco.mp3"), r#""C:\Users\G A\Reco\2026-11-11 reco.mp3""#);
        assert_eq!(entre_aspas("nota a.md"), "\"nota a.md\"");
    }

    #[test]
    fn so_abre_o_que_e_do_reco() {
        for ok in ["a_reco.mp3", "a.TXT", "n.md", "v.mkv", "x.resumo.md", "c.wav"] {
            assert!(abrivel(Path::new(ok)).is_ok(), "{ok}");
        }
        for ruim in ["calc.exe", "x.bat", "y.lnk", "z.cmd", "w.ps1", "v.vbs", "u.scr", "sem_extensao", "a.mp3.exe"] {
            assert!(abrivel(Path::new(ruim)).is_err(), "{ruim}");
        }
        assert!(abrivel(&std::env::temp_dir()).is_ok(), "pasta existente abre");
    }

    #[test]
    fn link_externo_so_http_https() {
        assert!(url_web("https://github.com/dosxnjos/reco/releases").is_ok());
        assert!(url_web("http://example.com").is_ok());
        for ruim in ["file:///C:/Windows/System32/calc.exe", "javascript:alert(1)", "ms-settings:", "", "https://"] {
            assert!(url_web(ruim).is_err(), "{ruim}");
        }
    }
}

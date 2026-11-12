//! Notificações do Windows (plugin notification), como `_balloon_if_hidden` (`reco.py:3999-4003`): com a
//! janela escondida, o status não aparece, então o aviso é o único jeito de saber. A queda do motor gravando
//! (D11) avisa sempre, escondida ou não.

use std::path::Path;

use serde_json::Value;
use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_notification::NotificationExt;

use crate::estado::EstadoCasco;

/// Texto de um aviso em português e em inglês.
#[derive(Debug, PartialEq, Eq)]
pub enum Aviso {
    GravacaoInterrompida,
    ErroDeGravacao { fatal: bool },
    TranscricaoPronta(String),
    NotaCopiada(String),
}

pub fn texto(a: &Aviso, ingles: bool) -> String {
    match (a, ingles) {
        (Aviso::GravacaoInterrompida, false) => "A gravação foi interrompida. Abra o Reco para ver o arquivo.".into(),
        (Aviso::GravacaoInterrompida, true) => "The recording was interrupted. Open Reco to see the file.".into(),
        (Aviso::ErroDeGravacao { fatal: true }, false) => "A gravação parou por um erro.".into(),
        (Aviso::ErroDeGravacao { fatal: true }, true) => "The recording stopped because of an error.".into(),
        (Aviso::ErroDeGravacao { fatal: false }, false) => "Problema numa fonte de áudio; a gravação continua.".into(),
        (Aviso::ErroDeGravacao { fatal: false }, true) => "Problem with an audio source; still recording.".into(),
        (Aviso::TranscricaoPronta(n), false) => format!("Transcrição pronta: {n}"),
        (Aviso::TranscricaoPronta(n), true) => format!("Transcription ready: {n}"),
        (Aviso::NotaCopiada(n), false) => format!("Nota salva — caminho copiado: {n}"),
        (Aviso::NotaCopiada(n), true) => format!("Note saved — path copied: {n}"),
    }
}

/// Aviso a dar depois de uma resposta de `rec.conclude`/`transcribe.file` que deu certo, se houver.
pub fn aviso_da_resposta(cmd: &str, args: &Value, data: &Value) -> Option<Aviso> {
    let nome = |chave: &str| {
        data.get(chave).and_then(Value::as_str).map(|p| {
            Path::new(p).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_else(|| p.to_string())
        })
    };
    match (cmd, args.get("action").and_then(Value::as_str)) {
        ("transcribe.file", _) | ("rec.conclude", Some("transcribe" | "transcribe_delete" | "final_pass")) => {
            nome("txt").map(Aviso::TranscricaoPronta)
        }
        ("rec.conclude", Some("nota")) => nome("md").map(Aviso::NotaCopiada),
        _ => None,
    }
}

fn janela_escondida<R: Runtime>(app: &AppHandle<R>) -> bool {
    app.get_webview_window(crate::hover::JANELA).map(|w| !w.is_visible().unwrap_or(false)).unwrap_or(true)
}

pub fn mostrar<R: Runtime>(app: &AppHandle<R>, aviso: &Aviso) {
    let ingles = app.try_state::<std::sync::Arc<EstadoCasco>>().map(|e| e.ingles()).unwrap_or(false);
    if let Err(e) = app.notification().builder().title("Reco").body(texto(aviso, ingles)).show() {
        ::log::warn!("[reco] notificação falhou: {e}");
    }
}

/// Só com a janela escondida (com ela à vista, a tela já mostra o status).
pub fn se_escondida<R: Runtime>(app: &AppHandle<R>, aviso: &Aviso) {
    if janela_escondida(app) {
        mostrar(app, aviso);
    }
}

#[cfg(test)]
mod testes {
    use super::*;
    use serde_json::json;

    #[test]
    fn aviso_so_para_transcricao_e_nota() {
        let d = json!({"txt": "C:/R/a_reco.txt", "deleted": false});
        assert_eq!(
            aviso_da_resposta("transcribe.file", &json!({"path": "x"}), &d),
            Some(Aviso::TranscricaoPronta("a_reco.txt".into()))
        );
        assert_eq!(
            aviso_da_resposta("rec.conclude", &json!({"action": "nota"}), &json!({"md": "C:/N/nota 1.md"})),
            Some(Aviso::NotaCopiada("nota 1.md".into()))
        );
        assert_eq!(aviso_da_resposta("rec.conclude", &json!({"action": "save"}), &json!({"path": "a"})), None);
        assert_eq!(aviso_da_resposta("library.list", &json!({}), &d), None);
        assert!(texto(&Aviso::GravacaoInterrompida, false).starts_with("A gravação foi interrompida"));
    }
}

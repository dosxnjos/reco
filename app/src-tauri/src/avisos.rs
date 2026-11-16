//! Notificações do Windows (plugin notification), como `_balloon_if_hidden` (`reco.py:3999-4003`): com a
//! janela escondida, o status não aparece, então o aviso é o único jeito de saber. A queda do motor gravando
//! (D11) avisa sempre, escondida ou não.

use std::path::Path;

use serde_json::Value;
use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_notification::NotificationExt;

use crate::estado::{EstadoCasco, Lingua};

/// Texto de um aviso em português, inglês e polonês (polonês nos termos de `i18n_pl.py`: *nagrywanie* é o ato
/// de gravar, *nagranie* o arquivo).
#[derive(Debug, PartialEq, Eq)]
pub enum Aviso {
    GravacaoInterrompida,
    ErroDeGravacao { fatal: bool },
    TranscricaoPronta(String),
    NotaCopiada(String),
    /// Gravar, Pausar ou Continuar pela bandeja falhou (nada grava e a janela pode estar escondida).
    BandejaFalhou { cmd: &'static str },
}

pub fn texto(a: &Aviso, lingua: Lingua) -> String {
    let t = |pt: &str, en: &str, pl: &str| lingua.escolher(pt, en, pl).to_string();
    match a {
        Aviso::GravacaoInterrompida => t(
            "A gravação foi interrompida. Abra o Reco para ver o arquivo.",
            "The recording was interrupted. Open Reco to see the file.",
            "Nagrywanie zostało przerwane. Otwórz Reco, aby zobaczyć plik.",
        ),
        Aviso::ErroDeGravacao { fatal: true } => t(
            "A gravação parou por um erro.",
            "The recording stopped because of an error.",
            "Nagrywanie zatrzymało się z powodu błędu.",
        ),
        Aviso::ErroDeGravacao { fatal: false } => t(
            "Problema numa fonte de áudio; a gravação continua.",
            "Problem with an audio source; still recording.",
            "Problem ze źródłem dźwięku; nagrywanie trwa nadal.",
        ),
        Aviso::TranscricaoPronta(n) => {
            format!("{} {n}", lingua.escolher("Transcrição pronta:", "Transcription ready:", "Transkrypcja gotowa:"))
        }
        Aviso::NotaCopiada(n) => format!(
            "{} {n}",
            lingua.escolher(
                "Nota salva — caminho copiado:",
                "Note saved — path copied:",
                "Zapisano notatkę — skopiowano ścieżkę:"
            )
        ),
        Aviso::BandejaFalhou { cmd: "rec.start" } => t(
            "A gravação não começou. Abra o Reco para ver o motivo.",
            "Recording did not start. Open Reco to see why.",
            "Nagrywanie się nie rozpoczęło. Otwórz Reco, aby zobaczyć przyczynę.",
        ),
        Aviso::BandejaFalhou { .. } => t(
            "Não deu para pausar ou continuar. Abra o Reco para ver o motivo.",
            "Could not pause or resume. Open Reco to see why.",
            "Nie udało się wstrzymać ani wznowić. Otwórz Reco, aby zobaczyć przyczynę.",
        ),
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
    let lingua = app.try_state::<std::sync::Arc<EstadoCasco>>().map(|e| e.lingua()).unwrap_or_default();
    if let Err(e) = app.notification().builder().title("Reco").body(texto(aviso, lingua)).show() {
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
        assert!(texto(&Aviso::GravacaoInterrompida, Lingua::Pt).starts_with("A gravação foi interrompida"));
        assert!(texto(&Aviso::BandejaFalhou { cmd: "rec.start" }, Lingua::Pt).starts_with("A gravação não começou"));
        assert!(texto(&Aviso::BandejaFalhou { cmd: "rec.pause" }, Lingua::En).starts_with("Could not pause"));
    }

    #[test]
    fn textos_pt_e_en_seguem_os_de_antes() {
        let pt = |a: &Aviso| texto(a, Lingua::Pt);
        let en = |a: &Aviso| texto(a, Lingua::En);
        assert_eq!(pt(&Aviso::ErroDeGravacao { fatal: true }), "A gravação parou por um erro.");
        assert_eq!(en(&Aviso::ErroDeGravacao { fatal: false }), "Problem with an audio source; still recording.");
        assert_eq!(pt(&Aviso::TranscricaoPronta("a.txt".into())), "Transcrição pronta: a.txt");
        assert_eq!(en(&Aviso::TranscricaoPronta("a.txt".into())), "Transcription ready: a.txt");
        assert_eq!(pt(&Aviso::NotaCopiada("n.md".into())), "Nota salva — caminho copiado: n.md");
        assert_eq!(en(&Aviso::NotaCopiada("n.md".into())), "Note saved — path copied: n.md");
        assert_eq!(en(&Aviso::BandejaFalhou { cmd: "rec.start" }), "Recording did not start. Open Reco to see why.");
    }

    #[test]
    fn avisos_em_polones() {
        let pl = |a: &Aviso| texto(a, Lingua::Pl);
        assert_eq!(pl(&Aviso::GravacaoInterrompida), "Nagrywanie zostało przerwane. Otwórz Reco, aby zobaczyć plik.");
        assert_eq!(pl(&Aviso::ErroDeGravacao { fatal: true }), "Nagrywanie zatrzymało się z powodu błędu.");
        assert_eq!(pl(&Aviso::ErroDeGravacao { fatal: false }), "Problem ze źródłem dźwięku; nagrywanie trwa nadal.");
        assert_eq!(pl(&Aviso::TranscricaoPronta("a_reco.txt".into())), "Transkrypcja gotowa: a_reco.txt");
        assert_eq!(
            pl(&Aviso::NotaCopiada("nota 1.md".into())),
            "Zapisano notatkę — skopiowano ścieżkę: nota 1.md"
        );
        assert_eq!(
            pl(&Aviso::BandejaFalhou { cmd: "rec.start" }),
            "Nagrywanie się nie rozpoczęło. Otwórz Reco, aby zobaczyć przyczynę."
        );
        for cmd in ["rec.pause", "rec.resume"] {
            assert_eq!(
                pl(&Aviso::BandejaFalhou { cmd }),
                "Nie udało się wstrzymać ani wznowić. Otwórz Reco, aby zobaczyć przyczynę."
            );
        }
    }
}

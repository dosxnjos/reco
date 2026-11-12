//! Quanto o casco espera cada resposta antes de desistir com `timeout` (substitui o `timeout_for` do Lacre).
//! Base: os tetos sugeridos do `docs/PROTOCOL.md`, com as folgas do md da Fase 3 (passo 4).

use std::time::Duration;

use serde_json::Value;

const HORA: u64 = 3600;

/// `rec.stop` segura o Sair (D11): 120 s de folga sobre os 30 s sugeridos (o motor drena o ao vivo).
pub const PRAZO_REC_STOP: Duration = Duration::from_secs(120);

/// Ações de `rec.conclude` que transcrevem (longas, com `progress`).
const CONCLUSOES_LONGAS: &[&str] = &["transcribe", "transcribe_delete", "final_pass", "nota"];

/// Prazo do casco para o comando `cmd` com estes `args`.
pub fn prazo(cmd: &str, args: &Value) -> Duration {
    match cmd {
        "transcribe.file" => Duration::from_secs(12 * HORA),
        "rec.conclude" => {
            let acao = args.get("action").and_then(Value::as_str).unwrap_or("");
            if CONCLUSOES_LONGAS.contains(&acao) {
                Duration::from_secs(12 * HORA)
            } else {
                Duration::from_secs(60)
            }
        }
        "convert.extract_mp3" => Duration::from_secs(2 * HORA),
        "resumo.ia" => Duration::from_secs(960),
        "rec.stop" => PRAZO_REC_STOP,
        // Baixa o modelo novo quando há (reco.py:1230-1266): em 60 s o Router desistiria no meio do download.
        "model.update_check" => Duration::from_secs(2 * HORA),
        _ => Duration::from_secs(60),
    }
}

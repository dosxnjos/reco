//! Duas rotinas do casco que precisam do motor e são testáveis sem Tauri (passo 5 da Fase 3):
//!
//! - **Sair seguro (D11):** com gravação em curso, `rec.stop` e esperar o arquivo fechar antes do `shutdown`.
//!   O MP3 só fica com a duração certa se o container fechar (`CLAUDE.md` § MP3); o app velho faz o mesmo em
//!   `_quit` (`reco.py:5088`). O Lacre só dava `shutdown(8 s)`, que no meio de uma gravação é corte.
//! - **Checagem de versão:** no primeiro `ready` do processo do casco, 1,5 s depois, `model.update_check` e
//!   então `app.update_check` (paridade com `_kick_update_checks`, `reco.py:2940-2949`; F3-D15).

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use serde_json::{json, Value};

use super::prazos::{prazo, PRAZO_REC_STOP};
use super::processo::Engine;

/// Quanto o casco espera o motor sair depois do `shutdown` antes de matar (o motor fecha tudo em menos).
pub const GRACA_SHUTDOWN: Duration = Duration::from_secs(8);
/// Prazo do `state` na saída: curto, porque um motor travado não pode segurar o Sair por 60 s.
const PRAZO_STATE_NA_SAIDA: Duration = Duration::from_secs(5);
/// Atraso das checagens de versão depois do primeiro `ready` (o velho usa 1,5 s depois de abrir).
pub const ATRASO_CHECAGEM: Duration = Duration::from_millis(1500);

/// Estados do motor em que há uma gravação aberta (arquivo crescendo). `starting` entra porque o motor
/// espera o start terminar e fecha o arquivo que nasceu (F2, `_claim_exit`).
pub fn gravando(rec_state: &str) -> bool {
    matches!(rec_state, "recording" | "paused" | "starting")
}

/// O que a saída fez (para log e teste).
#[derive(Debug, PartialEq, Eq)]
pub enum Saida {
    /// Motor já parado: só o `shutdown` (sem ressuscitá-lo para perguntar o estado).
    MotorParado,
    /// Nada gravando: `shutdown` direto.
    Ocioso,
    /// Gravando: `rec.stop` respondeu (ok ou erro) antes do `shutdown`.
    FechouGravacao { ok: bool },
}

/// Sai com segurança: pergunta o `state`; se há gravação aberta, pede `rec.stop` e espera a resposta (até
/// `PRAZO_REC_STOP`); só então `shutdown(graca)`. Bloqueia quem chama: rodar fora da thread principal.
pub async fn sair_com_seguranca(engine: &Arc<Engine>, graca: Duration) -> Saida {
    let resultado = if !engine.status().running {
        Saida::MotorParado
    } else {
        match engine.request(engine.new_id(), "state", json!({}), PRAZO_STATE_NA_SAIDA).await {
            Ok(st) if gravando(st.get("rec_state").and_then(Value::as_str).unwrap_or("")) => {
                ::log::info!("[reco] Sair com gravação aberta: rec.stop antes do shutdown (D11)");
                let r = engine.request(engine.new_id(), "rec.stop", json!({}), PRAZO_REC_STOP).await;
                if let Err(e) = &r {
                    ::log::warn!("[reco] rec.stop na saída falhou: {e}");
                }
                Saida::FechouGravacao { ok: r.is_ok() }
            }
            Ok(_) => Saida::Ocioso,
            Err(e) => {
                // Sem resposta do state, o shutdown ainda fecha o MP3 (o motor trata EOF e shutdown igual).
                ::log::warn!("[reco] state na saída falhou: {e}");
                Saida::Ocioso
            }
        }
    };
    // `shutdown` dorme em laço (até `graca`): quem chama roda isto numa thread própria (`block_on`).
    engine.shutdown(graca);
    resultado
}

/// Porteira do "primeiro `ready` do processo do casco" (não a cada reinício do motor).
#[derive(Default)]
pub struct PrimeiroReady(AtomicBool);

impl PrimeiroReady {
    /// `true` só na primeira vez que vê um `ready` sem `error` (import falhou = nada a checar).
    pub fn passa(&self, ready: &Value) -> bool {
        if ready.get("error").is_some_and(|e| !e.is_null()) {
            return false;
        }
        !self.0.swap(true, Ordering::SeqCst)
    }
}

/// Espera `atraso` e pede `model.update_check` e depois `app.update_check`, nessa ordem. Devolve o
/// `{tag, url}` da versão nova do app, ou `None` (`null`, erro ou `busy`: nada a avisar).
pub async fn checar_versoes(engine: &Arc<Engine>, atraso: Duration) -> Option<Value> {
    tokio::time::sleep(atraso).await;
    let args = json!({});
    if let Err(e) = engine.request(engine.new_id(), "model.update_check", args.clone(), prazo("model.update_check", &args)).await {
        ::log::info!("[reco] model.update_check: {e}");
    }
    match engine.request(engine.new_id(), "app.update_check", args.clone(), prazo("app.update_check", &args)).await {
        Ok(v) if v.get("url").and_then(Value::as_str).is_some() => Some(v),
        Ok(_) => None,
        Err(e) => {
            ::log::info!("[reco] app.update_check: {e}");
            None
        }
    }
}

#[cfg(test)]
mod testes {
    use super::*;
    use crate::motor::testes::falso::{self, Falso};

    #[test]
    fn so_estados_com_arquivo_aberto_contam_como_gravando() {
        for s in ["recording", "paused", "starting"] {
            assert!(gravando(s), "{s}");
        }
        for s in ["idle", "stopping", "stopped", ""] {
            assert!(!gravando(s), "{s}");
        }
    }

    #[test]
    fn primeiro_ready_passa_uma_vez_e_nunca_com_erro() {
        let p = PrimeiroReady::default();
        assert!(!p.passa(&json!({"event": "ready", "error": "ImportError"})));
        assert!(p.passa(&json!({"event": "ready", "import_s": 0.3})));
        assert!(!p.passa(&json!({"event": "ready", "import_s": 0.3})), "reinício do motor não checa de novo");
    }

    /// D11: com `state` respondendo `recording`, o casco pede `rec.stop`, **espera a resposta** e só então
    /// manda `shutdown`. O motor falso anota a chegada de cada pedido e também o momento em que o `rec.stop`
    /// respondeu (`rec.stop:respondido`, 0,3 s depois da chegada): o `shutdown` tem de vir depois dessa linha.
    #[tokio::test]
    #[ignore = "precisa de `python` no PATH"]
    async fn sair_fecha_gravacao() {
        let (engine, _seen, dir) = falso::subir("sair", Falso { rec_state: "recording", ..Default::default() });
        let saida = sair_com_seguranca(&engine, Duration::from_secs(5)).await;
        assert_eq!(saida, Saida::FechouGravacao { ok: true });
        assert_eq!(falso::cmds(&dir), vec!["state", "rec.stop", "rec.stop:respondido", "shutdown"]);
        assert!(!engine.status().running);

        // Controle: ocioso → shutdown direto, sem rec.stop.
        let (engine, _seen, dir2) = falso::subir("sair-ocioso", Falso::default());
        assert_eq!(sair_com_seguranca(&engine, Duration::from_secs(5)).await, Saida::Ocioso);
        assert_eq!(falso::cmds(&dir2), vec!["state", "shutdown"]);
        let _ = std::fs::remove_dir_all(dir);
        let _ = std::fs::remove_dir_all(dir2);
    }

    /// O motor falso emite `ready` ao subir; a porteira deixa passar e o casco pede as duas checagens, nessa
    /// ordem. A resposta `{tag, url}` volta para ser guardada (`versao_nova`).
    #[tokio::test]
    #[ignore = "precisa de `python` no PATH"]
    async fn apos_ready_checa_versao() {
        let update = r#"{"tag":"v9.9.9","url":"https://github.com/dosxnjos/reco/releases/tag/v9.9.9"}"#;
        let (engine, seen, dir) = falso::subir("versao", Falso { ready: true, update, ..Default::default() });
        let porteira = PrimeiroReady::default();
        let mut ready = None;
        for _ in 0..100 {
            ready = seen.lock().unwrap().iter().find(|v| v["event"] == "ready").cloned();
            if ready.is_some() {
                break;
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
        let ready = ready.expect("o motor falso não emitiu ready");
        assert!(porteira.passa(&ready));
        let nova = checar_versoes(&engine, Duration::from_millis(100)).await;
        assert_eq!(nova.unwrap()["tag"], "v9.9.9");
        assert_eq!(falso::cmds(&dir), vec!["model.update_check", "app.update_check"]);
        assert!(!porteira.passa(&ready), "segundo ready não checa de novo");
        engine.shutdown(Duration::from_secs(3));
        let _ = std::fs::remove_dir_all(dir);
    }
}

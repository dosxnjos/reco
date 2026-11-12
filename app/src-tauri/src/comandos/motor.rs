//! Comandos que falam com o motor. Nomes e argumentos são contrato com `ui/src/backend.ts` (passo 11; o Tauri
//! passa os argumentos em camelCase: `requestId`).
//!
//! - `engine_request`/`engine_status`: cópia do Lacre (`commands.rs:16-58`), com `shutdown` reservado ao casco
//!   e o gancho de `pos_resposta` (nota copiada e aviso com a janela escondida, F3-D4).
//! - `parar_gravacao` (F3-D13): `rec.stop` e, se `auto` vier preenchido, `rec.conclude {action: auto}` em
//!   segundo plano; o resultado vai à tela pelo evento `reco-conclusao` (a bandeja para pelo mesmo caminho).

use std::future::Future;
use std::sync::Arc;

use serde::Serialize;
use serde_json::{json, Map, Value};
use tauri::{AppHandle, Emitter, Manager, Runtime, State};

use crate::avisos::{self, Aviso};
use crate::comandos::arquivos::copiar_caminho;
use crate::estado::EstadoCasco;
use crate::motor::prazos::prazo;
use crate::motor::{error_obj, Engine, EngineStatus};

/// Evento do casco com o resultado da conclusão encadeada por `parar_gravacao`.
pub const EVENTO_CONCLUSAO: &str = "reco-conclusao";

/// Comandos que a tela não pode mandar: o ciclo de vida do motor é do casco.
const RESERVADOS: &[&str] = &["shutdown"];

fn err_string(e: &Value) -> String {
    e.to_string()
}

/// Resultado de `rec.conclude {action: auto}`: `{action, ok, data|error}`.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Conclusao {
    pub action: String,
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<Value>,
}

/// Depois de toda resposta que passa pelo Rust: nota → copia `"<md>"` (mesmo escondida, `reco.py:4053`);
/// transcrição ou nota prontas → aviso se a janela está escondida.
pub fn pos_resposta<R: Runtime>(app: &AppHandle<R>, cmd: &str, args: &Value, data: &Value) {
    if cmd == "rec.conclude" && args.get("action").and_then(Value::as_str) == Some("nota") {
        if let Some(md) = data.get("md").and_then(Value::as_str) {
            if let Err(e) = copiar_caminho(app, md) {
                ::log::warn!("[reco] falha ao copiar o caminho da nota: {e}");
            }
        }
    }
    if let Some(aviso) = avisos::aviso_da_resposta(cmd, args, data) {
        avisos::se_escondida(app, &aviso);
    }
}

#[tauri::command]
pub async fn engine_request<R: Runtime>(
    app: AppHandle<R>,
    engine: State<'_, Arc<Engine>>,
    cmd: String,
    args: Option<Value>,
    request_id: Option<String>,
) -> Result<Value, String> {
    if cmd.is_empty() || RESERVADOS.contains(&cmd.as_str()) {
        return Err(err_string(&error_obj("internal", &format!("command not allowed: {cmd}"))));
    }
    let args = match args {
        None | Some(Value::Null) => Value::Object(Map::new()),
        Some(v @ Value::Object(_)) => v,
        Some(_) => return Err(err_string(&error_obj("bad_args", "args must be an object"))),
    };
    let id = match request_id {
        Some(id) if !id.trim().is_empty() => id,
        _ => engine.new_id(),
    };
    let timeout = prazo(&cmd, &args);
    let engine = Arc::clone(&engine);
    let r = engine.request(id, &cmd, args.clone(), timeout).await;
    if let Ok(data) = &r {
        pos_resposta(&app, &cmd, &args, data);
    }
    r.map_err(|e| err_string(&e))
}

#[tauri::command]
pub fn engine_status(engine: State<'_, Arc<Engine>>) -> EngineStatus {
    engine.status()
}

/// `rec.stop`; se a resposta traz `auto` (`final_pass` ou `nota`), devolve também a conclusão a rodar em
/// seguida (o `rec.conclude` já foi **escrito** no motor quando esta função volta, então a ordem é garantida).
/// Testável sem Tauri: quem chama decide onde esperar a conclusão.
pub async fn parar_encadeando(
    engine: &Arc<Engine>,
) -> Result<(Value, Option<impl Future<Output = Conclusao> + Send + 'static>), Value> {
    let parou = engine.request(engine.new_id(), "rec.stop", json!({}), prazo("rec.stop", &json!({}))).await?;
    let Some(auto) = parou.get("auto").and_then(Value::as_str).map(str::to_string) else {
        return Ok((parou, None));
    };
    let args = json!({ "action": auto });
    let id = engine.new_id();
    let enviado = engine.send(&id, "rec.conclude", args.clone());
    let e = Arc::clone(engine);
    let conclusao = async move {
        let r = match enviado {
            Ok(rx) => e.wait(&id, rx, prazo("rec.conclude", &args)).await,
            Err(err) => Err(err),
        };
        match r {
            Ok(data) => Conclusao { action: auto, ok: true, data: Some(data), error: None },
            Err(err) => Conclusao { action: auto, ok: false, data: None, error: Some(err) },
        }
    };
    Ok((parou, Some(conclusao)))
}

/// Para pela tela ou pela bandeja: a resposta do `rec.stop` volta logo; a conclusão segue em segundo plano,
/// passa por `pos_resposta` e vai à tela pelo evento `reco-conclusao`.
pub async fn parar<R: Runtime>(app: &AppHandle<R>) -> Result<Value, Value> {
    let engine = Arc::clone(app.state::<Arc<Engine>>().inner());
    let (parou, conclusao) = parar_encadeando(&engine).await?;
    if let Some(fut) = conclusao {
        let app = app.clone();
        tauri::async_runtime::spawn(async move {
            let c = fut.await;
            if let Some(data) = c.data.as_ref() {
                pos_resposta(&app, "rec.conclude", &json!({ "action": c.action }), data);
            } else {
                // O mp3 fica no disco (F2-D12); a tela mostra o erro pelo evento abaixo.
                ::log::warn!("[reco] conclusão automática falhou: {:?}", c.error);
            }
            if let Err(e) = app.emit(EVENTO_CONCLUSAO, &c) {
                ::log::warn!("[reco] emit {EVENTO_CONCLUSAO}: {e}");
            }
        });
    }
    Ok(parou)
}

#[tauri::command]
pub async fn parar_gravacao<R: Runtime>(app: AppHandle<R>) -> Result<Value, String> {
    parar(&app).await.map_err(|e| err_string(&e))
}

/// `{tag, url}` guardado pela checagem do primeiro `ready` (passo 5), ou `null`.
#[tauri::command]
pub fn versao_nova(estado: State<'_, Arc<EstadoCasco>>) -> Option<Value> {
    estado.versao_nova()
}

/// Aviso usado quando o motor cai gravando (D11): sempre, escondida ou não.
pub fn avisar_gravacao_interrompida<R: Runtime>(app: &AppHandle<R>) {
    avisos::mostrar(app, &Aviso::GravacaoInterrompida);
}

#[cfg(test)]
mod testes {
    use super::*;
    use crate::motor::testes::falso::{self, Falso};
    use std::time::Duration;

    /// `rec.stop` com `auto: "nota"` → o casco pede `rec.conclude {action: nota}` em seguida e a conclusão
    /// volta com o `md` (é dele que o Rust copia o caminho entre aspas).
    #[tokio::test]
    #[ignore = "precisa de `python` no PATH"]
    async fn parar_encadeia_auto() {
        let (engine, _seen, dir) = falso::subir("parar", Falso { rec_state: "recording", auto: "nota", ..Default::default() });
        let (parou, conclusao) = parar_encadeando(&engine).await.expect("rec.stop");
        assert_eq!(parou["auto"], "nota");
        let c = conclusao.expect("auto preenchido tem de encadear").await;
        assert_eq!(c, Conclusao { action: "nota".into(), ok: true, data: Some(json!({"md": "C:/falso/nota a.md"})), error: None });
        let pedidos = falso::pedidos(&dir);
        let cmds: Vec<&str> = pedidos.iter().map(|(c, _)| c.as_str()).collect();
        assert_eq!(cmds, vec!["rec.stop", "rec.stop:respondido", "rec.conclude"]);
        assert_eq!(pedidos[2].1, json!({"action": "nota"}));
        engine.shutdown(Duration::from_secs(3));

        // Controle: auto nulo → nada encadeado.
        let (engine, _seen, dir2) = falso::subir("parar-nulo", Falso { rec_state: "recording", ..Default::default() });
        let (parou, conclusao) = parar_encadeando(&engine).await.expect("rec.stop");
        assert!(parou["auto"].is_null() && conclusao.is_none());
        assert_eq!(falso::cmds(&dir2), vec!["rec.stop", "rec.stop:respondido"]);
        engine.shutdown(Duration::from_secs(3));
        let _ = std::fs::remove_dir_all(dir);
        let _ = std::fs::remove_dir_all(dir2);
    }

    #[test]
    fn conclusao_serializa_como_o_contrato() {
        let c = Conclusao { action: "final_pass".into(), ok: false, data: None, error: Some(json!({"code": "busy"})) };
        assert_eq!(serde_json::to_value(&c).unwrap(), json!({"action": "final_pass", "ok": false, "error": {"code": "busy"}}));
    }
}

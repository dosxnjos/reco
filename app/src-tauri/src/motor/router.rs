//! Router: casa cada linha de resposta do stdout com o pedido pendente pelo `id` e reconhece eventos.
//! Molde: Lacre `src-tauri/src/engine.rs:47-131` (cópia, comentários traduzidos).

use std::collections::HashMap;
use std::sync::{Mutex, MutexGuard};

use serde_json::{json, Value};
use tokio::sync::oneshot;

/// Resultado de um pedido: `Ok(data)` ou `Err(objeto de erro {code, detail})`.
pub type Outcome = Result<Value, Value>;

/// Monta um objeto de erro com um código do PROTOCOL.md (ou do casco: `timeout`) e um detalhe técnico curto.
pub fn error_obj(code: &str, detail: &str) -> Value {
    json!({ "code": code, "detail": detail })
}

/// Um pânico com uma destas travas na mão não pode derrubar a ponte inteira.
pub(crate) fn lock<T>(m: &Mutex<T>) -> MutexGuard<'_, T> {
    m.lock().unwrap_or_else(|poisoned| poisoned.into_inner())
}

/// O que uma linha do stdout acabou sendo.
#[derive(Debug, PartialEq)]
pub enum Routed {
    /// Resposta entregue ao pedido pendente com este id.
    Delivered(String),
    /// Resposta cujo id ninguém espera (atrasada, cancelada ou que estourou o prazo).
    Unmatched(String),
    /// Linha de evento (tem a chave `"event"`); leva a linha JSON inteira.
    Event(Value),
    /// Vazia, não JSON, ou não é objeto do protocolo.
    Invalid,
}

/// Pedidos pendentes por id; cada um espera num canal oneshot.
#[derive(Default)]
pub struct Router {
    pending: Mutex<HashMap<String, oneshot::Sender<Outcome>>>,
}

impl Router {
    /// Registra um pedido pendente. Falha se o id já está esperando.
    pub fn register(&self, id: &str) -> Result<oneshot::Receiver<Outcome>, String> {
        let mut pending = lock(&self.pending);
        if pending.contains_key(id) {
            return Err(format!("duplicate request id {id}"));
        }
        let (tx, rx) = oneshot::channel();
        pending.insert(id.to_string(), tx);
        Ok(rx)
    }

    /// Esquece um pedido (prazo estourado, falha de escrita). O receptor não recebe mais nada.
    pub fn forget(&self, id: &str) {
        lock(&self.pending).remove(id);
    }

    pub fn pending_count(&self) -> usize {
        lock(&self.pending).len()
    }

    /// Classifica uma linha do stdout e a entrega se for resposta.
    pub fn route_line(&self, line: &str) -> Routed {
        let line = line.trim();
        if line.is_empty() {
            return Routed::Invalid;
        }
        let Ok(value) = serde_json::from_str::<Value>(line) else {
            return Routed::Invalid;
        };
        let Some(obj) = value.as_object() else {
            return Routed::Invalid;
        };
        // O PROTOCOL.md manda testar `event` antes de `id` (progress leva o id do pedido).
        if obj.contains_key("event") {
            return Routed::Event(value);
        }
        let Some(id) = obj.get("id").and_then(Value::as_str).map(str::to_string) else {
            return Routed::Invalid;
        };
        let outcome = if obj.get("ok").and_then(Value::as_bool) == Some(true) {
            Ok(obj.get("data").cloned().unwrap_or(Value::Null))
        } else {
            let err = obj.get("error").cloned().filter(|e| e.get("code").is_some());
            Err(err.unwrap_or_else(|| error_obj("internal", "malformed engine response")))
        };
        match lock(&self.pending).remove(&id) {
            Some(tx) => {
                // O receptor pode já ter ido embora (quem pediu desistiu); não é erro aqui.
                let _ = tx.send(outcome);
                Routed::Delivered(id)
            }
            None => Routed::Unmatched(id),
        }
    }

    /// Falha todos os pedidos pendentes com o mesmo erro (motor morreu ou está encerrando).
    pub fn fail_all(&self, error: &Value) {
        let drained: Vec<_> = lock(&self.pending).drain().collect();
        for (_, tx) in drained {
            let _ = tx.send(Err(error.clone()));
        }
    }
}

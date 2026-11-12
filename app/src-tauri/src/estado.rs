//! Estado que o casco guarda a partir dos eventos do motor e as reações a eles, em funções puras (sem Tauri).
//! O `lib.rs` executa as ações; assim a regra do D11 ("motor caiu gravando → alarme, nunca 'gravando'") e a
//! porteira do primeiro `ready` têm teste sem abrir janela.

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Mutex;

use serde_json::Value;

use crate::motor::router::lock;
use crate::motor::saida::{gravando, PrimeiroReady};

/// O que o casco faz em resposta a um evento ou a uma troca de status do motor.
#[derive(Debug, PartialEq, Eq)]
pub enum Acao {
    /// Redesenhar a bandeja (ícone, menu e dica) com o estado guardado.
    Bandeja,
    /// Primeiro `ready` do processo: checagens de versão (1,5 s depois) e leitura das preferências do casco.
    PrimeiroReady,
    /// D11: o motor caiu com gravação aberta. Notificar (mesmo escondida) e avisar a tela.
    GravacaoInterrompida,
    /// `rec.error` do motor: notificar se a janela está escondida. Leva o canal e se foi fatal.
    ErroDeGravacao { canal: String, fatal: bool },
}

pub struct EstadoCasco {
    rec_state: Mutex<String>,
    segundos: AtomicU64,
    /// Durante o Sair, a queda do motor é esperada: nada de alarme.
    saindo: AtomicBool,
    ingles: AtomicBool,
    versao_nova: Mutex<Option<Value>>,
    primeiro_ready: PrimeiroReady,
}

impl Default for EstadoCasco {
    fn default() -> Self {
        EstadoCasco {
            rec_state: Mutex::new("idle".into()),
            segundos: AtomicU64::new(0),
            saindo: AtomicBool::new(false),
            ingles: AtomicBool::new(false),
            versao_nova: Mutex::new(None),
            primeiro_ready: PrimeiroReady::default(),
        }
    }
}

fn segundos_de(ev: &Value) -> u64 {
    ev.get("elapsed_s").and_then(Value::as_f64).map(|s| s.max(0.0) as u64).unwrap_or(0)
}

impl EstadoCasco {
    pub fn rec_state(&self) -> String {
        lock(&self.rec_state).clone()
    }

    pub fn segundos(&self) -> u64 {
        self.segundos.load(Ordering::SeqCst)
    }

    pub fn ingles(&self) -> bool {
        self.ingles.load(Ordering::SeqCst)
    }

    /// Idioma efetivo informado pela interface (`definir_lingua`): `"en"` vale inglês, o resto português.
    pub fn definir_lingua(&self, lingua: &str) {
        self.ingles.store(lingua == "en", Ordering::SeqCst);
    }

    pub fn marcar_saindo(&self) -> bool {
        self.saindo.swap(true, Ordering::SeqCst)
    }

    pub fn saindo(&self) -> bool {
        self.saindo.load(Ordering::SeqCst)
    }

    pub fn guardar_versao_nova(&self, v: Option<Value>) {
        *lock(&self.versao_nova) = v;
    }

    pub fn versao_nova(&self) -> Option<Value> {
        lock(&self.versao_nova).clone()
    }

    /// Reação a uma linha de evento do motor (o JSON inteiro, com `event`).
    pub fn no_evento(&self, ev: &Value) -> Vec<Acao> {
        match ev.get("event").and_then(Value::as_str).unwrap_or("") {
            "state" => {
                let novo = ev.get("state").and_then(Value::as_str).unwrap_or("idle").to_string();
                *lock(&self.rec_state) = novo;
                self.segundos.store(segundos_de(ev), Ordering::SeqCst);
                vec![Acao::Bandeja]
            }
            "timer" => {
                self.segundos.store(segundos_de(ev), Ordering::SeqCst);
                vec![Acao::Bandeja]
            }
            "ready" if self.primeiro_ready.passa(ev) => vec![Acao::PrimeiroReady],
            "rec.error" => vec![Acao::ErroDeGravacao {
                canal: ev.get("channel").and_then(Value::as_str).unwrap_or("").to_string(),
                fatal: ev.get("fatal").and_then(Value::as_bool).unwrap_or(false),
            }],
            _ => vec![],
        }
    }

    /// Reação ao `engine-status`. Motor caído: o estado guardado volta a `idle` (o motor novo nasce ocioso e
    /// o reinício nunca religa a gravação, D11); se havia gravação aberta e não é o Sair, alarme.
    pub fn no_status(&self, running: bool) -> Vec<Acao> {
        if running {
            return vec![];
        }
        let antes = std::mem::replace(&mut *lock(&self.rec_state), "idle".into());
        self.segundos.store(0, Ordering::SeqCst);
        if self.saindo() || antes == "idle" {
            return vec![];
        }
        if gravando(&antes) {
            vec![Acao::Bandeja, Acao::GravacaoInterrompida]
        } else {
            vec![Acao::Bandeja]
        }
    }
}

#[cfg(test)]
mod testes {
    use super::*;
    use serde_json::json;

    #[test]
    fn motor_caido_gravando_dispara_alarme_e_zera_o_estado() {
        let e = EstadoCasco::default();
        e.no_evento(&json!({"event": "state", "state": "recording", "elapsed_s": 12.4}));
        e.no_evento(&json!({"event": "timer", "elapsed_s": 13}));
        assert_eq!(e.segundos(), 13);
        assert_eq!(e.no_status(false), vec![Acao::Bandeja, Acao::GravacaoInterrompida]);
        assert_eq!(e.rec_state(), "idle", "nunca continuar dizendo gravando");
        assert_eq!(e.no_status(false), vec![], "segunda queda sem gravação não alarma");

        e.no_evento(&json!({"event": "state", "state": "paused", "elapsed_s": 3}));
        assert_eq!(e.no_status(false), vec![Acao::Bandeja, Acao::GravacaoInterrompida], "pausado também");
    }

    #[test]
    fn queda_no_sair_ou_parado_nao_alarma() {
        let e = EstadoCasco::default();
        e.no_evento(&json!({"event": "state", "state": "stopped", "elapsed_s": 5}));
        assert_eq!(e.no_status(false), vec![Acao::Bandeja]);
        e.no_evento(&json!({"event": "state", "state": "recording", "elapsed_s": 1}));
        assert!(!e.marcar_saindo());
        assert_eq!(e.no_status(false), vec![]);
        assert_eq!(e.no_status(true), vec![]);
    }

    #[test]
    fn primeiro_ready_uma_vez_e_erros_repassados() {
        let e = EstadoCasco::default();
        assert_eq!(e.no_evento(&json!({"event": "ready", "error": "x"})), vec![]);
        assert_eq!(e.no_evento(&json!({"event": "ready", "import_s": 0.4})), vec![Acao::PrimeiroReady]);
        assert_eq!(e.no_evento(&json!({"event": "ready", "import_s": 0.4})), vec![]);
        assert_eq!(
            e.no_evento(&json!({"event": "rec.error", "channel": "save", "detail": "x", "fatal": true})),
            vec![Acao::ErroDeGravacao { canal: "save".into(), fatal: true }]
        );
        assert_eq!(e.no_evento(&json!({"event": "level", "mic": 0.1, "sys": null})), vec![]);
    }
}

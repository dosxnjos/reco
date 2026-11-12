//! Ponte com o motor Python: processo filho de longa duração falando JSON Lines em stdin/stdout
//! (contrato: `docs/PROTOCOL.md`). Cópia do `engine.rs` do Lacre dividida em arquivos (F3-D1).
//!
//! - `router`: casa resposta e pedido pelo `id`, reconhece evento.
//! - `processo`: sobe, lê, reinicia com backoff e encerra o filho (`Engine`).
//! - `log`: drena o stderr para `engine.log` (rotação de 2 MB).
//! - `prazos`: quanto o casco espera cada comando.
//! - `saida`: Sair seguro (D11) e checagem de versão depois do primeiro `ready`.

pub mod log;
pub mod prazos;
pub mod processo;
pub mod router;
pub mod saida;

#[cfg(test)]
pub(crate) mod testes;

pub use processo::{bundled_exe_name, Engine, EngineStatus, EventSink, Launch, Mode, Signal};
pub use router::{error_obj, Outcome};

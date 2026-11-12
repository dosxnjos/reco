//! Log do motor: o stderr dele (onde vai todo `print` e o log do Python) é drenado sempre e anexado a
//! `engine.log`, com rotação simples em 2 MB. Molde: Lacre `engine.rs:542-591`.

use std::io::{BufRead, BufReader, Read, Write};
use std::path::PathBuf;
use std::sync::OnceLock;

/// Onde o stderr do motor é anexado. O app define uma vez na partida; nos testes fica vazio.
pub static ENGINE_LOG: OnceLock<PathBuf> = OnceLock::new();
const ENGINE_LOG_MAX_BYTES: u64 = 2 * 1024 * 1024;

fn open_engine_log() -> Option<std::fs::File> {
    let path = ENGINE_LOG.get()?;
    if let Some(dir) = path.parent() {
        let _ = std::fs::create_dir_all(dir);
    }
    // Log pequeno: passou do teto, recomeça (a rodada anterior fica como .old).
    if std::fs::metadata(path).map(|m| m.len() > ENGINE_LOG_MAX_BYTES).unwrap_or(false) {
        let _ = std::fs::rename(path, path.with_extension("log.old"));
    }
    std::fs::OpenOptions::new().create(true).append(true).open(path).ok()
}

/// Lê o stderr do motor até o fim. Precisa rodar sempre: com o pipe cheio o motor trava.
pub(crate) fn drain_stderr(stderr: impl Read) {
    let mut reader = BufReader::new(stderr);
    let mut buf = Vec::new();
    let mut log = open_engine_log();
    if let Some(f) = log.as_mut() {
        let secs = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let _ = writeln!(f, "---- motor iniciado (unix {secs}) ----");
    }
    loop {
        buf.clear();
        match reader.read_until(b'\n', &mut buf) {
            Ok(0) | Err(_) => break,
            Ok(_) => {
                if cfg!(debug_assertions) {
                    eprint!("[motor] {}", String::from_utf8_lossy(&buf));
                }
                if let Some(f) = log.as_mut() {
                    let _ = f.write_all(&buf);
                }
            }
        }
    }
}

/// Corta em `max` caracteres respeitando a fronteira de caractere (UTF-8).
pub(crate) fn truncate(s: &str, max: usize) -> &str {
    match s.char_indices().nth(max) {
        Some((i, _)) => &s[..i],
        None => s,
    }
}

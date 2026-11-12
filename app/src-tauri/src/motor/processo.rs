//! O processo filho do motor: subir, escrever pedidos, ler o stdout numa thread, drenar o stderr,
//! reiniciar com backoff quando ele morre e mandar `shutdown` na saída.
//! Molde: Lacre `engine.rs:137-523` (Launch, processo, geração, backoff e shutdown).
//!
//! Nada aqui depende do Tauri: o casco pluga um `EventSink` que emite eventos do Tauri, e os testes plugam
//! uma closure que grava o que passou. O reinício **nunca** religa uma gravação (D11): o motor novo nasce
//! ocioso e a interface ressincroniza com `state`.

use std::ffi::OsString;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use serde::Serialize;
use serde_json::{json, Value};
use tokio::sync::oneshot;

use super::log::{drain_stderr, truncate};
use super::router::{error_obj, lock, Outcome, Routed, Router};

/// Versão do protocolo escrita em todo pedido.
pub const PROTOCOL_VERSION: u64 = 1;

/// Id do `shutdown` que o casco manda na saída (a resposta não tem quem espere).
const SHUTDOWN_ID: &str = "casco-shutdown";

/// Como o motor roda: do fonte (`python -m reco_engine`, "dev") ou congelado pelo PyInstaller ("bundled").
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    Dev,
    Bundled,
}

#[derive(Clone, Debug)]
pub struct Launch {
    pub program: OsString,
    pub args: Vec<OsString>,
    pub cwd: Option<PathBuf>,
    pub mode: Mode,
}

impl Launch {
    /// `python -m reco_engine` com diretório de trabalho `engine/` (como o teste da Fase 2 sobe o motor).
    pub fn dev(engine_dir: PathBuf) -> Self {
        Launch {
            program: "python".into(),
            args: vec!["-m".into(), "reco_engine".into()],
            cwd: Some(engine_dir),
            mode: Mode::Dev,
        }
    }

    /// O executável congelado (`engine/reco-engine(.exe)` nos recursos do app).
    pub fn bundled(exe: PathBuf) -> Self {
        let cwd = exe.parent().map(PathBuf::from);
        Launch { program: exe.into_os_string(), args: vec![], cwd, mode: Mode::Bundled }
    }

    /// Comando com as variáveis e a flag que o PROTOCOL.md pede (`CREATE_NO_WINDOW`: o exe é `console=True`).
    pub fn command(&self) -> Command {
        let mut cmd = Command::new(&self.program);
        cmd.args(&self.args)
            .env("PYTHONUNBUFFERED", "1")
            .env("PYTHONIOENCODING", "utf-8")
            .env("PYTHONUTF8", "1");
        if let Some(cwd) = &self.cwd {
            cmd.current_dir(cwd);
        }
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }
        cmd
    }
}

/// Nome do motor congelado dentro da pasta de recurso `engine/`.
pub fn bundled_exe_name() -> &'static str {
    if cfg!(windows) {
        "reco-engine.exe"
    } else {
        "reco-engine"
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct EngineStatus {
    pub running: bool,
    pub mode: Mode,
}

/// O que a ponte empurra para o casco.
#[derive(Debug)]
pub enum Signal {
    /// Uma linha de evento do protocolo, repassada como veio (evento do Tauri `engine-event`).
    Event(Value),
    /// O motor subiu ou caiu (evento do Tauri `engine-status`).
    Status(EngineStatus),
}

pub type EventSink = Arc<dyn Fn(Signal) + Send + Sync>;

/// Reinício: no máximo isto de tentativas dentro da janela, com backoff exponencial.
const RESTART_MAX: usize = 5;
const RESTART_WINDOW: Duration = Duration::from_secs(60);
const RESTART_BASE_DELAY: Duration = Duration::from_millis(300);
const RESTART_MAX_DELAY: Duration = Duration::from_secs(5);

#[derive(Default)]
struct Proc {
    stdin: Option<ChildStdin>,
    child: Option<Child>,
    /// Sobe a cada partida, para uma thread leitora velha não atropelar um processo novo.
    generation: u64,
}

pub struct Engine {
    launch: Launch,
    sink: EventSink,
    pub(crate) router: Router,
    proc: Mutex<Proc>,
    running: AtomicBool,
    shutting_down: AtomicBool,
    restarting: AtomicBool,
    restart_log: Mutex<Vec<Instant>>,
    next_id: AtomicU64,
}

impl Engine {
    pub fn new(launch: Launch, sink: EventSink) -> Arc<Self> {
        Arc::new(Engine {
            launch,
            sink,
            router: Router::default(),
            proc: Mutex::new(Proc::default()),
            running: AtomicBool::new(false),
            shutting_down: AtomicBool::new(false),
            restarting: AtomicBool::new(false),
            restart_log: Mutex::new(Vec::new()),
            next_id: AtomicU64::new(1),
        })
    }

    pub fn status(&self) -> EngineStatus {
        EngineStatus { running: self.running.load(Ordering::SeqCst), mode: self.launch.mode }
    }

    fn emit_status(&self) {
        (self.sink)(Signal::Status(self.status()));
    }

    /// Sobe o motor; se falhar, tenta de novo em segundo plano com backoff.
    pub fn start_or_retry(self: &Arc<Self>) {
        if let Err(e) = self.start() {
            ::log::warn!("[reco] motor não subiu: {e}");
            self.schedule_restart();
        }
    }

    /// Sobe o processo do motor se ele não está rodando. Idempotente.
    pub fn start(self: &Arc<Self>) -> std::io::Result<()> {
        if self.shutting_down.load(Ordering::SeqCst) {
            return Err(std::io::Error::other("encerrando"));
        }
        let mut proc = lock(&self.proc);
        if proc.stdin.is_some() {
            return Ok(());
        }
        let mut cmd = self.launch.command();
        cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        let mut child = cmd.spawn()?;
        let stdin = child.stdin.take();
        let stdout = child.stdout.take();
        let stderr = child.stderr.take();
        proc.generation += 1;
        let generation = proc.generation;
        proc.stdin = stdin;
        proc.child = Some(child);
        self.running.store(true, Ordering::SeqCst);
        drop(proc);

        if let Some(stderr) = stderr {
            // Tem de ser drenado, senão o motor trava quando o buffer do pipe enche.
            std::thread::Builder::new()
                .name("reco-motor-stderr".into())
                .spawn(move || drain_stderr(stderr))?;
        }
        if let Some(stdout) = stdout {
            let me = Arc::clone(self);
            std::thread::Builder::new().name("reco-motor-stdout".into()).spawn(move || {
                me.read_stdout(stdout);
                me.on_exit(generation);
            })?;
        }
        ::log::info!("[reco] motor subiu ({:?})", self.launch.mode);
        self.emit_status();
        Ok(())
    }

    fn read_stdout(&self, stdout: impl Read) {
        let mut reader = BufReader::new(stdout);
        let mut buf = Vec::with_capacity(64 * 1024);
        loop {
            buf.clear();
            match reader.read_until(b'\n', &mut buf) {
                Ok(0) => break,
                Ok(_) => {
                    self.handle_line(&String::from_utf8_lossy(&buf));
                }
                Err(e) => {
                    ::log::warn!("[reco] erro lendo o stdout do motor: {e}");
                    break;
                }
            }
        }
    }

    /// Encaminha uma linha do stdout: resposta a quem espera, evento ao casco.
    pub fn handle_line(&self, line: &str) -> Routed {
        let routed = self.router.route_line(line);
        match &routed {
            Routed::Event(v) => (self.sink)(Signal::Event(v.clone())),
            Routed::Unmatched(id) if id != SHUTDOWN_ID => {
                ::log::warn!("[reco] resposta do motor para id desconhecido {id}")
            }
            Routed::Invalid if !line.trim().is_empty() => ::log::warn!(
                "[reco] ignorando saída do motor fora do protocolo: {}",
                truncate(line.trim(), 200)
            ),
            _ => {}
        }
        routed
    }

    /// Chamado pela thread do stdout no EOF: recolhe o filho, falha os pendentes, talvez reinicie.
    fn on_exit(self: &Arc<Self>, generation: u64) {
        let child = {
            let mut proc = lock(&self.proc);
            if proc.generation != generation {
                return;
            }
            proc.stdin = None;
            proc.child.take()
        };
        if let Some(mut child) = child {
            match child.wait() {
                Ok(status) => ::log::info!("[reco] motor saiu: {status}"),
                Err(e) => ::log::warn!("[reco] falha esperando o motor: {e}"),
            }
        }
        self.running.store(false, Ordering::SeqCst);
        let shutting_down = self.shutting_down.load(Ordering::SeqCst);
        let detail = if shutting_down { "engine_shutdown" } else { "engine_exited" };
        self.router.fail_all(&error_obj("internal", detail));
        self.emit_status();
        if !shutting_down {
            self.schedule_restart();
        }
    }

    /// Reinício em segundo plano com backoff exponencial, até `RESTART_MAX` tentativas por janela.
    fn schedule_restart(self: &Arc<Self>) {
        if self.restarting.swap(true, Ordering::SeqCst) {
            return;
        }
        let me = Arc::clone(self);
        let spawned = std::thread::Builder::new().name("reco-motor-reinicio".into()).spawn(move || {
            loop {
                let Some(delay) = me.next_restart_delay() else {
                    ::log::warn!("[reco] o motor continua caindo; desisto até o próximo pedido");
                    break;
                };
                std::thread::sleep(delay);
                if me.shutting_down.load(Ordering::SeqCst) {
                    break;
                }
                match me.start() {
                    Ok(()) => break,
                    Err(e) => ::log::warn!("[reco] reinício do motor falhou: {e}"),
                }
            }
            me.restarting.store(false, Ordering::SeqCst);
        });
        if spawned.is_err() {
            self.restarting.store(false, Ordering::SeqCst);
        }
    }

    /// Próximo atraso do backoff, ou `None` quando o orçamento da janela acabou.
    fn next_restart_delay(&self) -> Option<Duration> {
        let mut log = lock(&self.restart_log);
        let now = Instant::now();
        log.retain(|t| now.duration_since(*t) < RESTART_WINDOW);
        if log.len() >= RESTART_MAX {
            return None;
        }
        log.push(now);
        let exp = u32::try_from(log.len() - 1).unwrap_or(u32::MAX).min(8);
        Some((RESTART_BASE_DELAY * 2u32.pow(exp)).min(RESTART_MAX_DELAY))
    }

    fn write_line(&self, line: &str) -> Result<(), Value> {
        let mut proc = lock(&self.proc);
        let Some(stdin) = proc.stdin.as_mut() else {
            return Err(error_obj("internal", "engine_not_running"));
        };
        let res = stdin
            .write_all(line.as_bytes())
            .and_then(|_| stdin.write_all(b"\n"))
            .and_then(|_| stdin.flush());
        res.map_err(|e| error_obj("internal", &format!("engine_write_failed: {e}")))
    }

    /// Gera um id novo de pedido.
    pub fn new_id(&self) -> String {
        format!("casco-{}", self.next_id.fetch_add(1, Ordering::SeqCst))
    }

    /// Escreve o pedido já (na ordem da chamada) e devolve o receptor da resposta. Junto com `wait`, deixa
    /// mandar dois pedidos em sequência garantida sem esperar a resposta do primeiro.
    pub fn send(self: &Arc<Self>, id: &str, cmd: &str, args: Value) -> Result<oneshot::Receiver<Outcome>, Value> {
        if !self.running.load(Ordering::SeqCst) && !self.restarting.load(Ordering::SeqCst) {
            // O orçamento de reinício pode ter acabado antes; um pedido novo é uma chance nova.
            if let Err(e) = self.start() {
                return Err(error_obj("internal", &format!("engine_not_running: {e}")));
            }
        }
        let rx = self.router.register(id).map_err(|e| error_obj("internal", &e))?;
        let line = json!({ "v": PROTOCOL_VERSION, "id": id, "cmd": cmd, "args": args }).to_string();
        if let Err(e) = self.write_line(&line) {
            self.router.forget(id);
            return Err(e);
        }
        Ok(rx)
    }

    /// Espera a resposta de um pedido mandado por `send`, até `timeout`.
    pub async fn wait(&self, id: &str, rx: oneshot::Receiver<Outcome>, timeout: Duration) -> Outcome {
        match tokio::time::timeout(timeout, rx).await {
            Ok(Ok(outcome)) => outcome,
            Ok(Err(_)) => Err(error_obj("internal", "engine_dropped_request")),
            Err(_) => {
                self.router.forget(id);
                Err(error_obj("timeout", "shell_timeout"))
            }
        }
    }

    /// Manda um pedido e espera a resposta. Nunca segura trava através do await: pedido longo
    /// (transcrição) não bloqueia os outros.
    pub async fn request(self: &Arc<Self>, id: String, cmd: &str, args: Value, timeout: Duration) -> Outcome {
        let rx = self.send(&id, cmd, args)?;
        self.wait(&id, rx, timeout).await
    }

    /// Pede ao motor que saia (`shutdown`), espera até `grace` e então mata. Sem reinício depois.
    /// Gravação em curso: use antes `saida::sair_com_seguranca` (D11), que pede `rec.stop` primeiro.
    pub fn shutdown(&self, grace: Duration) {
        self.shutting_down.store(true, Ordering::SeqCst);
        let line = json!({ "v": PROTOCOL_VERSION, "id": SHUTDOWN_ID, "cmd": "shutdown", "args": {} }).to_string();
        let _ = self.write_line(&line);
        let child = {
            let mut proc = lock(&self.proc);
            proc.stdin = None; // fechar o stdin é um segundo "por favor, saia" (EOF, D11)
            proc.child.take()
        };
        if let Some(mut child) = child {
            let deadline = Instant::now() + grace;
            loop {
                match child.try_wait() {
                    Ok(Some(_)) => break,
                    Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(50)),
                    _ => {
                        ::log::warn!("[reco] motor não saiu em {grace:?}: matando");
                        let _ = child.kill();
                        let _ = child.wait();
                        break;
                    }
                }
            }
        }
        self.running.store(false, Ordering::SeqCst);
        self.router.fail_all(&error_obj("internal", "engine_shutdown"));
    }
}

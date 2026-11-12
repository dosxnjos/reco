//! Testes da ponte (molde: Lacre `engine.rs:597-871`) e o motor falso em Python que os testes dos passos 5 e 6
//! também usam (`falso::subir`). Os ignorados precisam de `python` no PATH: `cargo test -- --ignored`.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use serde_json::{json, Value};

use super::log::truncate;
use super::prazos::prazo;
use super::processo::{Engine, EventSink, Launch, Mode, Signal};
use super::router::{error_obj, Routed, Router};

pub(crate) fn recording_sink() -> (EventSink, Arc<Mutex<Vec<Value>>>) {
    let seen = Arc::new(Mutex::new(Vec::new()));
    let seen2 = Arc::clone(&seen);
    let sink: EventSink = Arc::new(move |s| {
        if let Signal::Event(v) = s {
            seen2.lock().unwrap().push(v);
        }
    });
    (sink, seen)
}

/// Motor falso: responde o protocolo do Reco o bastante para os testes do casco e anota cada `cmd` recebido
/// (uma linha por pedido, na ordem de chegada) no arquivo de log que recebe por argumento.
pub(crate) mod falso {
    use super::*;

    const SCRIPT: &str = r#"
import json, os, sys, threading, time
log_path, rec_state, auto, ready, update = sys.argv[1:6]
lock = threading.Lock()
n_state = [0]
def out(o):
    with lock:
        sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()
def anota(cmd, args):
    with lock:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"cmd": cmd, "args": args}) + "\n")
def ok(i, data): out({"v":1,"id":i,"ok":True,"data":data})
def handle(req):
    i, cmd, args = req["id"], req["cmd"], req.get("args") or {}
    anota(cmd, args)
    if cmd == "hello": ok(i, {"engine_version":"0.0.0","protocol":1,"ready":True})
    elif cmd == "state":
        st = rec_state
        if rec_state == "stopping":   # o rec.stop em curso termina: stopped a partir do 4º state
            n_state[0] += 1
            st = "stopping" if n_state[0] < 4 else "stopped"
        ok(i, {"ready":True,"rec_state":st,"elapsed_s":3,"transcribing":False,"live":False,"last_rec":None,"auto":None})
    elif cmd == "rec.stop":
        time.sleep(0.3)
        anota("rec.stop:respondido", {})
        ok(i, {"path":"C:/falso/a_reco.mp3","duration_s":5.0,"auto":None if auto == "-" else auto})
    elif cmd == "rec.conclude":
        a = args.get("action")
        data = {"nota":{"md":"C:/falso/nota a.md"},"save":{"path":"C:/falso/a_reco.mp3"},
                "final_pass":{"txt":"C:/falso/a_reco.txt","text":"oi"}}.get(a, {})
        ok(i, data)
    elif cmd == "model.update_check":
        time.sleep(0.5); ok(i, {})
    elif cmd == "app.update_check": ok(i, json.loads(update))
    elif cmd == "slow":
        out({"v":1,"id":i,"event":"progress","pct":None,"text":"x"}); time.sleep(1.0); ok(i, {"slow":True})
    elif cmd == "boom": out({"v":1,"id":i,"ok":False,"error":{"code":"no_device","detail":"none"}})
    elif cmd == "die": sys.stdout.flush(); os._exit(3)
if ready == "1":
    out({"v":1,"event":"ready","import_s":0.1,"has":{},"lang":"pt","reco_version":None})
for line in sys.stdin:
    req = json.loads(line)
    if req["cmd"] == "shutdown":
        anota("shutdown", {}); ok(req["id"], {}); break
    threading.Thread(target=handle, args=(req,)).start()
"#;

    /// Opções do motor falso.
    pub(crate) struct Falso {
        pub rec_state: &'static str,
        /// `"-"` = `auto: null`.
        pub auto: &'static str,
        pub ready: bool,
        /// JSON da resposta de `app.update_check`.
        pub update: &'static str,
    }

    impl Default for Falso {
        fn default() -> Self {
            Falso { rec_state: "idle", auto: "-", ready: false, update: "null" }
        }
    }

    /// Sobe o motor falso numa pasta temporária própria. Devolve o motor, o que o sink viu e a pasta.
    pub(crate) fn subir(nome: &str, f: Falso) -> (Arc<Engine>, Arc<Mutex<Vec<Value>>>, PathBuf) {
        let dir = std::env::temp_dir().join(format!("reco-falso-{nome}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let script = dir.join("motor_falso.py");
        std::fs::write(&script, SCRIPT).unwrap();
        let log = dir.join("pedidos.jsonl");
        let launch = Launch {
            program: "python".into(),
            args: vec![
                "-u".into(),
                script.into_os_string(),
                log.into_os_string(),
                f.rec_state.into(),
                f.auto.into(),
                (if f.ready { "1" } else { "0" }).into(),
                f.update.into(),
            ],
            cwd: Some(dir.clone()),
            mode: Mode::Dev,
        };
        let (sink, seen) = recording_sink();
        let engine = Engine::new(launch, sink);
        engine.start().unwrap();
        (engine, seen, dir)
    }

    /// Os pedidos que o motor falso recebeu, na ordem: `(cmd, args)`.
    pub(crate) fn pedidos(dir: &std::path::Path) -> Vec<(String, Value)> {
        std::fs::read_to_string(dir.join("pedidos.jsonl"))
            .unwrap_or_default()
            .lines()
            .filter_map(|l| serde_json::from_str::<Value>(l).ok())
            .map(|v| (v["cmd"].as_str().unwrap_or("").to_string(), v["args"].clone()))
            .collect()
    }

    pub(crate) fn cmds(dir: &std::path::Path) -> Vec<String> {
        pedidos(dir).into_iter().map(|(c, _)| c).collect()
    }
}

#[test]
fn response_goes_to_matching_id_only() {
    let r = Router::default();
    let mut a = r.register("a").unwrap();
    let mut b = r.register("b").unwrap();
    let routed = r.route_line(r#"{"v":1,"id":"b","ok":true,"data":{"x":2}}"#);
    assert_eq!(routed, Routed::Delivered("b".into()));
    assert_eq!(b.try_recv().unwrap(), Ok(json!({"x": 2})));
    assert!(a.try_recv().is_err(), "a ainda tem de estar esperando");
    assert_eq!(r.pending_count(), 1);
    r.route_line("{\"v\":1,\"id\":\"a\",\"ok\":true,\"data\":[1,2]}\r\n");
    assert_eq!(a.try_recv().unwrap(), Ok(json!([1, 2])));
    assert_eq!(r.pending_count(), 0);
}

#[test]
fn error_response_carries_error_object() {
    let r = Router::default();
    let mut rx = r.register("e").unwrap();
    r.route_line(r#"{"v":1,"id":"e","ok":false,"error":{"code":"busy","detail":"x"}}"#);
    assert_eq!(rx.try_recv().unwrap(), Err(json!({"code":"busy","detail":"x"})));
    let mut rx = r.register("m").unwrap();
    r.route_line(r#"{"v":1,"id":"m","ok":false}"#);
    assert_eq!(rx.try_recv().unwrap().unwrap_err()["code"], "internal");
}

#[test]
fn ok_without_data_is_null() {
    let r = Router::default();
    let mut rx = r.register("s").unwrap();
    r.route_line(r#"{"v":1,"id":"s","ok":true}"#);
    assert_eq!(rx.try_recv().unwrap(), Ok(Value::Null));
}

#[test]
fn unknown_id_is_unmatched_and_harmless() {
    let r = Router::default();
    let mut rx = r.register("a").unwrap();
    assert_eq!(r.route_line(r#"{"v":1,"id":"zzz","ok":true,"data":{}}"#), Routed::Unmatched("zzz".into()));
    assert!(rx.try_recv().is_err());
    assert_eq!(r.pending_count(), 1);
}

#[test]
fn duplicate_id_is_rejected() {
    let r = Router::default();
    let _rx = r.register("dup").unwrap();
    assert!(r.register("dup").is_err());
}

#[test]
fn event_lines_are_not_responses() {
    let r = Router::default();
    let mut rx = r.register("tr-1").unwrap();
    let line = r#"{"v":1,"id":"tr-1","event":"progress","pct":42,"text":"Transcrevendo… 42%"}"#;
    match r.route_line(line) {
        Routed::Event(v) => assert_eq!(v, serde_json::from_str::<Value>(line).unwrap()),
        other => panic!("esperava evento, veio {other:?}"),
    }
    assert!(rx.try_recv().is_err(), "evento não pode resolver o pedido");
}

#[test]
fn invalid_lines_are_ignored() {
    let r = Router::default();
    for line in ["", "   ", "not json", "[1,2]", "42", r#"{"v":1,"ok":true}"#] {
        assert_eq!(r.route_line(line), Routed::Invalid, "linha: {line:?}");
    }
}

#[test]
fn fail_all_resolves_every_pending_request() {
    let r = Router::default();
    let mut a = r.register("a").unwrap();
    let mut b = r.register("b").unwrap();
    r.fail_all(&error_obj("internal", "engine_exited"));
    for rx in [&mut a, &mut b] {
        assert_eq!(rx.try_recv().unwrap().unwrap_err()["detail"], "engine_exited");
    }
    assert_eq!(r.pending_count(), 0);
}

#[test]
fn engine_forwards_events_to_sink_without_process() {
    let (sink, seen) = recording_sink();
    let engine = Engine::new(Launch::bundled(PathBuf::from("nao-existe")), sink);
    let mut rx = engine.router.register("t-1").unwrap();
    let ev = r#"{"v":1,"id":"t-1","event":"progress","pct":null,"text":"Carregando áudio…"}"#;
    engine.handle_line(ev);
    engine.handle_line("lixo");
    engine.handle_line(r#"{"v":1,"id":"t-1","ok":true,"data":{"txt":"a.txt"}}"#);
    assert_eq!(*seen.lock().unwrap(), vec![serde_json::from_str::<Value>(ev).unwrap()]);
    assert_eq!(rx.try_recv().unwrap(), Ok(json!({"txt": "a.txt"})));
}

#[test]
fn prazos_seguem_o_protocolo() {
    let h = |n: u64| Duration::from_secs(n * 3600);
    assert_eq!(prazo("transcribe.file", &json!({"path": "a"})), h(12));
    assert_eq!(prazo("convert.extract_mp3", &json!({})), h(2));
    assert_eq!(prazo("model.update_check", &json!({})), h(2));
    assert_eq!(prazo("resumo.ia", &json!({})), Duration::from_secs(960));
    assert_eq!(prazo("rec.stop", &json!({})), Duration::from_secs(120));
    assert_eq!(prazo("hello", &json!({})), Duration::from_secs(60));
    assert_eq!(prazo("library.list", &json!({})), Duration::from_secs(60));
}

#[test]
fn prazo_de_rec_conclude_depende_da_acao() {
    for longa in ["transcribe", "transcribe_delete", "final_pass", "nota"] {
        assert_eq!(prazo("rec.conclude", &json!({"action": longa})), Duration::from_secs(12 * 3600), "{longa}");
    }
    for curta in ["save", "delete"] {
        assert_eq!(prazo("rec.conclude", &json!({"action": curta})), Duration::from_secs(60), "{curta}");
    }
    assert_eq!(prazo("rec.conclude", &json!({})), Duration::from_secs(60));
}

#[test]
fn launch_dev_roda_o_modulo_do_motor() {
    let l = Launch::dev(PathBuf::from("engine"));
    assert_eq!(l.program, "python");
    assert_eq!(l.args, vec!["-m", "reco_engine"]);
    assert_eq!(l.cwd, Some(PathBuf::from("engine")));
    assert_eq!(super::processo::bundled_exe_name(), "reco-engine.exe");
}

#[test]
fn truncate_respects_char_boundaries() {
    assert_eq!(truncate("ação", 2), "aç");
    assert_eq!(truncate("ab", 5), "ab");
}

/// O caminho real de debug (`python -m reco_engine` em `engine/`): `hello` e `shutdown`.
/// Rodar com `cargo test -- --ignored motor_real_hello`. Não grava nem mexe em config (só `hello`).
#[tokio::test]
#[ignore = "precisa de python com as dependências do motor"]
async fn motor_real_hello() {
    let engine_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..").join("engine");
    let (sink, _seen) = recording_sink();
    let engine = Engine::new(Launch::dev(engine_dir), sink);
    engine.start().unwrap();
    let hello = engine.request(engine.new_id(), "hello", json!({}), Duration::from_secs(120)).await.expect("hello");
    assert!(hello.get("engine_version").is_some(), "{hello}");
    engine.shutdown(Duration::from_secs(8));
    assert!(!engine.status().running);
}

/// Ponta a ponta contra o motor falso (python no PATH). Rodar com `cargo test -- --ignored fake_engine`.
#[tokio::test]
#[ignore = "precisa de `python` no PATH"]
async fn fake_engine_end_to_end() {
    let (engine, seen, dir) = falso::subir("e2e", falso::Falso::default());
    let t = Duration::from_secs(10);
    let hello = engine.request(engine.new_id(), "hello", json!({}), t).await.unwrap();
    assert_eq!(hello["engine_version"], "0.0.0");

    // Pedido lento não bloqueia o rápido: o hello resolve com o slow ainda pendente.
    let e2 = Arc::clone(&engine);
    let slow = tokio::spawn(async move { e2.request("s1".into(), "slow", json!({}), t).await });
    tokio::time::sleep(Duration::from_millis(100)).await;
    engine.request(engine.new_id(), "hello", json!({}), t).await.unwrap();
    assert!(!slow.is_finished(), "o hello esperou o slow");
    assert_eq!(slow.await.unwrap().unwrap(), json!({"slow": true}));
    assert_eq!(seen.lock().unwrap()[0]["event"], "progress");

    let err = engine.request(engine.new_id(), "boom", json!({}), t).await.unwrap_err();
    assert_eq!(err["code"], "no_device");

    // A morte do motor falha o pedido pendente; depois ele volta sozinho.
    let err = engine.request(engine.new_id(), "die", json!({}), t).await.unwrap_err();
    assert_eq!(err["detail"], "engine_exited");
    let mut ok = false;
    for _ in 0..50 {
        tokio::time::sleep(Duration::from_millis(100)).await;
        if engine.status().running {
            ok = engine.request(engine.new_id(), "hello", json!({}), t).await.is_ok();
            break;
        }
    }
    assert!(ok, "o motor não voltou depois de morrer");

    let err = engine.request(engine.new_id(), "desconhecido", json!({}), Duration::from_millis(300)).await.unwrap_err();
    assert_eq!(err["code"], "timeout");

    engine.shutdown(Duration::from_secs(3));
    assert!(!engine.status().running);
    let _ = std::fs::remove_dir_all(dir);
}

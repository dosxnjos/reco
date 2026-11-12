//! Casco do Reco (Fase 3): sobe o motor Python, liga comandos e eventos à interface, cuida da bandeja, do
//! hover sem foco, da instância única e da saída segura (D11). Molde: Lacre `src-tauri/src/lib.rs`.

pub mod atalho;
pub mod avisos;
pub mod bandeja;
pub mod comandos;
pub mod estado;
pub mod hover;
pub mod instancia;
pub mod motor;

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use serde_json::json;
use tauri::path::BaseDirectory;
use tauri::tray::{MouseButton, MouseButtonState, TrayIcon, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, RunEvent, Runtime, WindowEvent, Wry};

use estado::{Acao, EstadoCasco};
use motor::saida::{self, ATRASO_CHECAGEM, GRACA_SHUTDOWN};
use motor::{Engine, EventSink, Launch, Signal};

/// Evento do Tauri com cada linha de evento do protocolo (payload = a linha JSON como o motor mandou).
pub const ENGINE_EVENT: &str = "engine-event";
/// Evento do Tauri quando o motor sobe ou cai (payload = `{running, mode}`).
pub const ENGINE_STATUS_EVENT: &str = "engine-status";
/// Versão nova do app achada depois do primeiro `ready` (`{tag, url}`); a tela também lê por `versao_nova`.
pub const EVENTO_VERSAO_NOVA: &str = "reco-versao-nova";
/// D11: o motor caiu com gravação aberta (a tela mostra o aviso com "Abrir pasta").
pub const EVENTO_GRAVACAO_INTERROMPIDA: &str = "reco-gravacao-interrompida";

/// Liberado só quando a saída segura terminou: aí o `ExitRequested` seguinte passa.
static PODE_SAIR: AtomicBool = AtomicBool::new(false);

/// Como rodar o motor:
/// 1. debug: `RECO_ENGINE=<reco-engine.exe>` roda o congelado (testar o PyInstaller sem instalador);
/// 2. debug: `python -m reco_engine` em `engine/` do repo;
/// 3. release: o recurso `engine/reco-engine.exe` (sem desvio).
fn resolve_launch<R: Runtime>(app: &AppHandle<R>) -> Launch {
    if cfg!(debug_assertions) {
        if let Some(path) = std::env::var_os("RECO_ENGINE").filter(|p| !p.is_empty()) {
            return Launch::bundled(PathBuf::from(path));
        }
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..").join("engine");
        return Launch::dev(dir);
    }
    let rel = format!("engine/{}", motor::bundled_exe_name());
    let exe = app.path().resolve(&rel, BaseDirectory::Resource).unwrap_or_else(|_| PathBuf::from(&rel));
    Launch::bundled(exe)
}

fn engine_de<R: Runtime>(app: &AppHandle<R>) -> Option<Arc<Engine>> {
    app.try_state::<Arc<Engine>>().map(|e| Arc::clone(e.inner()))
}

/// Executa o que o estado decidiu para um evento ou troca de status do motor.
fn executar<R: Runtime>(app: &AppHandle<R>, est: &Arc<EstadoCasco>, acoes: Vec<Acao>) {
    for a in acoes {
        match a {
            Acao::Bandeja => bandeja::atualizar(app, est),
            Acao::GravacaoInterrompida => {
                comandos::motor::avisar_gravacao_interrompida(app);
                let _ = app.emit(EVENTO_GRAVACAO_INTERROMPIDA, ());
            }
            Acao::ErroDeGravacao { fatal, .. } => avisos::se_escondida(app, &avisos::Aviso::ErroDeGravacao { fatal }),
            Acao::PrimeiroReady => {
                let (app, est) = (app.clone(), Arc::clone(est));
                tauri::async_runtime::spawn(async move {
                    let Some(engine) = engine_de(&app) else { return };
                    atalho::aplicar_preferencia(&app, &engine).await;
                    let nova = saida::checar_versoes(&engine, ATRASO_CHECAGEM).await;
                    if let Some(v) = &nova {
                        let _ = app.emit(EVENTO_VERSAO_NOVA, v);
                    }
                    est.guardar_versao_nova(nova);
                });
            }
        }
    }
}

fn criar_sink<R: Runtime>(app: &AppHandle<R>, est: Arc<EstadoCasco>) -> EventSink {
    let app = app.clone();
    Arc::new(move |signal| {
        let (res, acoes) = match signal {
            Signal::Event(payload) => {
                let acoes = est.no_evento(&payload);
                (app.emit(ENGINE_EVENT, payload), acoes)
            }
            Signal::Status(status) => {
                let acoes = est.no_status(status.running);
                (app.emit(ENGINE_STATUS_EVENT, status), acoes)
            }
        };
        if let Err(e) = res {
            ::log::warn!("[reco] emit falhou: {e}");
        }
        executar(&app, &est, acoes);
    })
}

/// Sair (menu da bandeja ou pedido de saída): em segundo plano, `rec.stop` se gravando e só então o
/// `shutdown` (D11); depois libera o `ExitRequested`. Nunca bloqueia a thread principal.
pub fn iniciar_saida<R: Runtime>(app: &AppHandle<R>) {
    let Some(est) = app.try_state::<Arc<EstadoCasco>>() else { return };
    if est.marcar_saindo() {
        return; // já saindo
    }
    let app = app.clone();
    let r = std::thread::Builder::new().name("reco-saida".into()).spawn(move || {
        if let Some(engine) = engine_de(&app) {
            let s = tauri::async_runtime::block_on(saida::sair_com_seguranca(&engine, GRACA_SHUTDOWN));
            ::log::info!("[reco] saída: {s:?}");
        }
        PODE_SAIR.store(true, Ordering::SeqCst);
        app.exit(0);
    });
    if r.is_err() {
        PODE_SAIR.store(true, Ordering::SeqCst);
    }
}

fn no_menu<R: Runtime>(app: &AppHandle<R>, id: &str) {
    let Some(est) = app.try_state::<Arc<EstadoCasco>>() else { return };
    let estado = est.rec_state();
    match id {
        bandeja::ID_GRAVAR if matches!(estado.as_str(), "recording" | "paused") => {
            // Parar mostra a janela fixada com as saídas (`_tray_toggle_rec`, `reco.py:4954-4963`).
            hover::mostrar_fixada(app);
            let app = app.clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = comandos::motor::parar(&app).await {
                    ::log::warn!("[reco] parar pela bandeja: {e}");
                }
            });
        }
        bandeja::ID_GRAVAR if estado == "idle" => pedir(app, "rec.start", json!({ "mode": "rec" })),
        bandeja::ID_PAUSAR if estado == "recording" => pedir(app, "rec.pause", json!({})),
        bandeja::ID_PAUSAR if estado == "paused" => pedir(app, "rec.resume", json!({})),
        bandeja::ID_ABRIR => hover::mostrar_fixada(app),
        bandeja::ID_SAIR => iniciar_saida(app),
        _ => {}
    }
}

/// Pedido ao motor em segundo plano (o resultado chega à tela pelos eventos `state`/`rec.error`). Falhou (sem
/// dispositivo, ocupado, motor fora): aviso com a janela escondida, como o `rec.error` (nada grava sem ninguém saber).
fn pedir<R: Runtime>(app: &AppHandle<R>, cmd: &'static str, args: serde_json::Value) {
    let Some(engine) = engine_de(app) else { return };
    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        let t = motor::prazos::prazo(cmd, &args);
        if let Err(e) = engine.request(engine.new_id(), cmd, args, t).await {
            ::log::warn!("[reco] {cmd} pela bandeja: {e}");
            avisos::se_escondida(&app, &avisos::Aviso::BandejaFalhou { cmd });
        }
    });
}

fn no_icone<R: Runtime>(tray: &TrayIcon<R>, ev: TrayIconEvent) {
    let app = tray.app_handle();
    match ev {
        TrayIconEvent::Enter { rect, .. } | TrayIconEvent::Move { rect, .. } => hover::no_enter(app, &rect),
        TrayIconEvent::Leave { rect, .. } => hover::guardar_rect_do_evento(app, &rect),
        TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, rect, .. } => {
            hover::guardar_rect_do_evento(app, &rect);
            hover::mostrar_fixada(app);
        }
        _ => {}
    }
}

pub fn run() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if let Some(repasse) = instancia::repasse_cli(&args) {
        std::process::exit(instancia::rodar_repasse(&repasse));
    }
    #[cfg(windows)]
    let Some(_mutex) = instancia::garantir_unica() else {
        return; // outro Reco já aberto: foi avisado para aparecer (exit 0)
    };
    let oculto = args.iter().any(|a| a == "--oculto");

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::new().level(::log::LevelFilter::Info).build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().with_handler(atalho::no_atalho).build())
        // Registrado, nunca ligado aqui: só o comando `definir_autostart`, a partir de Opções.
        .plugin(tauri_plugin_autostart::Builder::new().app_name("Reco Novo").arg("--oculto").build())
        .manage(Arc::new(EstadoCasco::default()))
        .manage(hover::HoverEstado::default())
        .manage(bandeja::BandejaEstado::<Wry>::default())
        .setup(move |app| {
            let handle = app.handle().clone();
            if let Ok(dir) = app.path().app_log_dir() {
                let _ = motor::log::ENGINE_LOG.set(dir.join("engine.log"));
            }
            let est = Arc::clone(app.state::<Arc<EstadoCasco>>().inner());
            let engine = Engine::new(resolve_launch(&handle), criar_sink(&handle, est));
            app.manage(Arc::clone(&engine)); // antes do start: o primeiro `ready` já acha o motor no estado
            engine.start_or_retry();
            bandeja::criar(&handle, no_menu, no_icone)?;
            #[cfg(windows)]
            {
                let h = handle.clone();
                instancia::escutar_show(move || {
                    let h2 = h.clone();
                    let _ = h.run_on_main_thread(move || hover::mostrar_fixada(&h2));
                });
            }
            if !oculto {
                hover::mostrar_fixada(&handle);
            }
            ::log::info!("[reco] casco pronto (oculto={oculto})");
            Ok(())
        })
        .on_window_event(|window, event| {
            // Fechar (X ou Alt+F4) esconde na bandeja; a gravação segue (Guarita `lib.rs:471-479`).
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                hover::esconder(window.app_handle());
            }
        })
        .invoke_handler(tauri::generate_handler![
            comandos::motor::engine_request,
            comandos::motor::engine_status,
            comandos::motor::parar_gravacao,
            comandos::motor::versao_nova,
            comandos::arquivos::copy_path,
            comandos::arquivos::open_path,
            comandos::arquivos::reveal_path,
            comandos::arquivos::open_external,
            comandos::arquivos::pick_file,
            comandos::arquivos::pick_folder,
            comandos::janela::window_hide,
            comandos::janela::window_minimize,
            comandos::janela::window_pin,
            comandos::janela::definir_lingua,
            atalho::definir_atalho,
            atalho::atalho_registrado,
            atalho::autostart_ligado,
            atalho::definir_autostart,
        ])
        .build(tauri::generate_context!())
        .expect("erro ao montar o Reco");

    app.run(|handle, event| match event {
        // O Lacre só trata `Exit`; aqui o pedido de saída espera a gravação fechar (D11).
        RunEvent::ExitRequested { api, .. } if !PODE_SAIR.load(Ordering::SeqCst) => {
            api.prevent_exit();
            iniciar_saida(handle);
        }
        RunEvent::Exit => {
            // Rede de segurança: se algo pulou a saída segura, ainda assim `shutdown` (fecha o MP3 no motor).
            if let Some(engine) = engine_de(handle) {
                if engine.status().running {
                    engine.shutdown(GRACA_SHUTDOWN);
                }
            }
        }
        _ => {}
    });
}

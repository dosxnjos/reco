//! Atalho global e iniciar com o Windows, os dois opt-in em Opções (passo 10, F3-D6).
//!
//! - Atalho: Ctrl+Shift+R, desligado até o Gabriel ligar (paridade com o `.lnk` opt-in, `reco.py:4866-4912`).
//!   Só mostra a janela com foco (a tela recebe `reco-atalho` e foca o botão principal). Falha ao registrar não
//!   derruba nada: volta o código `hotkey_taken`. A preferência é `casco_atalho` no config, gravada pelo motor
//!   (`config.set`, prefixo `casco_`, F2-D16): o Rust só lê (D6).
//! - Iniciar com o Windows: plugin autostart com `app_name("Reco")` e `--oculto` (no `lib.rs`); o estado
//!   é lido do próprio Windows (`is_enabled`), sem gravar em lugar nenhum.

use std::sync::Arc;

use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Runtime, State};
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutEvent, ShortcutState};

use crate::motor::prazos::prazo;
use crate::motor::{error_obj, Engine};

pub const EVENTO_ATALHO: &str = "reco-atalho";
pub const CHAVE_PREF: &str = "casco_atalho";

pub fn atalho_padrao() -> Shortcut {
    Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyR)
}

/// Só registra com a preferência explicitamente `true`; ausente, `null`, `false` ou outro tipo → não.
pub fn deve_registrar(pref_atalho: Option<&Value>) -> bool {
    matches!(pref_atalho, Some(Value::Bool(true)))
}

/// `casco_atalho` dentro da resposta de `config.get`/`config.set` (`{config: {...}, ...}`, PROTOCOL.md).
pub fn pref_do_config(data: &Value) -> Option<&Value> {
    data.get("config")?.get(CHAVE_PREF)
}

/// Handler do plugin: tecla apertada → mostra fixada e avisa a tela.
pub fn no_atalho<R: Runtime>(app: &AppHandle<R>, _s: &Shortcut, ev: ShortcutEvent) {
    if ev.state() == ShortcutState::Pressed {
        crate::hover::mostrar_fixada(app);
        let _ = app.emit(EVENTO_ATALHO, ());
    }
}

fn registrar<R: Runtime>(app: &AppHandle<R>, ligar: bool) -> Result<(), Value> {
    let gs = app.global_shortcut();
    let s = atalho_padrao();
    if !ligar {
        let _ = gs.unregister(s);
        return Ok(());
    }
    if gs.is_registered(s) {
        return Ok(());
    }
    gs.register(s).map_err(|e| error_obj("hotkey_taken", &e.to_string()))
}

/// Na partida (primeiro `ready`): lê a preferência pelo motor e registra se for `true`.
pub async fn aplicar_preferencia<R: Runtime>(app: &AppHandle<R>, engine: &Arc<Engine>) {
    let args = json!({});
    match engine.request(engine.new_id(), "config.get", args.clone(), prazo("config.get", &args)).await {
        Ok(data) if deve_registrar(pref_do_config(&data)) => {
            if let Err(e) = registrar(app, true) {
                ::log::warn!("[reco] atalho não registrado: {e}");
            }
        }
        Ok(_) => {}
        Err(e) => ::log::warn!("[reco] config.get para o atalho falhou: {e}"),
    }
}

/// Liga ou desliga o atalho e grava a preferência pelo motor. Ligar que falha (`hotkey_taken`) não grava.
#[tauri::command]
pub async fn definir_atalho<R: Runtime>(
    app: AppHandle<R>,
    engine: State<'_, Arc<Engine>>,
    ligar: bool,
) -> Result<bool, String> {
    registrar(&app, ligar).map_err(|e| e.to_string())?;
    let args = json!({ "changes": { CHAVE_PREF: ligar } });
    let engine = Arc::clone(&engine);
    let r = engine.request(engine.new_id(), "config.set", args.clone(), prazo("config.set", &args)).await;
    if let Err(e) = r {
        let _ = registrar(&app, !ligar); // não deixar o registro diferente do que ficou gravado
        return Err(e.to_string());
    }
    Ok(app.global_shortcut().is_registered(atalho_padrao()))
}

/// O atalho está registrado agora? (Opções mostra `hotkey_taken` se a preferência é `true` e isto é `false`.)
#[tauri::command]
pub fn atalho_registrado<R: Runtime>(app: AppHandle<R>) -> bool {
    app.global_shortcut().is_registered(atalho_padrao())
}

#[tauri::command]
pub fn autostart_ligado<R: Runtime>(app: AppHandle<R>) -> Result<bool, String> {
    app.autolaunch().is_enabled().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn definir_autostart<R: Runtime>(app: AppHandle<R>, ligar: bool) -> Result<bool, String> {
    let al = app.autolaunch();
    let r = if ligar { al.enable() } else { al.disable() };
    r.map_err(|e| e.to_string())?;
    al.is_enabled().map_err(|e| e.to_string())
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn so_registra_com_true_explicito() {
        assert!(deve_registrar(Some(&json!(true))));
        for nao in [json!(false), json!(null), json!("true"), json!(1)] {
            assert!(!deve_registrar(Some(&nao)), "{nao}");
        }
        assert!(!deve_registrar(None), "ausente não registra");
    }

    #[test]
    fn le_casco_atalho_da_resposta_do_config_get() {
        let ligado = json!({"config": {"casco_atalho": true, "mic_gain": 1.0}, "output_dir_efetivo": "C:/R", "lang_efetivo": "pt"});
        assert!(deve_registrar(pref_do_config(&ligado)));
        let ausente = json!({"config": {"mic_gain": 1.0}, "lang_efetivo": "pt"});
        assert!(!deve_registrar(pref_do_config(&ausente)));
        let desligado = json!({"config": {"casco_atalho": false}});
        assert!(!deve_registrar(pref_do_config(&desligado)));
        // A chave no nível de cima (fora de `config`) não vale: o contrato é `data.config.casco_atalho`.
        assert!(!deve_registrar(pref_do_config(&json!({"casco_atalho": true}))));
    }

    #[test]
    fn atalho_padrao_e_ctrl_shift_r() {
        assert_eq!(atalho_padrao(), Shortcut::new(Some(Modifiers::SHIFT | Modifiers::CONTROL), Code::KeyR));
    }
}

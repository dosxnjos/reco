//! Comandos da janela: esconder na bandeja (o X), minimizar, fixar (todo clique dentro da tela, como `_pin`)
//! e o idioma efetivo que a interface informa (a bandeja e os avisos falam a mesma língua da tela).

use std::sync::Arc;

use tauri::{AppHandle, Manager, Runtime, State};

use crate::estado::EstadoCasco;

/// X da barra própria: esconde na bandeja; a gravação segue (`reco.py:5079-5086`).
#[tauri::command]
pub fn window_hide<R: Runtime>(app: AppHandle<R>) {
    crate::hover::esconder(&app);
}

#[tauri::command]
pub fn window_minimize<R: Runtime>(app: AppHandle<R>) -> Result<(), String> {
    let w = app.get_webview_window(crate::hover::JANELA).ok_or("sem janela")?;
    w.minimize().map_err(|e| e.to_string())
}

/// Fixa a janela aberta pelo hover (ela para de sumir quando o cursor sai).
#[tauri::command]
pub fn window_pin<R: Runtime>(app: AppHandle<R>) {
    crate::hover::fixar(&app);
}

/// Idioma efetivo da interface (`pt` ou `en`): redesenha a bandeja na mesma língua. Assíncrono para rodar fora
/// da thread principal (os setters da bandeja esperam por ela).
#[tauri::command]
pub async fn definir_lingua<R: Runtime>(
    app: AppHandle<R>,
    estado: State<'_, Arc<EstadoCasco>>,
    lingua: String,
) -> Result<(), String> {
    estado.definir_lingua(&lingua);
    crate::bandeja::atualizar(&app, &estado);
    Ok(())
}

//! Hover no ícone mostra a janela sem tirar o foco; clique fixa (passo 9). Mecanismo provado na Fase 0 (D2,
//! modo `tao`): a janela nasce com `focus: false` e `focusable: false` (tauri.conf.json), o hover faz só
//! `show()`, e o clique que fixa faz `set_focusable(true)` + `set_focus()`. Código-base: o spike
//! `temp/spike-bandeja/src-tauri/src/main.rs`, que passou no `hover.py`.
//!
//! Pegadinhas da Fase 0 respeitadas aqui: ancorar pelo rect do ícone (o `TrayBottomCenter` do positioner põe
//! a janela em cima da barra); esconder por polling iniciado no `Enter` (o `Leave` nem sempre chega); não
//! confiar no evento `Focused` no modo `tao` (por isso a tela fixa pelo comando `window_pin`).

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use tauri::{AppHandle, Manager, PhysicalPosition, Runtime, WebviewWindow};

use crate::motor::router::lock;

pub const JANELA: &str = "main";
/// Carência antes de vigiar: o cursor precisa de um instante para ir do ícone à janela (`reco.py:5016`).
const CARENCIA: Duration = Duration::from_millis(500);
const PASSO: Duration = Duration::from_millis(120);
const BORDA_JANELA: i32 = 6;
const BORDA_ICONE: i32 = 4;

/// Retângulo `(esquerda, topo, direita, baixo)` em pixels físicos.
pub type Rect = (i32, i32, i32, i32);

/// Zona quente = janela ±6 px ∪ ícone ±4 px (`reco.py:5024-5045`). Cursor parado sobre o ícone conta como
/// dentro: o `WM_MOUSEMOVE` para quando o mouse para, por isso o vigia pergunta a posição.
pub fn dentro_da_zona(cursor: (i32, i32), janela: Rect, icone: Option<Rect>) -> bool {
    let (cx, cy) = cursor;
    let em = |r: Rect, m: i32| cx >= r.0 - m && cx <= r.2 + m && cy >= r.1 - m && cy <= r.3 + m;
    em(janela, BORDA_JANELA) || icone.is_some_and(|i| em(i, BORDA_ICONE))
}

/// Posição da janela `(largura, altura)` acima do ícone (ou abaixo, com a barra no alto), presa à área de
/// trabalho com 4 px de margem, como `_anchor_to_tray` (`reco.py:4980-4997`). Sem ícone: canto inferior direito.
pub fn posicao_ancorada(tam: (i32, i32), icone: Option<Rect>, area: Rect) -> (i32, i32) {
    let (w, h) = tam;
    let (wl, wt, wr, wb) = area;
    let (x, y) = match icone {
        Some((_, it, ir, ib)) => {
            let y = if it > (wb - wt) / 2 { it - h - 8 } else { ib + 8 };
            (ir - w, y)
        }
        None => (wr - w - 12, wb - h - 12),
    };
    (x.max(wl + 4).min(wr - w - 4), y.max(wt + 4).min(wb - h - 4))
}

#[derive(Default)]
pub struct Hover {
    fixada: AtomicBool,
    vigiando: AtomicBool,
    icone: Mutex<Option<Rect>>,
}

pub type HoverEstado = Arc<Hover>;

impl Hover {
    pub fn fixada(&self) -> bool {
        self.fixada.load(Ordering::SeqCst)
    }
    pub fn guardar_icone(&self, r: Rect) {
        *lock(&self.icone) = Some(r);
    }
    fn icone(&self) -> Option<Rect> {
        *lock(&self.icone)
    }
}

fn tauri_rect(rect: &tauri::Rect) -> Rect {
    let p = rect.position.to_physical::<i32>(1.0);
    let s = rect.size.to_physical::<i32>(1.0);
    (p.x, p.y, p.x + s.width, p.y + s.height)
}

pub fn guardar_rect_do_evento<R: Runtime>(app: &AppHandle<R>, rect: &tauri::Rect) {
    if let Some(h) = app.try_state::<HoverEstado>() {
        h.guardar_icone(tauri_rect(rect));
    }
}

fn posicionar<R: Runtime>(w: &WebviewWindow<R>, icone: Option<Rect>) {
    let Ok(tam) = w.outer_size() else { return };
    let area = win::area_util();
    let (x, y) = posicao_ancorada((tam.width as i32, tam.height as i32), icone, area);
    let _ = w.set_position(PhysicalPosition::new(x, y));
}

/// `Enter`/`Move` no ícone com a janela escondida: posiciona e mostra **sem ativar**, e liga o vigia.
pub fn no_enter<R: Runtime>(app: &AppHandle<R>, rect: &tauri::Rect) {
    let Some(h) = app.try_state::<HoverEstado>() else { return };
    h.guardar_icone(tauri_rect(rect));
    let Some(w) = app.get_webview_window(JANELA) else { return };
    if h.fixada() || w.is_visible().unwrap_or(false) {
        return;
    }
    posicionar(&w, h.icone());
    // Por cima de tudo enquanto é só espiada (o spike da Fase 0 passou com `always_on_top(true)`); mostrar
    // sem ativar não muda a ordem das janelas, então sem isto ela poderia nascer atrás da que tem o foco.
    let _ = w.set_always_on_top(true);
    let _ = w.show(); // focusable(false): o show não toma o foreground (Fase 0, foco_preservado=true)
    vigiar(app.clone(), w, Arc::clone(&h));
}

/// Mostra, foca e fixa: clique no ícone, "Abrir" do menu, `Reco.Show` da segunda instância, atalho global.
pub fn mostrar_fixada<R: Runtime>(app: &AppHandle<R>) {
    let Some(h) = app.try_state::<HoverEstado>() else { return };
    let Some(w) = app.get_webview_window(JANELA) else { return };
    h.fixada.store(true, Ordering::SeqCst);
    if !w.is_visible().unwrap_or(false) {
        posicionar(&w, h.icone().or_else(|| crate::bandeja::rect_do_icone(app)));
    }
    let _ = w.set_focusable(true);
    let _ = w.show();
    let _ = w.unminimize();
    let _ = w.set_focus();
    // Fixada e com foco, volta a ser janela comum (o velho só faz `lift()`, não fica por cima de tudo).
    let _ = w.set_always_on_top(false);
}

/// Fixa a janela aberta pelo hover (a tela chama em todo clique dentro dela, como `_pin`, `reco.py:5054`). Com
/// `focusable(false)` o clique não ativa a janela; por isso o foco de teclado vem daqui, como no clique que
/// fixa pelo ícone (o único caminho que o spike da Fase 0 provou).
pub fn fixar<R: Runtime>(app: &AppHandle<R>) {
    let Some(h) = app.try_state::<HoverEstado>() else { return };
    let ja_fixada = h.fixada.swap(true, Ordering::SeqCst);
    if let Some(w) = app.get_webview_window(JANELA) {
        if !ja_fixada {
            let _ = w.set_focusable(true);
            let _ = w.set_focus();
            let _ = w.set_always_on_top(false);
        }
    }
}

/// Esconde na bandeja (X, fim do hover) e volta ao modo sem foco.
pub fn esconder<R: Runtime>(app: &AppHandle<R>) {
    if let Some(h) = app.try_state::<HoverEstado>() {
        h.fixada.store(false, Ordering::SeqCst);
    }
    if let Some(w) = app.get_webview_window(JANELA) {
        let _ = w.hide();
        let _ = w.set_focusable(false);
    }
}

/// Polling de 120 ms depois de 500 ms de carência: fora da zona e não fixada → esconde.
fn vigiar<R: Runtime>(app: AppHandle<R>, w: WebviewWindow<R>, h: HoverEstado) {
    if h.vigiando.swap(true, Ordering::SeqCst) {
        return;
    }
    let app_vigia = app.clone();
    let spawned = std::thread::Builder::new().name("reco-hover".into()).spawn(move || {
        let app = app_vigia;
        std::thread::sleep(CARENCIA);
        loop {
            if h.fixada() || !w.is_visible().unwrap_or(false) {
                break;
            }
            let janela = w
                .outer_position()
                .ok()
                .zip(w.outer_size().ok())
                .map(|(p, s)| (p.x, p.y, p.x + s.width as i32, p.y + s.height as i32));
            let Some(janela) = janela else { break };
            if !dentro_da_zona(win::cursor(), janela, h.icone()) {
                esconder(&app);
                break;
            }
            std::thread::sleep(PASSO);
        }
        h.vigiando.store(false, Ordering::SeqCst);
    });
    if spawned.is_err() {
        // Sem thread não há vigia: a janela ficaria aberta para sempre; melhor fixar.
        fixar(&app);
    }
}

#[cfg(windows)]
mod win {
    use super::Rect;
    use windows_sys::Win32::Foundation::{POINT, RECT};
    use windows_sys::Win32::UI::WindowsAndMessaging::{GetCursorPos, SystemParametersInfoW, SPI_GETWORKAREA};

    pub fn cursor() -> (i32, i32) {
        let mut p = POINT { x: 0, y: 0 };
        unsafe { GetCursorPos(&mut p) };
        (p.x, p.y)
    }

    pub fn area_util() -> Rect {
        let mut r = RECT { left: 0, top: 0, right: 0, bottom: 0 };
        unsafe { SystemParametersInfoW(SPI_GETWORKAREA, 0, &mut r as *mut _ as _, 0) };
        (r.left, r.top, r.right, r.bottom)
    }
}

#[cfg(not(windows))]
mod win {
    use super::Rect;
    pub fn cursor() -> (i32, i32) {
        (i32::MIN, i32::MIN)
    }
    pub fn area_util() -> Rect {
        (0, 0, 1920, 1080)
    }
}

#[cfg(test)]
mod testes {
    use super::*;

    const JAN: Rect = (1000, 400, 1500, 1100);
    const ICO: Rect = (1700, 1160, 1740, 1200);

    #[test]
    fn cursor_parado_sobre_o_icone_fica_dentro() {
        assert!(dentro_da_zona((1720, 1180), JAN, Some(ICO)));
        assert!(dentro_da_zona((1696, 1156), JAN, Some(ICO)), "4 px fora do ícone ainda conta");
        assert!(!dentro_da_zona((1695, 1180), JAN, Some(ICO)), "5 px fora do ícone já não");
    }

    #[test]
    fn borda_de_6_px_da_janela() {
        assert!(dentro_da_zona((994, 700), JAN, None));
        assert!(dentro_da_zona((1506, 394), JAN, None));
        assert!(!dentro_da_zona((993, 700), JAN, None));
        assert!(!dentro_da_zona((1200, 1107), JAN, None));
    }

    #[test]
    fn fora_das_duas_zonas_esconde() {
        assert!(!dentro_da_zona((100, 100), JAN, Some(ICO)));
        assert!(!dentro_da_zona((1600, 1180), JAN, Some(ICO)), "entre a janela e o ícone");
        assert!(!dentro_da_zona((100, 100), JAN, None));
    }

    #[test]
    fn ancora_acima_do_icone_e_presa_na_area() {
        let area = (0, 0, 1920, 1152); // barra embaixo: área útil termina em 1152
        let ico = (1700, 1160, 1740, 1200);
        // 1160 - 700 - 8 = 452, mas a margem de 4 px da área (1152 - 700 - 4 = 448) vence.
        assert_eq!(posicao_ancorada((500, 700), Some(ico), area), (1240, 448));
        assert_eq!(posicao_ancorada((300, 400), Some(ico), (0, 0, 1920, 1200)), (1440, 752), "folgada: 8 px acima");
        // Ícone no canto direito: a janela não passa da borda.
        assert_eq!(posicao_ancorada((500, 700), Some((1890, 1160, 1920, 1200)), area), (1416, 448));
        // Barra no alto: abaixo do ícone.
        assert_eq!(posicao_ancorada((500, 700), Some((1700, 0, 1740, 40)), (0, 48, 1920, 1200)), (1240, 52));
        // Sem ícone: canto inferior direito.
        assert_eq!(posicao_ancorada((500, 700), None, area), (1408, 440));
    }
}

//! Bandeja dirigida pelo Rust a partir dos eventos do motor (passo 8; molde: Guarita `lib.rs:355-405`).
//! Rótulos e dica espelham o app velho (`reco.py:4938-4952`, `:5059-5073`); o ícone fica vermelho gravando e
//! também pausado (`reco.py:5064-5066`). Textos PT/EN/PL numa tabela pequena aqui (F3-D4: webview escondida tem
//! timers estrangulados, então a bandeja não depende dela); o polonês é o da tabela de Toni (`i18n_pl.py`).

use std::sync::atomic::{AtomicU8, Ordering};
use std::sync::{Arc, Mutex};

use tauri::image::Image;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::{TrayIcon, TrayIconBuilder};
use tauri::{AppHandle, Manager, Runtime};

use crate::estado::{EstadoCasco, Lingua};

pub const ID_BANDEJA: &str = "reco";
pub const ID_GRAVAR: &str = "gravar";
pub const ID_PAUSAR: &str = "pausar";
pub const ID_ABRIR: &str = "abrir";
pub const ID_SAIR: &str = "sair";

/// Uma frase em português, inglês e polonês.
type Texto = (&'static str, &'static str, &'static str);

const GRAVAR: Texto = ("Gravar", "Record", "Nagrywaj");
const PARAR: Texto = ("Parar", "Stop", "Zatrzymaj");
const PAUSAR: Texto = ("Pausar", "Pause", "Wstrzymaj");
const CONTINUAR: Texto = ("Continuar", "Resume", "Wznów");
const ABRIR: Texto = ("Abrir", "Open", "Otwórz");
const SAIR: Texto = ("Sair", "Quit", "Zakończ");

fn tr(t: Texto, lingua: Lingua) -> &'static str {
    lingua.escolher(t.0, t.1, t.2)
}

/// Rótulos dos dois primeiros itens do menu por estado do motor: `(gravar_ou_parar, pausar_ou_continuar)`.
/// `None` = sem ação de um clique nesse estado (item desabilitado), como o velho em BUSY/STOPPED.
pub fn rotulos(estado: &str, lingua: Lingua) -> (Option<&'static str>, Option<&'static str>) {
    let rec = match estado {
        "recording" | "paused" => Some(tr(PARAR, lingua)),
        "idle" => Some(tr(GRAVAR, lingua)),
        _ => None, // starting, stopping, stopped
    };
    let pausa = match estado {
        "recording" => Some(tr(PAUSAR, lingua)),
        "paused" => Some(tr(CONTINUAR, lingua)),
        _ => None,
    };
    (rec, pausa)
}

/// `HH:MM:SS`, como o cronômetro do app velho.
pub fn hms(segundos: u64) -> String {
    format!("{:02}:{:02}:{:02}", segundos / 3600, (segundos / 60) % 60, segundos % 60)
}

/// Dica do ícone: "Reco — gravando 00:12:34", "Reco — pausado …" ou "Reco — pronto".
pub fn dica(estado: &str, segundos: u64, lingua: Lingua) -> String {
    match estado {
        "recording" => format!("Reco — {} {}", lingua.escolher("gravando", "recording", "nagrywanie"), hms(segundos)),
        "paused" => format!("Reco — {} {}", lingua.escolher("pausado", "paused", "pauza"), hms(segundos)),
        _ => format!("Reco — {}", lingua.escolher("pronto", "ready", "gotowe")),
    }
}

/// Vermelho com a sessão "armada": gravando ou pausado.
pub fn icone_vermelho(estado: &str) -> bool {
    matches!(estado, "recording" | "paused")
}

/// Itens do menu guardados para trocar texto e habilitado sem remontar o menu.
pub struct Itens<R: Runtime> {
    gravar: MenuItem<R>,
    pausar: MenuItem<R>,
    abrir: MenuItem<R>,
    sair: MenuItem<R>,
}

// Manual: o derive exigiria `R: Clone`, e o runtime não é (os `MenuItem` são).
impl<R: Runtime> Clone for Itens<R> {
    fn clone(&self) -> Self {
        Itens {
            gravar: self.gravar.clone(),
            pausar: self.pausar.clone(),
            abrir: self.abrir.clone(),
            sair: self.sair.clone(),
        }
    }
}

pub struct Bandeja<R: Runtime> {
    itens: Mutex<Option<Itens<R>>>,
    tray: Mutex<Option<TrayIcon<R>>>,
    /// 0 = cinza, 1 = vermelho (nasce cinza).
    ultimo_vermelho: AtomicU8,
}

impl<R: Runtime> Default for Bandeja<R> {
    fn default() -> Self {
        Bandeja { itens: Mutex::new(None), tray: Mutex::new(None), ultimo_vermelho: AtomicU8::new(0) }
    }
}

pub type BandejaEstado<R> = Arc<Bandeja<R>>;

const ICONE_IDLE: &[u8] = include_bytes!("../icons/tray_idle.ico");
const ICONE_REC: &[u8] = include_bytes!("../icons/tray_rec.ico");

fn icone(vermelho: bool) -> Option<Image<'static>> {
    Image::from_bytes(if vermelho { ICONE_REC } else { ICONE_IDLE }).ok()
}

/// Monta a bandeja. `on_menu` e `on_icone` vêm do `lib.rs` (rodam na thread principal: nunca bloquear nelas).
pub fn criar<R, M, I>(app: &AppHandle<R>, on_menu: M, on_icone: I) -> tauri::Result<()>
where
    R: Runtime,
    M: Fn(&AppHandle<R>, &str) + Send + Sync + 'static,
    I: Fn(&TrayIcon<R>, tauri::tray::TrayIconEvent) + Send + Sync + 'static,
{
    // Nasce em português; o `definir_lingua` da interface redesenha na língua dela.
    let pt = Lingua::Pt;
    let gravar = MenuItem::with_id(app, ID_GRAVAR, tr(GRAVAR, pt), true, None::<&str>)?;
    let pausar = MenuItem::with_id(app, ID_PAUSAR, tr(PAUSAR, pt), false, None::<&str>)?;
    let abrir = MenuItem::with_id(app, ID_ABRIR, tr(ABRIR, pt), true, None::<&str>)?;
    let sair = MenuItem::with_id(app, ID_SAIR, tr(SAIR, pt), true, None::<&str>)?;
    let sep1 = PredefinedMenuItem::separator(app)?;
    let sep2 = PredefinedMenuItem::separator(app)?;
    let menu = Menu::with_items(app, &[&gravar, &pausar, &sep1, &abrir, &sep2, &sair])?;
    let mut tb = TrayIconBuilder::with_id(ID_BANDEJA)
        .tooltip(dica("idle", 0, pt))
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(move |app, ev| on_menu(app, ev.id().as_ref()))
        .on_tray_icon_event(on_icone);
    if let Some(img) = icone(false) {
        tb = tb.icon(img);
    }
    let tray = tb.build(app)?;
    let b = app.state::<BandejaEstado<R>>();
    *crate::motor::router::lock(&b.itens) = Some(Itens { gravar, pausar, abrir, sair });
    *crate::motor::router::lock(&b.tray) = Some(tray);
    Ok(())
}

/// Redesenha menu, ícone e dica a partir do estado guardado. Pode rodar fora da thread principal (os setters
/// do Tauri despacham para ela); por isso a thread principal nunca pode esperar o motor.
pub fn atualizar<R: Runtime>(app: &AppHandle<R>, est: &EstadoCasco) {
    let Some(b) = app.try_state::<BandejaEstado<R>>() else { return };
    let (estado, seg, l) = (est.rec_state(), est.segundos(), est.lingua());
    let (rec, pausa) = rotulos(&estado, l);
    // Os setters do Tauri esperam a thread principal (`run_item_main_thread`): nunca chamá-los com uma trava
    // nossa na mão, senão a thread principal (que também lê estas travas) e esta se travam uma à outra.
    let itens = crate::motor::router::lock(&b.itens).as_ref().map(Itens::clone);
    let tray = crate::motor::router::lock(&b.tray).clone();
    if let Some(it) = itens.as_ref() {
        let _ = it.gravar.set_text(rec.unwrap_or(tr(GRAVAR, l)));
        let _ = it.gravar.set_enabled(rec.is_some());
        let _ = it.pausar.set_text(pausa.unwrap_or(tr(PAUSAR, l)));
        let _ = it.pausar.set_enabled(pausa.is_some());
        let _ = it.abrir.set_text(tr(ABRIR, l));
        let _ = it.sair.set_text(tr(SAIR, l));
    }
    let vermelho = icone_vermelho(&estado);
    // O `timer` chega 1/s: o ícone só é trocado quando muda de cor; a dica, sempre.
    let trocar_icone = b.ultimo_vermelho.swap(vermelho as u8, Ordering::SeqCst) != vermelho as u8;
    if let Some(tray) = tray.as_ref() {
        if trocar_icone {
            let _ = tray.set_icon(icone(vermelho));
        }
        let _ = tray.set_tooltip(Some(dica(&estado, seg, l)));
    }
}

/// Retângulo físico do ícone `(esquerda, topo, direita, baixo)`, se o Explorer já o posicionou.
pub fn rect_do_icone<R: Runtime>(app: &AppHandle<R>) -> Option<(i32, i32, i32, i32)> {
    let b = app.try_state::<BandejaEstado<R>>()?;
    let tray = crate::motor::router::lock(&b.tray).clone()?; // soltar a trava antes do `rect()` (ver `atualizar`)
    let r = tray.rect().ok()??;
    let p = r.position.to_physical::<i32>(1.0);
    let s = r.size.to_physical::<i32>(1.0);
    (s.width > 0 && s.height > 0).then_some((p.x, p.y, p.x + s.width, p.y + s.height))
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn rotulos_por_estado_como_o_app_velho() {
        assert_eq!(rotulos("idle", Lingua::Pt), (Some("Gravar"), None));
        assert_eq!(rotulos("recording", Lingua::Pt), (Some("Parar"), Some("Pausar")));
        assert_eq!(rotulos("paused", Lingua::Pt), (Some("Parar"), Some("Continuar")));
        for l in [Lingua::Pt, Lingua::En, Lingua::Pl] {
            for sem_acao in ["starting", "stopping", "stopped"] {
                assert_eq!(rotulos(sem_acao, l), (None, None), "{sem_acao} ({l:?}): nada de Parar");
            }
        }
        assert_eq!(rotulos("recording", Lingua::En), (Some("Stop"), Some("Pause")));
        assert_eq!(rotulos("idle", Lingua::En), (Some("Record"), None));
    }

    #[test]
    fn rotulos_em_polones_com_os_termos_de_toni() {
        // Os mesmos de `i18n_pl.py` (Gravar, Parar, Pausar, Continuar, Abrir, Sair).
        assert_eq!(rotulos("idle", Lingua::Pl), (Some("Nagrywaj"), None));
        assert_eq!(rotulos("recording", Lingua::Pl), (Some("Zatrzymaj"), Some("Wstrzymaj")));
        assert_eq!(rotulos("paused", Lingua::Pl), (Some("Zatrzymaj"), Some("Wznów")));
        assert_eq!(tr(ABRIR, Lingua::Pl), "Otwórz");
        assert_eq!(tr(SAIR, Lingua::Pl), "Zakończ");
    }

    #[test]
    fn dica_com_cronometro() {
        assert_eq!(dica("recording", 754, Lingua::Pt), "Reco — gravando 00:12:34");
        assert_eq!(dica("paused", 3600, Lingua::Pt), "Reco — pausado 01:00:00");
        assert_eq!(dica("idle", 99, Lingua::Pt), "Reco — pronto");
        assert_eq!(dica("stopped", 5, Lingua::En), "Reco — ready");
        assert_eq!(dica("recording", 5, Lingua::En), "Reco — recording 00:00:05");
        // Polonês: "Reco — nagrywanie {d}", "Reco — pauza {d}", "Reco — gotowe" da tabela de Toni.
        assert_eq!(dica("recording", 754, Lingua::Pl), "Reco — nagrywanie 00:12:34");
        assert_eq!(dica("paused", 3600, Lingua::Pl), "Reco — pauza 01:00:00");
        assert_eq!(dica("idle", 0, Lingua::Pl), "Reco — gotowe");
        assert_eq!(dica("stopping", 7, Lingua::Pl), "Reco — gotowe");
    }

    #[test]
    fn icone_vermelho_gravando_e_pausado() {
        assert!(icone_vermelho("recording") && icone_vermelho("paused"));
        assert!(!icone_vermelho("idle") && !icone_vermelho("stopping") && !icone_vermelho("stopped"));
    }
}

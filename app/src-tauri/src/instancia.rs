//! Instância única e repasse de CLI (passo 7), antes do `Builder` do Tauri:
//!
//! 1. `--transcribe` (D6, F3-D14): repassado ao motor congelado **antes** do mutex, como o velho
//!    (`reco.py:5148-5179` roda antes de `:5197-5210`). Sem janela, webview, bandeja nem mutex.
//! 2. Mutex `Local\Reco.SingleInstance` (D7, F3-D2): o mesmo do app velho, então os dois se excluem. Se já
//!    existe, `PostMessageW(HWND_BROADCAST, "Reco.Show")` e sai com 0 (quem está aberto aparece).
//! 3. Receber `Reco.Show`: janela de topo escondida (message-only não recebe broadcast) numa thread com laço
//!    de mensagens, como o `tray.py:136-137`. Ao chegar, a closure do casco mostra, foca e fixa.

use std::path::PathBuf;
use std::process::{Command, Stdio};

/// Argumentos para o motor quando há `--transcribe` (com `--diarize` e o resto intactos), senão `None`.
/// Recebe os argumentos **sem** o nome do programa.
pub fn repasse_cli(args: &[String]) -> Option<Vec<String>> {
    args.iter().any(|a| a == "--transcribe").then(|| args.to_vec())
}

/// Onde está o motor para o repasse: release = `engine/reco-engine.exe` ao lado do exe do casco (recurso do
/// passo 3); debug = `RECO_ENGINE=<exe>` ou `python -m reco_engine` em `engine/` do repo.
fn comando_do_motor() -> Option<Command> {
    if cfg!(debug_assertions) {
        if let Some(exe) = std::env::var_os("RECO_ENGINE").filter(|p| !p.is_empty()) {
            return Some(Command::new(exe));
        }
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..").join("engine");
        let mut c = Command::new("python");
        c.args(["-m", "reco_engine"]).current_dir(dir);
        return Some(c);
    }
    let exe = std::env::current_exe().ok()?.parent()?.join("engine").join(crate::motor::bundled_exe_name());
    exe.is_file().then(|| Command::new(exe))
}

/// Roda o motor com os argumentos do repasse, espera e devolve o código dele. Motor ausente ou que não sobe:
/// 2, como erro do velho. O log e o `.txt` são do motor (`cli.py`): o casco não escreve nada.
pub fn rodar_repasse(args: &[String]) -> i32 {
    let Some(mut cmd) = comando_do_motor() else { return 2 };
    cmd.args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .env("PYTHONUNBUFFERED", "1")
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    match cmd.status() {
        Ok(s) => s.code().unwrap_or(2),
        Err(_) => 2,
    }
}

pub const NOME_MUTEX: &str = "Local\\Reco.SingleInstance";
pub const MENSAGEM_SHOW: &str = "Reco.Show";

#[cfg(windows)]
pub use win::{adquirir_mutex, avisar_quem_esta_aberto, escutar_show, Mutex as MutexDoReco};

/// Garante a instância única. `Some(mutex)` = somos os donos (guardar até o fim do processo); `None` = outro
/// Reco (velho ou novo) já está aberto: ele foi avisado para aparecer e este processo deve sair com 0.
/// Em debug, `RECO_SEM_MUTEX=1` pula o mutex (só para provar o casco com o app velho aberto; nunca no release).
#[cfg(windows)]
pub fn garantir_unica() -> Option<Option<MutexDoReco>> {
    if cfg!(debug_assertions) && std::env::var("RECO_SEM_MUTEX").as_deref() == Ok("1") {
        ::log::warn!("[reco] RECO_SEM_MUTEX=1: mutex pulado (só debug)");
        return Some(None);
    }
    match adquirir_mutex(NOME_MUTEX) {
        Some(m) => Some(Some(m)),
        None => {
            avisar_quem_esta_aberto();
            None
        }
    }
}

#[cfg(windows)]
mod win {
    use std::sync::OnceLock;

    use windows_sys::Win32::Foundation::{CloseHandle, GetLastError, HANDLE, HWND, LPARAM, LRESULT, WPARAM};
    use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows_sys::Win32::System::Threading::CreateMutexW;
    use windows_sys::Win32::UI::WindowsAndMessaging::{
        CreateWindowExW, DefWindowProcW, DispatchMessageW, GetMessageW, PostMessageW, RegisterClassW,
        RegisterWindowMessageW, TranslateMessage, HWND_BROADCAST, MSG, WNDCLASSW,
    };

    use super::MENSAGEM_SHOW;

    const ERROR_ALREADY_EXISTS: u32 = 183;

    fn wide(s: &str) -> Vec<u16> {
        s.encode_utf16().chain(std::iter::once(0)).collect()
    }

    /// Dono do mutex nomeado; fecha o handle ao cair (o sistema também fecha quando o processo sai).
    pub struct Mutex(HANDLE);
    unsafe impl Send for Mutex {}
    unsafe impl Sync for Mutex {}

    impl Drop for Mutex {
        fn drop(&mut self) {
            unsafe { CloseHandle(self.0) };
        }
    }

    /// `CreateMutexW`; `None` se o nome já existe (`GetLastError() == 183`) ou a chamada falhou.
    pub fn adquirir_mutex(nome: &str) -> Option<Mutex> {
        let n = wide(nome);
        unsafe {
            let h = CreateMutexW(std::ptr::null(), 0, n.as_ptr());
            let erro = GetLastError();
            if h.is_null() {
                return None;
            }
            if erro == ERROR_ALREADY_EXISTS {
                CloseHandle(h);
                return None;
            }
            Some(Mutex(h))
        }
    }

    fn mensagem_show() -> u32 {
        unsafe { RegisterWindowMessageW(wide(MENSAGEM_SHOW).as_ptr()) }
    }

    /// Igual ao velho: `PostMessageW(HWND_BROADCAST, RegisterWindowMessageW("Reco.Show"))`.
    pub fn avisar_quem_esta_aberto() {
        unsafe { PostMessageW(HWND_BROADCAST, mensagem_show(), 0, 0) };
    }

    type AoShow = Box<dyn Fn() + Send + Sync>;
    static AO_SHOW: OnceLock<AoShow> = OnceLock::new();
    static MSG_SHOW: OnceLock<u32> = OnceLock::new();

    unsafe extern "system" fn wnd_proc(hwnd: HWND, msg: u32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
        if Some(&msg) == MSG_SHOW.get() {
            if let Some(f) = AO_SHOW.get() {
                // Nunca deixar um pânico atravessar de volta para o Win32.
                let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(f));
            }
            return 0;
        }
        DefWindowProcW(hwnd, msg, wparam, lparam)
    }

    /// Cria a janela de topo escondida que recebe o `Reco.Show` e roda o laço de mensagens numa thread
    /// própria. `ao_show` roda nessa thread: deve só despachar para a thread principal.
    pub fn escutar_show(ao_show: impl Fn() + Send + Sync + 'static) {
        if AO_SHOW.set(Box::new(ao_show)).is_err() {
            return; // já escutando
        }
        let _ = MSG_SHOW.set(mensagem_show());
        let r = std::thread::Builder::new().name("reco-show".into()).spawn(|| unsafe {
            let hinst = GetModuleHandleW(std::ptr::null());
            let classe = wide("RecoCascoShow");
            let mut wc: WNDCLASSW = std::mem::zeroed();
            wc.lpfnWndProc = Some(wnd_proc);
            wc.hInstance = hinst;
            wc.lpszClassName = classe.as_ptr();
            RegisterClassW(&wc);
            // Sem pai e sem WS_VISIBLE: de topo e invisível, recebe broadcast (message-only não recebe).
            let titulo = wide("Reco");
            let hwnd = CreateWindowExW(
                0,
                classe.as_ptr(),
                titulo.as_ptr(),
                0,
                0,
                0,
                0,
                0,
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                hinst,
                std::ptr::null(),
            );
            if hwnd.is_null() {
                ::log::warn!("[reco] janela do Reco.Show não nasceu: {}", GetLastError());
                return;
            }
            let mut msg: MSG = std::mem::zeroed();
            while GetMessageW(&mut msg, std::ptr::null_mut(), 0, 0) > 0 {
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
        });
        if let Err(e) = r {
            ::log::warn!("[reco] thread do Reco.Show não subiu: {e}");
        }
    }
}

#[cfg(test)]
mod testes {
    use super::*;

    fn v(a: &[&str]) -> Vec<String> {
        a.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn repasse_cli_so_com_transcribe() {
        let a = v(&["--transcribe", "a.mp3", "--diarize"]);
        assert_eq!(repasse_cli(&a), Some(a.clone()));
        assert_eq!(repasse_cli(&v(&["C:/x y/b_reco.mp3", "--transcribe"])), Some(v(&["C:/x y/b_reco.mp3", "--transcribe"])));
        assert_eq!(repasse_cli(&v(&[])), None);
        assert_eq!(repasse_cli(&v(&["--oculto"])), None);
        assert_eq!(repasse_cli(&v(&["--transcribe-x"])), None, "só a flag exata");
    }

    #[cfg(windows)]
    #[test]
    fn mutex_detecta_a_segunda_aquisicao() {
        let nome = format!("Local\\Reco.Teste.{}", std::process::id());
        let primeiro = adquirir_mutex(&nome).expect("a primeira aquisição tem de passar");
        assert!(adquirir_mutex(&nome).is_none(), "a segunda tem de ver o mutex existente");
        drop(primeiro);
        assert!(adquirir_mutex(&nome).is_some(), "solto, o nome volta a estar livre");
    }
}

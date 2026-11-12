//! Iniciar com o Windows, opt-in em Opções (F4-D6): o valor `Reco` em `HKCU\…\CurrentVersion\Run`, gravado à mão.
//!
//! Por que não o `tauri-plugin-autostart` (passo 13 da Fase 4, 12/11/2026): o `auto-launch` 0.6.0 dele monta o valor
//! com `format!("{} {}", caminho, args)` (`windows.rs:77`), **sem aspas**, e a pasta do usuário pode ter espaço: o
//! Windows tenta `C:\Users\<primeira palavra>.exe` antes do exe certo (caminho sem aspas clássico). E o `disable()`
//! dele só apaga o `Run`, deixando a marca em `…\Explorer\StartupApproved\Run`. Aqui o valor sai `"<exe>" --oculto`
//! (`valor_run`) e desligar apaga as duas entradas. O estado é lido do próprio Windows, sem gravar em outro lugar (D6).

use tauri::Runtime;

pub const NOME: &str = "Reco";
pub const ARGS: [&str; 1] = ["--oculto"];

/// As duas chaves (sob `HKEY_CURRENT_USER`) e o nome do valor. Os testes passam chaves próprias.
pub struct Chaves<'a> {
    pub run: &'a str,
    pub aprovado: &'a str,
    pub nome: &'a str,
}

pub const CHAVES_REAIS: Chaves<'static> = Chaves {
    run: r"Software\Microsoft\Windows\CurrentVersion\Run",
    aprovado: r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
    nome: NOME,
};

/// O valor do `Run`: o caminho **entre aspas** e os argumentos (`"C:\Users\x y\…\reco.exe" --oculto`).
pub fn valor_run(exe: &str, args: &[&str]) -> String {
    let mut v = format!("\"{exe}\"");
    for a in args {
        v.push(' ');
        v.push_str(a);
    }
    v
}

/// A marca do Gerenciador de Tarefas em `StartupApproved\Run`: 1º byte `02`/`06` habilitado, `03`/`07` desabilitado
/// (bit 0 ligado). Vazia ou ausente conta como habilitada (é o que o Windows faz sem a marca).
pub fn marca_desabilitada(bytes: &[u8]) -> bool {
    bytes.first().is_some_and(|b| b & 1 == 1)
}

#[cfg(windows)]
mod reg {
    use super::{marca_desabilitada, Chaves};
    use windows_registry::CURRENT_USER;

    /// `ERROR_FILE_NOT_FOUND` como HRESULT: chave ou valor que não existe.
    fn nao_existe(e: &windows_registry::Result<()>) -> bool {
        matches!(e, Err(err) if err.code().0 as u32 == 0x8007_0002)
    }

    /// Apaga um valor; chave ou valor ausente é sucesso (desligar duas vezes não é erro).
    fn apagar(chave: &str, nome: &str) -> Result<(), String> {
        let r = CURRENT_USER.options().write().open(chave).and_then(|k| k.remove_value(nome));
        if r.is_ok() || nao_existe(&r) {
            Ok(())
        } else {
            r.map_err(|e| e.to_string())
        }
    }

    pub fn valor_atual(ch: &Chaves) -> Option<String> {
        CURRENT_USER.open(ch.run).and_then(|k| k.get_string(ch.nome)).ok()
    }

    /// Grava o `Run` e tira a marca do Gerenciador de Tarefas (se ele a desabilitou, ligar em Opções vence).
    pub fn ligar(ch: &Chaves, valor: &str) -> Result<(), String> {
        CURRENT_USER.create(ch.run).and_then(|k| k.set_string(ch.nome, valor)).map_err(|e| e.to_string())?;
        apagar(ch.aprovado, ch.nome)
    }

    /// Apaga o `Run` **e** a marca do `StartupApproved\Run` (a máquina volta a como estava).
    pub fn desligar(ch: &Chaves) -> Result<(), String> {
        apagar(ch.run, ch.nome)?;
        apagar(ch.aprovado, ch.nome)
    }

    /// Ligado = o valor existe no `Run` e o Gerenciador de Tarefas não o desabilitou.
    pub fn ligado(ch: &Chaves) -> bool {
        if valor_atual(ch).is_none() {
            return false;
        }
        let marca = CURRENT_USER.open(ch.aprovado).and_then(|k| k.get_value(ch.nome));
        !matches!(marca, Ok(v) if marca_desabilitada(&v))
    }

    /// Só troca o valor **antigo deste mesmo exe** (o sem aspas que o plugin gravava) pelo certo. Outro caminho fica
    /// como está: um casco de build (`C:\pt\…`) aberto com o autostart ligado não pode tomar o boot do instalado.
    /// Desligado não cria nada. Devolve se regravou.
    pub fn reparar(ch: &Chaves, antigo: &str, certo: &str) -> Result<bool, String> {
        match valor_atual(ch) {
            Some(atual) if atual == antigo => {
                CURRENT_USER.create(ch.run).and_then(|k| k.set_string(ch.nome, certo)).map_err(|e| e.to_string())?;
                Ok(true)
            }
            _ => Ok(false),
        }
    }
}

/// Fora do Windows não há `Run`: desligado sempre, ligar falha com motivo.
#[cfg(not(windows))]
mod reg {
    use super::Chaves;
    pub fn ligar(_: &Chaves, _: &str) -> Result<(), String> {
        Err("iniciar com o Windows só existe no Windows".into())
    }
    pub fn desligar(_: &Chaves) -> Result<(), String> {
        Ok(())
    }
    pub fn ligado(_: &Chaves) -> bool {
        false
    }
    pub fn reparar(_: &Chaves, _: &str, _: &str) -> Result<bool, String> {
        Ok(false)
    }
}

/// O valor que o `tauri-plugin-autostart` gravava (`format!("{} {}")` do `auto-launch` 0.6.0), para o reparo.
pub fn valor_antigo_sem_aspas(exe: &str, args: &[&str]) -> String {
    format!("{} {}", exe, args.join(" "))
}

fn exe_atual() -> Result<String, String> {
    Ok(std::env::current_exe().map_err(|e| e.to_string())?.display().to_string())
}

fn valor_deste_exe() -> Result<String, String> {
    Ok(valor_run(&exe_atual()?, &ARGS))
}

/// Na partida: se já estava ligado com o valor velho **deste exe** (sem aspas), troca pelo certo. Erro só vai ao log.
pub fn reparar_na_partida() {
    let r = exe_atual()
        .and_then(|exe| reg::reparar(&CHAVES_REAIS, &valor_antigo_sem_aspas(&exe, &ARGS), &valor_run(&exe, &ARGS)));
    match r {
        Ok(true) => ::log::info!("[reco] iniciar com o Windows: valor do Run regravado com aspas"),
        Ok(false) => {}
        Err(e) => ::log::warn!("[reco] iniciar com o Windows: reparo falhou: {e}"),
    }
}

#[tauri::command]
pub fn autostart_ligado<R: Runtime>(_app: tauri::AppHandle<R>) -> Result<bool, String> {
    Ok(reg::ligado(&CHAVES_REAIS))
}

#[tauri::command]
pub fn definir_autostart<R: Runtime>(_app: tauri::AppHandle<R>, ligar: bool) -> Result<bool, String> {
    if ligar {
        reg::ligar(&CHAVES_REAIS, &valor_deste_exe()?)?;
    } else {
        reg::desligar(&CHAVES_REAIS)?;
    }
    Ok(reg::ligado(&CHAVES_REAIS))
}

#[cfg(test)]
mod testes {
    use super::*;

    const EXE: &str = r"C:\Users\Nome Com Espaco\AppData\Local\Reco\reco.exe";

    #[test]
    fn valor_do_run_vai_entre_aspas() {
        assert_eq!(valor_run(EXE, &ARGS), r#""C:\Users\Nome Com Espaco\AppData\Local\Reco\reco.exe" --oculto"#);
        assert_eq!(valor_run(r"C:\R\reco.exe", &[]), r#""C:\R\reco.exe""#);
    }

    #[test]
    fn marca_do_gerenciador() {
        assert!(!marca_desabilitada(&[2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]));
        assert!(marca_desabilitada(&[3, 0, 0, 0, 0x10, 0x20, 0x30, 0x40, 1, 2, 3, 4]));
        assert!(!marca_desabilitada(&[6, 0, 0, 0]));
        assert!(marca_desabilitada(&[7]));
        assert!(!marca_desabilitada(&[]));
    }

    /// Contra o registro de verdade, mas numa chave só de teste (`HKCU\Software\RecoTeste`), nunca no `Run` real.
    #[cfg(windows)]
    mod registro {
        use super::super::{reg, valor_antigo_sem_aspas, valor_run, Chaves, ARGS};
        use super::EXE;
        use std::sync::Mutex;
        use windows_registry::{Type, CURRENT_USER};

        const RAIZ: &str = r"Software\RecoTeste";
        const HABILITADA: [u8; 12] = [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        const DESABILITADA: [u8; 12] = [3, 0, 0, 0, 0x5a, 0x1c, 0x9e, 0x3f, 0x4b, 0x2d, 0xdb, 0x01];
        /// Os testes daqui dividem a `RAIZ` e a apagam no fim: um de cada vez.
        static TRAVA: Mutex<()> = Mutex::new(());

        struct Sandbox {
            run: String,
            aprovado: String,
            _trava: std::sync::MutexGuard<'static, ()>,
        }

        impl Sandbox {
            fn nova(nome: &str) -> Self {
                let trava = TRAVA.lock().unwrap_or_else(|e| e.into_inner());
                let base = format!(r"{RAIZ}\{nome}-{}", std::process::id());
                let s = Sandbox { run: format!(r"{base}\Run"), aprovado: format!(r"{base}\StartupApproved\Run"), _trava: trava };
                // A chave do `StartupApproved` existe numa máquina real; sem ela o teste da limpeza passaria vazio.
                CURRENT_USER.create(&s.aprovado).expect("criar a chave de teste");
                s
            }
            fn chaves(&self) -> Chaves<'_> {
                Chaves { run: &self.run, aprovado: &self.aprovado, nome: "Reco" }
            }
            fn marcar(&self, bytes: &[u8]) {
                CURRENT_USER.create(&self.aprovado).unwrap().set_bytes("Reco", Type::Bytes, bytes).unwrap();
            }
            fn tem_marca(&self) -> bool {
                CURRENT_USER.open(&self.aprovado).and_then(|k| k.get_value("Reco")).is_ok()
            }
        }

        impl Drop for Sandbox {
            fn drop(&mut self) {
                let _ = CURRENT_USER.remove_tree(RAIZ);
                let _ = CURRENT_USER.open("Software").and_then(|k| k.remove_tree("RecoTeste"));
            }
        }

        #[test]
        fn ligar_grava_com_aspas_e_desligar_limpa_as_duas_entradas() {
            let sb = Sandbox::nova("ligar");
            let ch = sb.chaves();
            let valor = valor_run(EXE, &ARGS);
            assert!(!reg::ligado(&ch));

            // O Gerenciador de Tarefas tinha desabilitado: ligar em Opções vence.
            sb.marcar(&DESABILITADA);
            reg::ligar(&ch, &valor).unwrap();
            assert_eq!(reg::valor_atual(&ch).as_deref(), Some(r#""C:\Users\Nome Com Espaco\AppData\Local\Reco\reco.exe" --oculto"#));
            assert!(reg::ligado(&ch));

            // O Windows (ou o plugin antigo) deixa a marca de habilitado: desligar tem de apagá-la também.
            sb.marcar(&HABILITADA);
            reg::desligar(&ch).unwrap();
            assert_eq!(reg::valor_atual(&ch), None, "o Run ficou");
            assert!(!sb.tem_marca(), "a marca do StartupApproved ficou");
            assert!(!reg::ligado(&ch));

            // Desligar de novo (nada a apagar) não é erro.
            reg::desligar(&ch).unwrap();
        }

        #[test]
        fn ligado_respeita_a_marca_do_gerenciador() {
            let sb = Sandbox::nova("marca");
            let ch = sb.chaves();
            reg::ligar(&ch, &valor_run(EXE, &ARGS)).unwrap();
            assert!(reg::ligado(&ch), "sem marca = habilitado");
            sb.marcar(&DESABILITADA);
            assert!(!reg::ligado(&ch), "desabilitado no Gerenciador de Tarefas");
            sb.marcar(&HABILITADA);
            assert!(reg::ligado(&ch));
        }

        #[test]
        fn reparar_troca_o_valor_sem_aspas_e_nao_liga_quem_esta_desligado() {
            let sb = Sandbox::nova("reparar");
            let ch = sb.chaves();
            let certo = valor_run(EXE, &ARGS);
            let antigo = valor_antigo_sem_aspas(EXE, &ARGS);
            assert_eq!(antigo, format!("{EXE} --oculto"), "o formato do plugin");
            assert!(!reg::reparar(&ch, &antigo, &certo).unwrap());
            assert_eq!(reg::valor_atual(&ch), None, "desligado continua desligado");

            // O que o build 0.3.0 com o plugin gravava.
            CURRENT_USER.create(&sb.run).unwrap().set_string("Reco", &antigo).unwrap();
            assert!(reg::reparar(&ch, &antigo, &certo).unwrap());
            assert_eq!(reg::valor_atual(&ch).as_deref(), Some(certo.as_str()));
            assert!(!reg::reparar(&ch, &antigo, &certo).unwrap(), "já certo: nada a fazer");
        }

        #[test]
        fn reparar_nao_toma_o_boot_de_outro_exe() {
            let sb = Sandbox::nova("outro");
            let ch = sb.chaves();
            // Ligado pelo app instalado; quem abre é um casco de build noutro caminho.
            let do_instalado = valor_run(EXE, &ARGS);
            CURRENT_USER.create(&sb.run).unwrap().set_string("Reco", &do_instalado).unwrap();
            let build = r"C:\pt\debug\reco.exe";
            let mudou = reg::reparar(&ch, &valor_antigo_sem_aspas(build, &ARGS), &valor_run(build, &ARGS)).unwrap();
            assert!(!mudou);
            assert_eq!(reg::valor_atual(&ch).as_deref(), Some(do_instalado.as_str()), "o Run mudou de dono");
            // Nem o valor sem aspas de outro exe.
            let sem_aspas_do_instalado = valor_antigo_sem_aspas(EXE, &ARGS);
            CURRENT_USER.create(&sb.run).unwrap().set_string("Reco", &sem_aspas_do_instalado).unwrap();
            assert!(!reg::reparar(&ch, &valor_antigo_sem_aspas(build, &ARGS), &valor_run(build, &ARGS)).unwrap());
            assert_eq!(reg::valor_atual(&ch).as_deref(), Some(sem_aspas_do_instalado.as_str()));
        }
    }
}

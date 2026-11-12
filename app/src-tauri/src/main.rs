// Sem janela de console no release do Windows.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    reco_lib::run()
}

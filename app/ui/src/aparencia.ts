// Cache local da skin e do tema (revisão adversarial da Fase 3): o config do motor é o dono (D6, `casco_skin` e
// `casco_tema`), mas ele só responde depois do `ready`. Sem o cache, quem escolheu Caderno ou Claro via a janela
// nascer em Fita no tema do sistema e trocar em seguida. O `index.html` aplica o mesmo cache antes do primeiro
// desenho (script em linha, mesma chave); a interface reconcilia quando o `config.get` chega.
import type { Skin, Tema } from "./tipos";

export const CHAVE_APARENCIA = "reco.aparencia";

const SKINS_OK = ["a", "b", "c"], TEMAS_OK = ["sistema", "claro", "escuro"];

/** O que está guardado (só valores conhecidos; o resto cai no padrão). */
export function lerAparencia(): { skin: Skin; tema: Tema } {
  let skin: Skin = "a", tema: Tema = "sistema";
  try {
    const o = JSON.parse(localStorage.getItem(CHAVE_APARENCIA) ?? "{}") as { skin?: string; tema?: string };
    if (o.skin && SKINS_OK.includes(o.skin)) skin = o.skin as Skin;
    if (o.tema && TEMAS_OK.includes(o.tema)) tema = o.tema as Tema;
  } catch { /* cache ilegível: padrão */ }
  return { skin, tema };
}

export function guardarAparencia(skin: Skin, tema: Tema): void {
  try { localStorage.setItem(CHAVE_APARENCIA, JSON.stringify({ skin, tema })); } catch { /* sem armazenamento: só perde o cache */ }
}

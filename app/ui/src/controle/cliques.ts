// Liga os gestos da janela ao controle: um ouvinte de clique por delegação (data-acao), o duplo clique da Biblioteca,
// a busca, o ganho (arrasto e teclado) e os selects de dispositivo. Todo clique dentro da janela fixa a janela do
// hover (window_pin, passo 9: o foco na janela não fixa sozinho no modo tao).
import type { App } from "../app";
import { fmtGanho, fracParaGanho, ganhoParaFrac, ganhoPorTecla } from "../ganho";
import { texto } from "../dom";
import { acaoGravar } from "./gravar";
import { acaoOpcoes, aoTrocarDispositivo } from "./opcoes";
import { recarregarBiblioteca } from "./dados";
import { acaoTelas } from "./telas";

async function despachar(app: App, b: HTMLElement): Promise<void> {
  const acao = b.dataset.acao!;
  if (acao === "aba") {
    if (b.getAttribute("aria-disabled") === "true") { app.diz("info", "av.arquivo-bloqueado"); return; }
    const tela = b.dataset.tela as App["v"]["tela"];
    app.v.tela = tela; app.v.aviso = null; app.desenhar();
    if (tela === "biblioteca" && !app.conduzido) await recarregarBiblioteca(app);
    return;
  }
  for (const f of [acaoGravar, acaoTelas, acaoOpcoes]) if (await f(app, acao, b)) return;
}

function ligarGanho(app: App): void {
  const ultimoEnvio = { mic: 0, sis: 0 }, pendente: Record<string, number | undefined> = {};
  const aplicar = (canal: "mic" | "sis", g: number) => {
    if (canal === "mic") app.v.g.ganhoMic = g; else app.v.g.ganhoSis = g;
    const inp = app.r["ganho-" + canal] as HTMLInputElement;
    inp.value = String(Math.round(ganhoParaFrac(g) * 1000));
    texto(app.r[`ganho-${canal}-valor`], fmtGanho(g, app.v.lingua));
    // ao vivo, no máximo a cada 150 ms, sem gravar config (_on_gain, reco.py:3206-3212)
    const enviar = () => { ultimoEnvio[canal] = Date.now(); pendente[canal] = undefined; void app.pedir("rec.set_gain", { [canal === "mic" ? "mic" : "sys"]: g }).catch(() => undefined); };
    const espera = 150 - (Date.now() - ultimoEnvio[canal]);
    clearTimeout(pendente[canal]);
    if (espera <= 0) enviar(); else pendente[canal] = window.setTimeout(enviar, espera);
  };
  // ao soltar, uma vez só: o motor aplica e grava com round(g, 4) (_on_gain_release, reco.py:3214-3216)
  const soltar = (canal: "mic" | "sis") => {
    const g = canal === "mic" ? app.v.g.ganhoMic : app.v.g.ganhoSis;
    void app.pedir("config.set", { changes: { [canal === "mic" ? "mic_gain" : "sys_gain"]: Math.round(g * 10000) / 10000 } }).catch((e) => app.falhou(e));
  };
  for (const canal of ["mic", "sis"] as const) {
    const inp = app.r["ganho-" + canal] as HTMLInputElement;
    inp.addEventListener("input", () => aplicar(canal, fracParaGanho(Number(inp.value) / 1000)));
    inp.addEventListener("change", () => soltar(canal));
    inp.addEventListener("keydown", (ev) => {
      const g = ganhoPorTecla(canal === "mic" ? app.v.g.ganhoMic : app.v.g.ganhoSis, ev.key);
      if (g == null) return;
      ev.preventDefault();
      aplicar(canal, g);
    });
    inp.addEventListener("keyup", (ev) => { if (ganhoPorTecla(0, ev.key) != null) soltar(canal); });
  }
}

function ligarBusca(app: App): void {
  const busca = app.r.busca as HTMLInputElement;
  let espera: number | undefined;
  busca.addEventListener("input", () => {
    clearTimeout(espera);
    espera = window.setTimeout(() => { app.v.b.busca = busca.value; app.v.b.sel = null; void recarregarBiblioteca(app); }, 250);
  });
}

export function ligarGestos(app: App): void {
  const raiz = app.raiz;
  raiz.addEventListener("pointerdown", () => { void app.be.windowPin().catch(() => undefined); }, { capture: true });
  raiz.addEventListener("click", (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-acao]");
    if (!b || !raiz.contains(b) || (b as HTMLButtonElement).disabled) return;
    void despachar(app, b).catch((e) => app.falhou(e));
  });
  raiz.addEventListener("dblclick", (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>('[data-acao="item"]');
    const item = b ? app.v.b.itens[Number(b.dataset.i)] : undefined;
    if (item) void app.be.openPath(item.path).catch((e) => app.falhou(e));
  });
  raiz.querySelectorAll<HTMLSelectElement>("select[data-campo]").forEach((sel) => sel.addEventListener("change", () => void aoTrocarDispositivo(app, sel)));
  ligarGanho(app);
  ligarBusca(app);
}

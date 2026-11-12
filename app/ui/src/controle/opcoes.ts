// Ações de Opções e da barra de título. Toda preferência vai ao motor por config.set (D6); as do casco têm o prefixo
// casco_ (F2-D16): casco_skin, casco_tema, casco_atalho. Atalho e iniciar com o Windows são comandos do Rust.
import { erroDe, type App } from "../app";
import { recarregarBiblioteca, recarregarDispositivos, aplicarConfig } from "./dados";
import type { ConfigProto, Lingua, Skin, Tema } from "../tipos";

async function gravarConfig(app: App, changes: Record<string, unknown>): Promise<ConfigProto> {
  const c = await app.pedir<ConfigProto>("config.set", { changes });
  return c;
}

/** Troca a skin sem tirar o seletor de baixo do ponteiro: o grupo Visual fica na mesma altura da lista (ou o mais
 *  perto que a rolagem deixa) e o foco vai ao botão escolhido, à vista (DESIGN.md, Condutor de estados). */
export function trocarSkin(app: App, skin: Skin): void {
  const lista = app.raiz.querySelector<HTMLElement>('[data-area="opcoes-lista"]')!;
  const grupo = app.raiz.querySelector<HTMLElement>('[data-grupo="skin"]')!;
  const altura = grupo.getBoundingClientRect().top - lista.getBoundingClientRect().top;
  app.v.skin = skin;
  app.desenhar();
  lista.scrollTop += grupo.getBoundingClientRect().top - lista.getBoundingClientRect().top - altura;
  const botao = grupo.querySelector<HTMLElement>(`[data-skin="${skin}"]`)!;
  botao.focus({ preventScroll: true });
  // só rola se o botão saiu da área visível (o scroll-padding da lista não conta: rolar por ele moveria o grupo)
  const rb = botao.getBoundingClientRect(), rl = lista.getBoundingClientRect();
  if (rb.top < rl.top || rb.bottom > rl.bottom) botao.scrollIntoView({ block: "nearest" });
}

async function escolherPasta(app: App, chave: "output_dir" | "nota_dir"): Promise<void> {
  const p = await app.be.pickFolder();
  if (!p) return;
  aplicarConfig(app, await gravarConfig(app, { [chave]: p }));
  if (chave === "output_dir") { app.v.b.pasta = app.v.o.pasta; await recarregarBiblioteca(app); }
  app.desenhar();
}

async function idioma(app: App, l: Lingua): Promise<void> {
  try {
    aplicarConfig(app, await gravarConfig(app, { language: l }));
    await app.be.definirLingua(app.v.lingua);
    app.desenhar();
  } catch (e) {
    if (erroDe(e).code === "busy") app.diz("aviso", "av.idioma-ocupado"); else app.falhou(e);
  }
}

async function atalho(app: App): Promise<void> {
  const o = app.v.o;
  try {
    o.atalho = await app.be.definirAtalho(!o.atalho);
    o.atalhoOcupado = false;
  } catch (e) {
    if (erroDe(e).code === "hotkey_taken") { o.atalhoOcupado = true; o.atalho = false; } else app.falhou(e);
  }
  app.desenhar();
}

/** Ações de Opções e da barra de título; devolve false se a ação não é daqui. */
export async function acaoOpcoes(app: App, acao: string, el: HTMLElement): Promise<boolean> {
  const v = app.v;
  const tabela: Record<string, () => Promise<unknown> | void> = {
    skin: () => { const s = el.dataset.skin as Skin; trocarSkin(app, s); return gravarConfig(app, { casco_skin: s }); },
    aparencia: () => { v.tema = el.dataset.tema as Tema; app.desenhar(); return gravarConfig(app, { casco_tema: v.tema }); },
    idioma: () => idioma(app, el.dataset.idioma === "en" ? "en" : "pt"),
    "atualizar-disp": () => recarregarDispositivos(app, true),
    "op-pasta": () => escolherPasta(app, "output_dir"),
    "op-nota": () => escolherPasta(app, "nota_dir"),
    processar: async () => { aplicarConfig(app, await gravarConfig(app, { device: el.dataset.valor })); app.desenhar(); },
    "ao-vivo": async () => { aplicarConfig(app, await gravarConfig(app, { live: !v.o.aoVivo })); app.desenhar(); },
    atalho: () => atalho(app),
    autostart: async () => { v.o.autostart = await app.be.definirAutostart(!v.o.autostart); app.desenhar(); },
    versao: () => (v.versao ? app.be.openExternal(v.versao.url) : undefined),
    minimizar: () => app.be.windowMinimize(),
    fechar: () => app.be.windowHide(),
  };
  const f = tabela[acao];
  if (!f) return false;
  await f();
  return true;
}

/** Entrada ou saída escolhida no select: grava e relê a lista (o aviso de ausente depende dela). */
export async function aoTrocarDispositivo(app: App, sel: HTMLSelectElement): Promise<void> {
  try {
    aplicarConfig(app, await gravarConfig(app, { [sel.dataset.campo!]: sel.value }));
    await recarregarDispositivos(app);
  } catch (e) { app.falhou(e); }
}

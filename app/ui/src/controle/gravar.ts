// Fluxos da tela Gravar: gravar (gravação ou nota), pausar, continuar, parar (sempre por `parar_gravacao`, para o Rust
// encadear o `auto`), as saídas depois de parar e a transcrição disparada daqui (F2-D12, F3-D8, F3-D13).
import { erroDe, type App } from "../app";
import { nomeDe } from "../dom";
import { t, textoErro } from "../i18n";
import { GRAVANDO } from "../vista";
import { zerarNiveis } from "../vu";
import type { Conclusao, EngineEvent, ErroGravar } from "../tipos";

interface Inicio { mic: { name: string; via: string }; sys: { name: string; via: string }; live: boolean }
let parandoAgora = false;
let caminho = "";

export const caminhoGravacao = (): string => caminho;

function erroDeComecar(e: unknown): ErroGravar {
  const err = erroDe(e);
  const linha = t("g.erro-linha", { erro: textoErro(err.code), detalhe: err.detail });
  return { titulo: t("g.erro-comecar"), nota: t("g.erro-comecar-nota"), linha, detalhe: `${err.code}: ${err.detail}`, saida: "opcoes" };
}

export function estadoGravando(app: App): "gravando" | "gravando-ao-vivo" | "nota-gravando" {
  const g = app.v.g;
  return g.modo === "nota" ? "nota-gravando" : g.aoVivo ? "gravando-ao-vivo" : "gravando";
}

async function comecar(app: App): Promise<void> {
  const g = app.v.g;
  try {
    const r = await app.pedir<Inicio>("rec.start", { mode: g.modo === "nota" ? "nota" : "rec" });
    g.mic = r.mic.name; g.sis = r.sys.via === "ausente" ? g.padraoSis : r.sys.name; g.sisAusente = r.sys.via === "ausente";
    g.aoVivo = r.live; g.segundos = 0; g.falas = []; app.v.ocupado = true; app.v.estado.opcoes = "durante-gravacao";
    app.ir("gravar", estadoGravando(app));
  } catch (e) {
    g.erro = erroDeComecar(e);
    app.ir("gravar", "erro");
  }
}

/** Para pelo casco (o Rust pede `rec.stop` e, se houver `auto`, a conclusão; o resultado chega por `reco-conclusao`). */
async function parar(app: App): Promise<void> {
  const g = app.v.g;
  parandoAgora = true;
  try {
    const r = await app.be.pararGravacao();
    zerarNiveis();
    depoisDeParar(app, r.path, r.duration_s, r.auto);
  } catch (e) {
    const err = erroDe(e);
    zerarNiveis();
    app.v.ocupado = false;
    if (err.code === "no_audio") { app.ir("gravar", "pronto"); app.diz("aviso", "av.nada-gravado"); return; }
    g.erro = { ...erroDeComecar(e), titulo: t("g.erro-interrompida"), nota: t("g.erro-interrompida-nota"), saida: "pasta" };
    app.ir("gravar", "erro");
  } finally {
    parandoAgora = false;
  }
}

export function depoisDeParar(app: App, path: string | null, dur: number | null, auto: string | null): void {
  const g = app.v.g;
  caminho = path ?? "";
  g.arquivo = nomeDe(caminho); if (dur != null) g.segundos = Math.round(dur);
  app.v.estado.opcoes = "normal";
  if (auto) {
    g.tarefa = auto === "nota" ? "nota" : "passada"; g.pct = null; app.v.ocupado = true;
    app.ir("gravar", "transcrevendo");
  } else {
    app.v.ocupado = false;
    app.ir("gravar", "parado");
  }
}

/** `state` do motor: acompanha o que foi feito fora da tela (bandeja) sem atropelar o que a tela está fazendo. */
export async function aoEstadoMotor(app: App, s: string): Promise<void> {
  const e = app.v.estado.gravar;
  if (s === "recording" && !GRAVANDO.has(e) && e !== "transcrevendo") { app.v.ocupado = true; app.ir("gravar", estadoGravando(app)); }
  else if (s === "recording" && e === "pausado") app.ir("gravar", estadoGravando(app));
  else if (s === "paused" && GRAVANDO.has(e) && e !== "pausado") { zerarNiveis(); app.ir("gravar", "pausado"); }
  else if (s === "stopped" && GRAVANDO.has(e) && !parandoAgora) {
    const st = await app.pedir<{ last_rec: string | null; elapsed_s: number; auto: string | null }>("state");
    zerarNiveis();
    depoisDeParar(app, st.last_rec, st.elapsed_s, st.auto);
  } else if (s === "idle" && (GRAVANDO.has(e) || e === "parado") && !parandoAgora) {
    zerarNiveis(); app.v.ocupado = false; app.ir("gravar", "pronto");
  }
}

/** Resultado da conclusão encadeada pelo Rust (nota ou passada final), mesmo quando quem parou foi a bandeja. */
export function aoConcluir(app: App, c: Conclusao): void {
  const g = app.v.g;
  app.v.ocupado = false;
  if (!c.ok) {
    app.ir("gravar", c.action === "final_pass" ? "parado" : "pronto");
    app.falhou(c.error);
    return;
  }
  const d = c.data ?? {};
  if (c.action === "nota") { g.txt = String(d.md ?? ""); g.tarefa = "nota"; app.ir("gravar", "transcricao-pronta"); return; }
  g.txt = String(d.txt ?? "");
  app.ir("gravar", "parado");
  app.diz("ok", "st.g.transcricao-pronta", { txt: nomeDe(g.txt) });
}

async function concluir(app: App, action: string): Promise<void> {
  const g = app.v.g;
  const longa = action === "transcribe" || action === "transcribe_delete";
  if (longa) { g.tarefa = "transcrever"; g.pct = null; app.v.ocupado = true; app.ir("gravar", "transcrevendo"); }
  try {
    const d = await app.pedir<Record<string, unknown>>("rec.conclude", { action }, (ev: EngineEvent) => {
      g.pct = typeof ev.pct === "number" ? ev.pct : null; app.desenhar();
    });
    app.v.ocupado = false;
    if (longa) { g.txt = String(d.txt ?? ""); app.ir("gravar", "transcricao-pronta"); return; }
    app.ir("gravar", "pronto");
    app.diz("ok", "av.excluido", { nome: nomeDe(String(d.path ?? caminho)) });
  } catch (e) {
    app.v.ocupado = false;
    if (erroDe(e).code === "cancelled") { app.ir("gravar", "pronto"); app.diz("info", "av.transcricao-parada"); return; }
    if (longa) app.ir("gravar", "pronto");
    app.falhou(e);
    throw e;
  }
}

async function salvarECopiar(app: App, copiar: boolean): Promise<void> {
  const d = await app.pedir<{ path: string }>("rec.conclude", { action: "save" });
  app.ir("gravar", "pronto");
  if (copiar) { await app.be.copyPath(d.path); app.diz("ok", "av.caminho-copiado", { path: d.path }); }
  else app.diz("ok", "av.salvo", { nome: nomeDe(d.path) });
}

async function secundario(app: App): Promise<void> {
  const e = app.v.estado.gravar;
  if (e === "parado") { await app.be.openPath(caminho); return; }
  if (e === "pausado") { await app.pedir("rec.resume"); app.ir("gravar", estadoGravando(app)); return; }
  if (GRAVANDO.has(e)) { await app.pedir("rec.pause"); zerarNiveis(); app.ir("gravar", "pausado"); }
}

/** Ações da tela Gravar; devolve false se a ação não é desta tela. */
export async function acaoGravar(app: App, acao: string, b: HTMLElement): Promise<boolean> {
  const v = app.v, e = v.estado.gravar;
  const tabela: Record<string, () => Promise<unknown> | void> = {
    principal: () => (GRAVANDO.has(e) ? parar(app) : e === "parado" ? salvarECopiar(app, true) : comecar(app)),
    secundario: () => secundario(app),
    modo: () => { v.g.modo = b.dataset.modo === "nota" ? "nota" : "gravacao"; app.desenhar(); },
    "salvar-transcrever": () => concluir(app, "transcribe").catch(() => undefined),
    "so-salvar": () => salvarECopiar(app, false),
    "transcrever-apagar": () => concluir(app, "transcribe_delete").catch(() => undefined),
    excluir: () => concluir(app, "delete").catch(() => undefined),
    "parar-transcricao": () => app.pedir("transcribe.cancel"),
    "abrir-transcricao": () => app.be.openPath(v.g.txt),
    "copiar-caminho": async () => { await app.be.copyPath(v.g.txt); app.diz("ok", "av.caminho-copiado", { path: v.g.txt }); },
    "abrir-pasta": () => app.be.revealPath(v.g.txt || v.g.pasta),
    "erro-saida": () => (v.g.erro.saida === "pasta" ? app.be.revealPath(v.g.pasta) : app.ir("opcoes", v.estado.opcoes, true)),
    detalhes: () => app.ir("gravar", "erro-detalhe"),
    "fechar-detalhe": () => app.ir("gravar", "erro"),
    "copiar-erro": async () => { await navigator.clipboard.writeText(v.g.erro.detalhe); app.diz("ok", "av.detalhes-copiados"); },
  };
  const f = tabela[acao];
  if (!f) return false;
  await f();
  return true;
}

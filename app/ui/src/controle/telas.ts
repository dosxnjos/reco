// Ações das abas Biblioteca e Arquivo (F1-D4: uma origem e duas ações, Transcrever e Converter para MP3).
import { erroDe, type App } from "../app";
import { nomeDe, pastaDe } from "../dom";
import { t, textoErro } from "../i18n";
import { recarregarBiblioteca } from "./dados";
import type { EngineEvent } from "../tipos";

const pctDe = (ev: EngineEvent): number | null => (typeof ev.pct === "number" ? ev.pct : null);

async function libTranscrever(app: App): Promise<void> {
  const b = app.v.b, item = b.sel != null ? b.itens[b.sel] : undefined;
  if (app.v.estado.biblioteca === "transcrevendo-item") { await app.pedir("transcribe.cancel"); return; }
  if (!item) return;
  b.trPath = item.path; b.trPct = null; app.v.g.ocupadoFora = true;
  app.ir("biblioteca", "transcrevendo-item");
  try {
    const d = await app.pedir<{ txt: string }>("transcribe.file", { path: item.path }, (ev) => { b.trPct = pctDe(ev); app.desenhar(); });
    b.trPath = null; app.v.estado.biblioteca = "selecionada";
    await recarregarBiblioteca(app);
    app.diz("ok", "st.a.pronto-txt", { saida: nomeDe(d.txt) });
  } catch (e) {
    b.trPath = null; app.ir("biblioteca", "selecionada");
    if (erroDe(e).code === "cancelled") app.diz("info", "av.transcricao-parada"); else app.falhou(e);
  } finally {
    app.v.g.ocupadoFora = false; app.desenhar();
  }
}

async function libResumo(app: App): Promise<void> {
  const b = app.v.b, item = b.sel != null ? b.itens[b.sel] : undefined;
  if (!item) return;
  b.resumoPath = item.path;
  app.ir("biblioteca", "resumindo");
  try {
    const d = await app.pedir<{ path: string; existia: boolean }>("resumo.ia", { path: item.path });
    app.ir("biblioteca", "selecionada");
    await app.be.openPath(d.path);
    app.diz("ok", "av.resumo-pronto", { nome: nomeDe(d.path) });
  } catch (e) {
    app.ir("biblioteca", "selecionada"); app.falhou(e);
  } finally {
    b.resumoPath = null;
  }
}

async function libExcluir(app: App): Promise<void> {
  const b = app.v.b, item = b.sel != null ? b.itens[b.sel] : undefined;
  if (!item) return;
  const d = await app.pedir<{ path: string }>("library.delete", { path: item.path });
  b.sel = null;
  await recarregarBiblioteca(app);
  app.diz("ok", "av.excluido", { nome: nomeDe(d.path) });
}

export function selecionar(app: App, i: number): void {
  const b = app.v.b;
  b.sel = i;
  const e = app.v.estado.biblioteca;
  if (e === "transcrevendo-item" || e === "resumindo") app.desenhar(); else app.ir("biblioteca", "selecionada");
}

function tipoDe(nome: string): string {
  const ext = (nome.split(".").pop() ?? "").toUpperCase();
  const video = ["MP4", "MKV", "MOV", "AVI", "WEBM", "WMV", "M4V", "FLV", "MPG", "MPEG", "TS", "3GP"].includes(ext);
  return t(video ? "a.tipo-video" : "a.tipo-audio", { ext });
}

async function arqEscolher(app: App): Promise<void> {
  const p = await app.be.pickFile("midia");
  if (!p) return;
  const nome = nomeDe(p);
  app.v.a.origem = { nome, path: p, meta: t("a.meta-sem-tamanho", { tipo: tipoDe(nome) }) };
  app.ir("arquivo", "escolhido");
}

async function arqRodar(app: App, tarefa: "transcrever" | "converter"): Promise<void> {
  const a = app.v.a, origem = a.origem;
  if (!origem) return;
  a.tarefa = tarefa; a.pct = null; a.falta = t("a.falta-espera"); app.v.g.ocupadoFora = true;
  app.ir("arquivo", tarefa === "converter" ? "convertendo" : "transcrevendo");
  try {
    const d = tarefa === "converter"
      ? await app.pedir<{ path: string }>("convert.extract_mp3", { path: origem.path }, (ev) => { a.pct = pctDe(ev); app.desenhar(); })
      : await app.pedir<{ txt: string }>("transcribe.file", { path: origem.path }, (ev) => { a.pct = pctDe(ev); app.desenhar(); });
    a.saidaPath = "txt" in d ? d.txt : d.path; a.saida = nomeDe(a.saidaPath);
    app.ir("arquivo", "pronto");
  } catch (e) {
    const err = erroDe(e);
    if (err.code === "cancelled") { app.ir("arquivo", "escolhido"); app.diz("info", "av.transcricao-parada"); return; }
    const semAudio = err.code === "no_audio_stream";
    a.erroTitulo = t(semAudio ? "a.erro-sem-audio" : "a.erro-falhou");
    a.erroNota = semAudio ? t("a.erro-sem-audio-nota") : textoErro(err.code) + (err.detail ? ` (${err.detail})` : "");
    a.erroLinha = t("a.erro-linha", { nome: origem.nome, motivo: textoErro(err.code) });
    app.ir("arquivo", "erro");
  } finally {
    app.v.g.ocupadoFora = false; app.desenhar();
  }
}

/** Ações da Biblioteca e do Arquivo; devolve false se a ação não é destas telas. */
export async function acaoTelas(app: App, acao: string, el: HTMLElement): Promise<boolean> {
  const v = app.v, sel = v.b.sel != null ? v.b.itens[v.b.sel] : undefined;
  const tabela: Record<string, () => Promise<unknown> | void> = {
    item: () => selecionar(app, Number(el.dataset.i)),
    "lib-ouvir": () => sel && app.be.openPath(sel.path),
    "lib-transcrever": () => libTranscrever(app),
    "lib-abrir": () => (sel?.txt ? app.be.openPath(sel.txt) : app.diz("info", "av.sem-texto")),
    "lib-resumo": () => libResumo(app),
    "lib-excluir": () => libExcluir(app),
    "lib-pasta": () => app.be.revealPath(v.b.pasta),
    "lib-atualizar": () => recarregarBiblioteca(app),
    "limpar-busca": () => { v.b.busca = ""; return recarregarBiblioteca(app); },
    "ir-gravar": () => app.ir("gravar", v.estado.gravar, true),
    "ir-opcoes": () => app.ir("opcoes", v.estado.opcoes, true),
    "arq-escolher": () => arqEscolher(app),
    "arq-transcrever": () => arqRodar(app, "transcrever"),
    "arq-converter": () => arqRodar(app, "converter"),
    "arq-parar": () => app.pedir("transcribe.cancel"),
    "arq-pasta": () => app.be.revealPath(v.a.origem ? v.a.origem.path : v.g.pasta),
    "arq-abrir": () => app.be.openPath(v.a.saidaPath),
    "arq-copiar": async () => { await app.be.copyPath(v.a.saidaPath); app.diz("ok", "av.caminho-copiado", { path: v.a.saidaPath }); },
  };
  const f = tabela[acao];
  if (!f) return false;
  await f();
  return true;
}

export const pastaDaOrigem = (app: App): string => (app.v.a.origem ? pastaDe(app.v.a.origem.path) : app.v.g.pasta);

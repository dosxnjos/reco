// Conversões do protocolo para a Vista (config, dispositivos, biblioteca) e as recargas que mais de uma tela pede.
import type { App } from "../app";
import { guardarAparencia } from "../aparencia";
import { duracaoCurta } from "../dom";
import { t } from "../i18n";
import type { ConfigProto, DevicesProto, ItemLib, ItemProto, Lingua, Skin, Tema } from "../tipos";

const quando = (mtime: number): string => {
  const d = new Date(mtime * 1000), p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`;
};

export const paraItem = (i: ItemProto): ItemLib =>
  ({ nome: i.name, path: i.path, quando: quando(i.mtime), duracao: duracaoCurta(i.duration_s), temTexto: !!i.txt, txt: i.txt });

/** Aplica o config do motor (D6: o motor é o dono; o casco só lê e pede config.set). */
export function aplicarConfig(app: App, c: ConfigProto): void {
  const v = app.v, cfg = c.config;
  v.lingua = (c.lang_efetivo === "en" ? "en" : "pt") as Lingua;
  v.g.pasta = c.output_dir_efetivo; v.o.pasta = c.output_dir_efetivo;
  if (!v.b.pasta) v.b.pasta = c.output_dir_efetivo;
  v.o.notaDir = typeof cfg.nota_dir === "string" ? cfg.nota_dir : "";
  v.o.processar = String(cfg.device ?? "AUTO").toUpperCase();
  v.o.aoVivo = !!cfg.live; v.g.aoVivo = !!cfg.live;
  v.o.atalho = cfg.casco_atalho === true;
  v.g.ganhoMic = Number(cfg.mic_gain ?? 1); v.g.ganhoSis = Number(cfg.sys_gain ?? 1);
  // o config do motor vence o cache local (aparencia.ts): chave ausente ou inválida é o padrão, não o que estava guardado
  v.skin = cfg.casco_skin === "b" || cfg.casco_skin === "c" ? (cfg.casco_skin as Skin) : "a";
  v.tema = cfg.casco_tema === "claro" || cfg.casco_tema === "escuro" ? (cfg.casco_tema as Tema) : "sistema";
  guardarAparencia(v.skin, v.tema);
  v.o.selMic = String(cfg.mic_device ?? "auto:console"); v.o.selSis = String(cfg.sys_device ?? "auto:console");
}

/** Nome do que vai gravar, antes da 1ª gravação. ⚠️ `console`/`comm` do motor são o NOME do padrão do Windows
 *  (`reco.scan_device_state`), não o id (defeito 2 do passo 17: a busca por id deixava Entrada e Saída vazias).
 *  Sem padrão conhecido, "Automático (padrão do Windows)". */
function nomeEscolhido(st: DevicesProto["microphone"], sel: string | null): string {
  if (sel === "auto:comm") return st.comm ?? st.console ?? t("o.auto-comm");
  if (!sel || sel.startsWith("auto")) return st.console ?? t("o.auto-console");
  return st.devs.find((d) => d.id === sel)?.name ?? st.console ?? t("o.auto-console"); // salvo que sumiu: cai no padrão
}

/** Dispositivos: listas de Opções, nomes do painel Pronto e o aviso de dispositivo ausente. */
export function aplicarDispositivos(app: App, d: DevicesProto): void {
  const v = app.v;
  v.o.mics = d.microphone.devs.map((x) => ({ id: x.id, nome: x.name }));
  v.o.siss = d.speaker.devs.map((x) => ({ id: x.id, nome: x.name }));
  v.o.selMic = d.selected.mic_device ?? "auto:console"; v.o.selSis = d.selected.sys_device ?? "auto:console";
  const padrao = d.speaker.console ?? t("o.auto-console");
  v.o.padraoSis = padrao; v.g.padraoSis = padrao;
  if (!v.ocupado) {
    v.g.mic = nomeEscolhido(d.microphone, d.selected.mic_device);
    v.g.sis = d.missing.sys ? padrao : nomeEscolhido(d.speaker, d.selected.sys_device);
    v.g.sisAusente = d.missing.sys;
  }
  v.estado.opcoes = v.ocupado ? "durante-gravacao" : d.missing.sys || d.missing.mic ? "dispositivo-ausente" : "normal";
}

export async function recarregarDispositivos(app: App, refrescar = false): Promise<void> {
  try {
    aplicarDispositivos(app, await app.pedir<DevicesProto>(refrescar ? "devices.refresh" : "devices.list"));
    app.desenhar();
  } catch (e) { app.falhou(e); }
}

/** Biblioteca: lista (ou busca) e o estado que cabe. */
export async function recarregarBiblioteca(app: App): Promise<void> {
  const b = app.v.b, q = b.busca.trim();
  try {
    const res = q
      ? await app.pedir<{ items: ItemProto[] }>("library.search", { q })
      : await app.pedir<{ folder: string; items: ItemProto[] }>("library.list");
    if ("folder" in res && typeof res.folder === "string") b.pasta = res.folder;
    const selPath = b.sel != null ? b.itens[b.sel]?.path : null;
    b.itens = res.items.map(paraItem);
    const i = selPath ? b.itens.findIndex((x) => x.path === selPath) : -1;
    b.sel = i >= 0 ? i : null;
    const e = app.v.estado.biblioteca;
    if (e === "transcrevendo-item" || e === "resumindo") { app.desenhar(); return; }
    app.v.estado.biblioteca = !b.itens.length ? (q ? "busca-sem-resultado" : "vazia") : b.sel != null ? "selecionada" : "lista";
    app.desenhar();
  } catch (e) {
    const err = e as { detail?: string };
    b.erro = err?.detail ?? String(e);
    app.ir("biblioteca", "erro");
  }
}

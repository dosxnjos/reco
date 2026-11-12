// Partida e eventos do motor: `hello` ao montar e a cada reinício (o `ready` pode se perder), config e dispositivos
// depois do pronto, e cada evento global levado à Vista (state, timer, level, live.*, rec.error, progress).
import { erroDe, type App } from "../app";
import { t, textoErro } from "../i18n";
import { aplicarCronometro } from "../render/gravar";
import { aoNivel } from "../vu";
import { aplicarConfig, recarregarBiblioteca, recarregarDispositivos } from "./dados";
import { aoConcluir, aoEstadoMotor, depoisDeParar, estadoGravando } from "./gravar";
import versaoApp from "../../../package.json";
import type { ConfigProto, EngineEvent, EngineStatus } from "../tipos";

interface Hello { engine_version: string; ready: boolean }
interface Estado { rec_state: string; elapsed_s: number; live: boolean; last_rec: string | null; auto: string | null; transcribing: boolean }

let prontoUmaVez = false;

async function aoPronto(app: App): Promise<void> {
  const v = app.v;
  try {
    aplicarConfig(app, await app.pedir<ConfigProto>("config.get"));
    await app.be.definirLingua(v.lingua);
  } catch (e) { app.falhou(e); }
  await recarregarDispositivos(app);
  if (v.estado.gravar === "motor-subindo") v.estado.gravar = "pronto";
  await ressincronizar(app);
  if (!prontoUmaVez) {
    prontoUmaVez = true;
    v.o.autostart = await app.be.autostartLigado().catch(() => false);
    const registrado = await app.be.atalhoRegistrado().catch(() => false);
    v.o.atalhoOcupado = v.o.atalho && !registrado;
    v.versao = await app.be.versaoNova().catch(() => null);
    void recarregarBiblioteca(app);
  }
  app.desenhar();
}

/** Retrato do motor (`state`) para a tela voltar a bater com ele depois de abrir ou de um reinício. */
async function ressincronizar(app: App): Promise<void> {
  const v = app.v;
  const s = await app.pedir<Estado>("state").catch(() => null);
  if (!s) return;
  v.g.segundos = Math.round(s.elapsed_s ?? 0);
  if (s.rec_state === "recording" || s.rec_state === "paused") {
    v.ocupado = true; v.g.aoVivo = s.live; v.estado.opcoes = "durante-gravacao";
    v.estado.gravar = s.rec_state === "paused" ? "pausado" : estadoGravando(app);
  } else if (s.rec_state === "stopped" && v.estado.gravar !== "transcrevendo") {
    depoisDeParar(app, s.last_rec, s.elapsed_s, null);
  }
}

export async function iniciarMotor(app: App): Promise<void> {
  try {
    const h = await app.pedir<Hello>("hello");
    app.v.o.versaoApp = versaoApp.version; app.v.o.versaoMotor = h.engine_version;
    if (h.ready) await aoPronto(app);
  } catch (e) {
    console.warn("[reco] hello falhou", e);
  }
}

function aoReady(app: App, ev: EngineEvent): void {
  if (typeof ev.error === "string" && ev.error) {
    app.v.g.erro = { titulo: t("g.erro-motor"), nota: t("g.erro-motor-nota"), linha: textoErro("unavailable"), detalhe: ev.error, saida: "pasta" };
    app.ir("gravar", "erro");
    return;
  }
  void aoPronto(app);
}

function aoErroGravacao(app: App, ev: EngineEvent): void {
  const canal = t(`canal.${String(ev.channel)}` as "canal.mic"), detalhe = String(ev.detail ?? "");
  if (!ev.fatal) { app.diz("aviso", "av.aviso-gravacao", { canal, detalhe }); return; }
  const salvar = ev.channel === "save";
  app.v.ocupado = false;
  app.v.g.erro = {
    titulo: t(salvar ? "g.erro-salvar" : "g.erro-interrompida"), nota: t(salvar ? "g.erro-salvar-nota" : "g.erro-interrompida-nota"),
    linha: t("av.aviso-gravacao", { canal, detalhe }), detalhe, saida: salvar ? "opcoes" : "pasta",
  };
  app.ir("gravar", "erro");
}

/** Evento do motor (engine-event). Com o condutor no comando, nada muda a Vista. */
export function aoEvento(app: App, ev: EngineEvent): void {
  if (app.conduzido) return;
  const g = app.v.g;
  switch (ev.event) {
    case "ready": aoReady(app, ev); return;
    case "state": void aoEstadoMotor(app, String(ev.state)).catch((e) => app.falhou(e)); return;
    case "timer": g.segundos = Number(ev.elapsed_s ?? 0); aplicarCronometro(app.v, app.r); return;
    case "level": aoNivel(ev.mic as number | null, ev.sys as number | null); return;
    case "progress": app.aoProgresso(ev) || aoProgressoSemDono(app, ev); return;
    case "live.text":
      g.falas = [...g.falas, { quem: t(ev.channel === "mic" ? "g.eu" : "g.outros"), eu: ev.channel === "mic", texto: String(ev.text ?? "") }];
      app.desenhar(); return;
    case "live.warn": app.diz("aviso", "av.ao-vivo", { texto: String(ev.text ?? "") }); return;
    case "rec.error": aoErroGravacao(app, ev); return;
  }
}

/** `progress` de pedido que não é da tela (a conclusão encadeada pelo Rust: nota ou passada final). */
function aoProgressoSemDono(app: App, ev: EngineEvent): boolean {
  if (app.v.estado.gravar !== "transcrevendo") return false;
  app.v.g.pct = typeof ev.pct === "number" ? ev.pct : null;
  app.desenhar();
  return true;
}

let caiu = false;
export function aoStatus(app: App, s: EngineStatus): void {
  if (app.conduzido) return;
  if (!s.running) { caiu = true; return; }
  if (caiu) { caiu = false; void iniciarMotor(app).then(() => app.diz("info", "av.motor-voltou")); }
}

/** Motor caiu gravando (D11): alarme visível, nunca "gravando" sem gravar; o Rust já pôs o ícone em idle. */
export function aoGravacaoInterrompida(app: App): void {
  if (app.conduzido) return;
  app.v.ocupado = false;
  app.v.g.erro = { titulo: t("g.erro-interrompida"), nota: t("g.erro-interrompida-nota"), linha: t("g.erro-interrompida"), detalhe: "", saida: "pasta" };
  app.ir("gravar", "erro", true);
}

export function ouvirMotor(app: App): void {
  void app.be.onEngineEvent((ev) => { try { aoEvento(app, ev); } catch (e) { app.falhou(erroDe(e)); } });
  void app.be.onEngineStatus((s) => aoStatus(app, s));
  void app.be.onCasco("reco-conclusao", (c) => { if (!app.conduzido) aoConcluir(app, c); });
  void app.be.onCasco("reco-versao-nova", (x) => { app.v.versao = x; app.desenhar(); });
  void app.be.onCasco("reco-gravacao-interrompida", () => aoGravacaoInterrompida(app));
  void app.be.onCasco("reco-atalho", () => {
    if (app.conduzido) return;
    app.v.tela = "gravar"; app.desenhar();
    app.r.principal.focus();
    app.diz("info", "av.atalho");
  });
}

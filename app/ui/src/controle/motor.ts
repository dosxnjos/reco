// Partida e eventos do motor: `hello` ao montar e a cada reinício (o `ready` pode se perder), config e dispositivos
// depois do pronto, e cada evento global levado à Vista (state, timer, level, live.*, rec.error, progress).
// Motor fora do ar (revisão adversarial da Fase 3): queda, `hello` que falha ou `ready` que demora viram um aviso
// visível com Gravar desabilitado (`motorFora`); o aviso some sozinho quando o motor fica pronto. O alarme do D11
// (caiu gravando) não some: a pessoa precisa ver que a gravação parou.
import { erroDe, type App } from "../app";
import { t } from "../i18n";
import { aplicarCronometro } from "../render/gravar";
import { GRAVANDO } from "../vista";
import { aoNivel, zerarNiveis } from "../vu";
import { aplicarConfig, recarregarBiblioteca, recarregarDispositivos } from "./dados";
import { aoConcluir, aoEstadoMotor, mostrarInterrompida, ressincronizar } from "./gravar";
import versaoApp from "../../../package.json";
import type { ConfigProto, EngineEvent, EngineStatus, ErroGravar } from "../tipos";

interface Hello { engine_version: string; ready: boolean }

/** Quanto a tela espera em "Preparando o motor" antes de dizer que ele está demorando (ready em 0,9 s livre e
 *  5,4 s com a máquina carregada na Fase 0; o primeiro abrir depois de instalar pode passar pelo antivírus). */
export const PRAZO_MOTOR_MS = 20_000;

let prontoUmaVez = false;

/** Mostra um aviso do motor na tela Gravar sem atropelar o que é mais importante (gravando, transcrevendo, alarme). */
function avisoDoMotor(app: App, erro: ErroGravar): void {
  const v = app.v, e = v.estado.gravar;
  v.motorFora = true;
  const trocavel = e === "motor-subindo" || e === "pronto" || e === "parado" || e === "transcricao-pronta" || (e === "erro" && v.g.erro.doMotor);
  if (trocavel) { v.g.erro = { ...erro, doMotor: true }; v.ocupado = false; app.ir("gravar", "erro"); } else app.desenhar();
}

async function aoPronto(app: App): Promise<void> {
  const v = app.v;
  v.motorFora = false;
  if (v.estado.gravar === "erro" && v.g.erro.doMotor) v.estado.gravar = "pronto";
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

function motorNaoCarregou(app: App, detalhe: string): void {
  avisoDoMotor(app, { titulo: t("g.erro-motor"), nota: t("g.erro-motor-nota"), linha: t("g.erro-motor-linha"), detalhe, saida: "pasta" });
}

export async function iniciarMotor(app: App): Promise<void> {
  window.setTimeout(() => {
    if (app.conduzido || app.v.estado.gravar !== "motor-subindo") return;
    avisoDoMotor(app, { titulo: t("g.erro-motor-lento"), nota: t("g.erro-motor-lento-nota"), linha: t("g.erro-motor-lento-linha"), detalhe: "", saida: "pasta" });
  }, PRAZO_MOTOR_MS);
  try {
    const h = await app.pedir<Hello>("hello");
    app.v.o.versaoApp = versaoApp.version; app.v.o.versaoMotor = h.engine_version;
    if (h.ready) await aoPronto(app);
  } catch (e) {
    console.warn("[reco] hello falhou", e);
    if (app.conduzido) return;
    const err = erroDe(e);
    motorNaoCarregou(app, `${err.code}: ${err.detail}`);
  }
}

function aoReady(app: App, ev: EngineEvent): void {
  if (typeof ev.error === "string" && ev.error) { motorNaoCarregou(app, ev.error); return; }
  void aoPronto(app);
}

function aoErroGravacao(app: App, ev: EngineEvent): void {
  const canal = t(`canal.${String(ev.channel)}` as "canal.mic"), detalhe = String(ev.detail ?? "");
  if (!ev.fatal) { app.diz("aviso", "av.aviso-gravacao", { canal, detalhe }); return; }
  const salvar = ev.channel === "save";
  zerarNiveis();
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
/** `engine-status`: caído, a tela avisa na hora (gravando é o alarme do D11; parado ou ocioso, o aviso do motor). */
export function aoStatus(app: App, s: EngineStatus): void {
  if (app.conduzido) return;
  if (!s.running) {
    caiu = true;
    if (GRAVANDO.has(app.v.estado.gravar)) { app.v.motorFora = true; mostrarInterrompida(app); return; }
    avisoDoMotor(app, { titulo: t("g.erro-motor-fora"), nota: t("g.erro-motor-fora-nota"), linha: t("g.erro-motor-fora-linha"), detalhe: "", saida: "pasta" });
    return;
  }
  if (caiu) { caiu = false; void iniciarMotor(app).then(() => app.diz("info", "av.motor-voltou")); }
}

/** Motor caiu gravando (D11): alarme visível, nunca "gravando" sem gravar; o Rust já pôs o ícone em idle. */
export function aoGravacaoInterrompida(app: App): void {
  if (app.conduzido) return;
  mostrarInterrompida(app);
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

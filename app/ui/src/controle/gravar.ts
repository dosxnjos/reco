// Fluxos da tela Gravar: gravar (gravação ou nota), pausar, continuar, parar (sempre por `parar_gravacao`, para o Rust
// encadear o `auto`), as saídas depois de parar e a transcrição disparada daqui (F2-D12, F3-D8, F3-D13).
// Revisão adversarial da Fase 3: um pedido curto por vez nos botões da tela (trava de pedido em voo), `busy` e
// `refused` ressincronizam pelo `state` em vez de mostrar erro, e a conclusão que chega antes da resposta do parar
// fica guardada até a tela saber que parou.
import { erroDe, type App } from "../app";
import { nomeDe, relogio } from "../dom";
import { t, textoErro } from "../i18n";
import { GRAVANDO } from "../vista";
import { zerarNiveis } from "../vu";
import type { Conclusao, EngineEvent, ErroGravar } from "../tipos";

interface Inicio { mic: { name: string; via: string }; sys: { name: string; via: string }; live: boolean }
interface Estado { rec_state: string; elapsed_s: number; live: boolean; last_rec: string | null; auto: string | null; transcribing: boolean }

let parandoAgora = false;
let comecando = false;
/** Lendo o `state` depois de um `stopped` que veio de fora (bandeja): a conclusão espera, como no parar da tela. */
let lendoParada = false;
let conclusaoGuardada: Conclusao | null = null;
let caminho = "";

export const caminhoGravacao = (): string => caminho;

/** Erro de uma ação de gravação: título, nota por código e a linha do status sem o detalhe cru (ele vai a Detalhes). */
function erroDeGravacao(e: unknown, titulo: string, nota: string, saida: ErroGravar["saida"]): ErroGravar {
  const err = erroDe(e);
  return { titulo, nota, linha: t("g.erro-linha", { titulo, erro: textoErro(err.code) }), detalhe: `${err.code}: ${err.detail}`, saida };
}

export function estadoGravando(app: App): "gravando" | "gravando-ao-vivo" | "nota-gravando" {
  const g = app.v.g;
  return g.modo === "nota" ? "nota-gravando" : g.aoVivo ? "gravando-ao-vivo" : "gravando";
}

/** Alarme do D11: a gravação parou no meio. Medidores zerados e o tempo gravado no texto (o cronômetro volta a 0). */
export function mostrarInterrompida(app: App): void {
  const g = app.v.g;
  zerarNiveis();
  app.v.ocupado = false; app.v.estado.opcoes = "normal";
  g.erro = { titulo: t("g.erro-interrompida"), nota: t("g.erro-interrompida-nota"), linha: t("g.erro-interrompida-linha", { tempo: relogio(g.segundos) }), detalhe: "", saida: "pasta" };
  app.ir("gravar", "erro", true);
}

/** Retrato do motor (`state`) para a tela voltar a bater com ele: depois de abrir, de um reinício ou de um pedido
 *  recusado (`busy`/`refused`: a tela estava atrasada em relação ao motor). */
export async function ressincronizar(app: App): Promise<void> {
  const v = app.v, e = v.estado.gravar;
  const s = await app.pedir<Estado>("state").catch(() => null);
  if (!s) return;
  if (s.rec_state === "recording" || s.rec_state === "paused") {
    v.g.segundos = Math.round(s.elapsed_s ?? 0);
    v.ocupado = true; v.g.aoVivo = s.live; v.estado.opcoes = "durante-gravacao";
    v.estado.gravar = s.rec_state === "paused" ? "pausado" : estadoGravando(app);
  } else if (s.rec_state === "stopped" && e !== "transcrevendo") {
    depoisDeParar(app, s.last_rec, s.elapsed_s, null);
  } else if (s.rec_state === "idle" && GRAVANDO.has(e)) {
    mostrarInterrompida(app); // a tela dizia gravando e o motor está ocioso: nunca seguir "gravando" (D11)
  } else if (s.rec_state === "idle" && e === "parado") {
    v.ocupado = false; app.ir("gravar", "pronto"); app.diz("info", "av.parado-salvo", { nome: v.g.arquivo });
  }
  app.desenhar();
}

async function comecar(app: App): Promise<void> {
  const g = app.v.g;
  comecando = true;
  try {
    const r = await app.pedir<Inicio>("rec.start", { mode: g.modo === "nota" ? "nota" : "rec" });
    g.mic = r.mic.name; g.sis = r.sys.via === "ausente" ? g.padraoSis : r.sys.name; g.sisAusente = r.sys.via === "ausente";
    g.aoVivo = r.live; g.segundos = 0; g.falas = []; app.v.ocupado = true; app.v.estado.opcoes = "durante-gravacao";
    app.ir("gravar", estadoGravando(app));
  } catch (e) {
    const code = erroDe(e).code;
    if (code === "busy" || code === "refused") { comecando = false; await ressincronizar(app); return; }
    const nota = t(code === "no_device" ? "g.erro-comecar-nota" : code === "unavailable" ? "g.erro-motor-nota" : "g.erro-comecar-nota-outro");
    g.erro = erroDeGravacao(e, t("g.erro-comecar"), nota, "opcoes");
    app.ir("gravar", "erro");
  } finally {
    comecando = false;
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
    const code = erroDe(e).code;
    zerarNiveis();
    // recusado ou ocupado: o motor não estava onde a tela achava (outro parar em curso): ele diz onde está
    if (code === "refused" || code === "busy") { parandoAgora = false; await ressincronizar(app); return; }
    app.v.ocupado = false;
    if (code === "no_audio") { app.ir("gravar", "pronto"); app.diz("aviso", "av.nada-gravado"); return; }
    g.erro = erroDeGravacao(e, t("g.erro-interrompida"), t("g.erro-interrompida-nota"), "pasta");
    app.ir("gravar", "erro");
  } finally {
    parandoAgora = false;
    aplicarConclusaoGuardada(app);
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

/** Gravação começada fora da tela (a bandeja grava sempre no modo `rec`, lib.rs): o `state` traz o ao vivo. */
async function gravandoDeFora(app: App): Promise<void> {
  const v = app.v;
  v.g.modo = "gravacao"; v.g.falas = []; v.ocupado = true; v.estado.opcoes = "durante-gravacao";
  const s = await app.pedir<Estado>("state").catch(() => null);
  if (s) { v.g.aoVivo = s.live; v.g.segundos = Math.round(s.elapsed_s ?? 0); }
  app.ir("gravar", estadoGravando(app));
}

/** `state` do motor: acompanha o que foi feito fora da tela (bandeja) sem atropelar o que a tela está fazendo. */
export async function aoEstadoMotor(app: App, s: string): Promise<void> {
  const e = app.v.estado.gravar;
  if (s === "recording" && comecando) return; // a resposta do rec.start desenha (com o modo e os nomes certos)
  if (s === "recording" && !GRAVANDO.has(e) && e !== "transcrevendo") await gravandoDeFora(app);
  else if (s === "recording" && e === "pausado") app.ir("gravar", estadoGravando(app));
  else if (s === "paused" && GRAVANDO.has(e) && e !== "pausado") { zerarNiveis(); app.ir("gravar", "pausado"); }
  else if (s === "stopped" && GRAVANDO.has(e) && !parandoAgora) {
    lendoParada = true;
    try {
      const st = await app.pedir<Estado>("state");
      zerarNiveis();
      depoisDeParar(app, st.last_rec, st.elapsed_s, st.auto);
    } finally {
      lendoParada = false;
      aplicarConclusaoGuardada(app);
    }
  } else if (s === "idle" && (GRAVANDO.has(e) || e === "parado") && !parandoAgora) {
    zerarNiveis(); app.v.ocupado = false; app.ir("gravar", "pronto");
  }
}

function aplicarConclusaoGuardada(app: App): void {
  const c = conclusaoGuardada;
  conclusaoGuardada = null;
  if (c) aoConcluir(app, c);
}

/** Resultado da conclusão encadeada pelo Rust (nota ou passada final), mesmo quando quem parou foi a bandeja. O
 *  evento e a resposta do `parar_gravacao` não têm ordem garantida: chegando antes, espera a tela saber que parou. */
export function aoConcluir(app: App, c: Conclusao): void {
  if (parandoAgora || lendoParada) { conclusaoGuardada = c; return; }
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

// Trava de pedido em voo: enquanto um gravar, parar, pausar, salvar ou excluir não respondeu, outro clique nesses
// botões é ignorado (com o motor real, parar leva o tempo de drenar e fechar o MP3). As longas (transcrever) mudam a
// tela na hora e liberam o Parar transcrição, então ficam fora. Com o condutor no comando o backend falso congela e
// nunca responde: a trava não vale ali.
const COM_TRAVA = new Set(["principal", "secundario", "so-salvar", "excluir"]);
let emVoo = false;

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
  const travar = COM_TRAVA.has(acao) && !app.conduzido;
  if (travar && emVoo) return true;
  if (travar) emVoo = true;
  try {
    await f();
  } finally {
    if (travar) emVoo = false;
  }
  return true;
}

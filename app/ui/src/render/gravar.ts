// Tela Gravar: cronômetro, rótulo do estado, ações (principal e secundário no mesmo lugar), modo e painel.
import { t, type Chave } from "../i18n";
import { usar } from "../icones";
import { camada, desabilitar, marcar, relogio, texto, variavel, nomeDe, type Refs } from "../dom";
import { GRAVANDO } from "../vista";
import { fmtGanho, ganhoParaFrac } from "../ganho";
import { rolarAoVivo, seguirFala, sincronizarFalas } from "../vivo";
import type { Sinal, Vista } from "../tipos";

type Rec = [Sinal, string, Chave];
const REC: Record<string, Rec> = {
  "motor-subindo": ["espera", "hourglass", "rec.preparando"], "pronto": ["info", "circle", "rec.pronto"],
  "gravando": ["rec", "circle", "rec.gravando"], "gravando-ao-vivo": ["rec", "circle", "rec.ao-vivo"], "nota-gravando": ["rec", "circle", "rec.nota"],
  "pausado": ["info", "pause", "rec.pausado"], "parado": ["info", "square", "rec.parado"], "transcrevendo": ["espera", "file-text", "rec.transcrevendo"],
  "transcricao-pronta": ["ok", "circle-check", "rec.texto-pronto"], "erro": ["erro", "circle-alert", "rec.erro"], "erro-detalhe": ["erro", "circle-alert", "rec.erro"],
};
const VARIANTE: Record<string, string> = {
  "motor-subindo": "motor", "pronto": "pronto", "gravando": "gravando", "gravando-ao-vivo": "aovivo", "nota-gravando": "nota", "pausado": "gravando",
  "parado": "parado", "transcrevendo": "transcrevendo", "transcricao-pronta": "pronta", "erro": "erro", "erro-detalhe": "erro",
};

function principal(e: string, nota: boolean): [string, string, Chave, boolean] {
  if (e === "motor-subindo") return ["grava", "circle", nota ? "g.gravar-nota" : "g.gravar", true];
  if (GRAVANDO.has(e)) return ["acao", "square", "g.parar", false];
  if (e === "parado") return ["acao", "copy", "g.salvar-copiar", false];
  if (e === "transcrevendo") return ["grava", "circle", nota ? "g.gravar-nota" : "g.gravar", true];
  return ["grava", "circle", nota ? "g.gravar-nota" : "g.gravar", false];
}

// Quando o botão principal trocou de papel (Gravar, Parar, Salvar…) pela última vez: um clique cujo aperto começou
// antes disso foi mirado no papel antigo e é ignorado (controle/cliques.ts; revisão adversarial da Fase 3).
let papel = "", papelDesde = 0;
export const principalTrocouEm = (): number => papelDesde;

function acoes(v: Vista, r: Refs, raiz: HTMLElement, e: string, nota: boolean): void {
  const [tom, icone, rotulo, travado] = principal(e, nota);
  if (rotulo !== papel) { papel = rotulo; papelDesde = performance.now(); }
  // motor fora do ar: Gravar (e Salvar, que também pede ao motor) desabilitado; o status diz o motivo
  const semMotor = v.motorFora && !GRAVANDO.has(e);
  marcar(r.principal, "data-tom", tom); usar(r["principal-icone"], icone); texto(r["principal-texto"], t(rotulo)); desabilitar(r.principal, travado || semMotor);
  const pausa = e === "pausado", parado = e === "parado";
  usar(r["secundario-icone"], pausa || parado ? "play" : "pause");
  texto(r["secundario-texto"], t(pausa ? "g.continuar" : parado ? "g.ouvir" : "g.pausar"));
  desabilitar(r.secundario, !(GRAVANDO.has(e) || parado));
  const livre = e === "pronto" || e === "transcricao-pronta" || e === "erro";
  raiz.querySelectorAll<HTMLButtonElement>(".modo-op").forEach((b) => {
    marcar(b, "aria-checked", String(b.dataset.modo === (nota ? "nota" : "gravacao")));
    desabilitar(b, !livre || (b.dataset.modo === "nota" && v.g.ocupadoFora));
  });
}

function medidores(v: Vista, r: Refs, nota: boolean): void {
  r["medidor-sis"].toggleAttribute("data-fora", nota);
  for (const [canal, g] of [["mic", v.g.ganhoMic], ["sis", v.g.ganhoSis]] as const) {
    const inp = r["ganho-" + canal] as HTMLInputElement;
    if (document.activeElement !== inp) inp.value = String(Math.round(ganhoParaFrac(g) * 1000));
    texto(r[`ganho-${canal}-valor`], fmtGanho(g, v.lingua));
  }
}

function painel(v: Vista, r: Refs, e: string): void {
  const g = v.g, variante = VARIANTE[e];
  camada(r.aovivo.parentElement!, variante);
  texto(r["info-mic"], g.mic); texto(r["info-sis"], g.sis); texto(r["info-pasta"], g.pasta);
  texto(r["grav-pasta"], g.pasta); texto(r["grav-mic"], g.mic); texto(r["grav-sis"], g.sisAusente ? g.padraoSis : g.sis);
  texto(r["tr-arquivo"], g.arquivo);
  texto(r["tr-tarefa"], t(`g.tarefa-${g.tarefa}`));
  texto(r["tr-pct"], g.pct == null ? "…" : `${g.pct}%`);
  variavel(r["tr-barra"], "--progresso", `${g.pct ?? 0}%`);
  texto(r["pronta-titulo"], t(g.tarefa === "nota" ? "g.pronta-nota" : "g.pronta-transcricao"));
  texto(r["pronta-arquivo"], nomeDe(g.txt));
  texto(r["erro-titulo"], g.erro.titulo); texto(r["erro-nota"], g.erro.nota);
  const pasta = g.erro.saida === "pasta";
  usar(r["erro-botao-icone"], pasta ? "folder-open" : "settings-2");
  texto(r["erro-botao-texto"], t(pasta ? "g.abrir-pasta" : "g.ver-dispositivos"));
  sincronizarFalas(r.aovivo, g.falas);
  if (variante === "aovivo") rolarAoVivo(r.aovivo);
  seguirFala(r);
}

export function aplicarGravar(v: Vista, r: Refs, raiz: HTMLElement): void {
  const e = v.estado.gravar, [sinal, icone, rotulo] = REC[e];
  marcar(r.rec, "data-sinal", sinal); usar(r["rec-icone"], icone); texto(r["rec-texto"], t(rotulo));
  r.cronometro.toggleAttribute("data-gravando", sinal === "rec");
  const rodando = GRAVANDO.has(e) || e === "parado";
  texto(r.crono, relogio(rodando ? v.g.segundos : 0));
  const nota = e === "nota-gravando" || (v.g.modo === "nota" && !GRAVANDO.has(e));
  acoes(v, r, raiz, e, nota);
  medidores(v, r, nota);
  painel(v, r, e);
}

/** Só o cronômetro (evento timer, 1/s): nenhum outro nó é tocado. */
export function aplicarCronometro(v: Vista, r: Refs): void {
  const e = v.estado.gravar;
  texto(r.crono, relogio(GRAVANDO.has(e) || e === "parado" ? v.g.segundos : 0));
}

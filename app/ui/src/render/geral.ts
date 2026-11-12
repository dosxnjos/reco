// Partes comuns a todas as telas: skin e tema no <html>, textos, barra de título, abas, status e detalhe do erro.
import { aplicarTextos, definirLingua, t } from "../i18n";
import { usar } from "../icones";
import { ativar, esconder, marcar, texto, titulo, type Refs } from "../dom";
import { ICONE_SINAL, linhaStatus } from "./status";
import type { Vista } from "../tipos";

let linguaAplicada = "";

export function aplicarGeral(v: Vista, r: Refs, raiz: HTMLElement): void {
  const html = document.documentElement;
  marcar(html, "data-direcao", v.skin);
  if (v.tema === "sistema") html.removeAttribute("data-tema"); else marcar(html, "data-tema", v.tema);
  definirLingua(v.lingua);
  if (linguaAplicada !== v.lingua) {
    linguaAplicada = v.lingua;
    html.lang = v.lingua === "en" ? "en" : "pt-BR";
  }
  aplicarTextos(raiz);
  esconder(r.versao, !v.versao);
  texto(r["versao-texto"], v.versao ? t("titulo.versao-nova", { tag: v.versao.tag }) : "");
  titulo(r.versao, v.versao ? t("titulo.versao-dica", { tag: v.versao.tag }) : "");
  raiz.querySelectorAll<HTMLButtonElement>(".aba").forEach((a) => {
    marcar(a, "aria-selected", String(a.dataset.tela === v.tela));
    a.tabIndex = 0;
    if (a.dataset.tela !== "arquivo") return;
    marcar(a, "aria-disabled", String(v.ocupado));
    titulo(a, v.ocupado ? t("aba.bloqueada") : "");
    usar(r["aba-arquivo-icone"], v.ocupado ? "lock" : "file-audio");
  });
  raiz.querySelectorAll("[data-tela-painel]").forEach((p) => ativar(p, (p as HTMLElement).dataset.telaPainel === v.tela));
}

export function aplicarStatus(v: Vista, r: Refs, raiz: HTMLElement): void {
  const [sinal, txt] = linhaStatus(v);
  const area = raiz.querySelector<HTMLElement>('[data-area="status"]')!;
  marcar(area, "data-sinal", sinal);
  usar(r["status-icone"], ICONE_SINAL[sinal]);
  texto(r["status-texto"], txt);
  titulo(area, txt);
  const erro = v.tela === "gravar" && v.estado.gravar === "erro" && !v.aviso;
  esconder(r["status-detalhes"], !(erro && v.g.erro.detalhe));
  const det = v.tela === "gravar" && v.estado.gravar === "erro-detalhe";
  ativar(r.detalhe, det);
  texto(r["detalhe-texto"], v.g.erro.detalhe);
  raiz.querySelectorAll<HTMLElement>(".tela").forEach((p) => { p.inert = det; });
}

// i18n por código: `t("chave", {x})` devolve o texto da língua atual com `{x}` trocado.
import { en } from "./en";
import { pt, type Chave } from "./pt";
import type { Lingua } from "../tipos";

export type { Chave };
const DIC: Record<Lingua, Record<Chave, string>> = { pt, en };
let atual: Lingua = "pt";

export function definirLingua(l: Lingua): void { atual = l; }
export function lingua(): Lingua { return atual; }

export function t(chave: Chave, vars: Record<string, string | number> = {}): string {
  const base = DIC[atual][chave] ?? pt[chave] ?? chave;
  return base.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? String(vars[k]) : m));
}

/** Código de erro do protocolo (ou do casco) para texto; código desconhecido mostra o próprio código. */
export function textoErro(code: string): string {
  const chave = ("erro." + code) as Chave;
  return chave in pt ? t(chave) : code;
}

/** Aplica os textos estáticos marcados no HTML (data-t, data-t-aria, data-t-title, data-t-ph). */
export function aplicarTextos(raiz: ParentNode): void {
  raiz.querySelectorAll<HTMLElement>("[data-t]").forEach((e) => troca(e, t(e.dataset.t as Chave)));
  raiz.querySelectorAll<HTMLElement>("[data-t-aria]").forEach((e) => e.setAttribute("aria-label", t(e.dataset.tAria as Chave)));
  raiz.querySelectorAll<HTMLElement>("[data-t-title]").forEach((e) => { e.title = t(e.dataset.tTitle as Chave); });
  raiz.querySelectorAll<HTMLInputElement>("[data-t-ph]").forEach((e) => { e.placeholder = t(e.dataset.tPh as Chave); });
}

function troca(e: HTMLElement, v: string): void { if (e.textContent !== v) e.textContent = v; }

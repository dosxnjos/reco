// Ganho por canal: porte de gain_to_frac/frac_to_gain/fmt_gain (reco.py:2748-2763). Metade esquerda do controle vai
// de 0× a 1× (atenua), a direita de 1× a 10× (reforça); o valor encaixa em passos de 0,5.
import type { Lingua } from "./tipos";

export const GANHO_MIN = 0, GANHO_UNIDADE = 1, GANHO_MAX = 10, GANHO_PASSO = 0.5;

export function ganhoParaFrac(g: number): number {
  const x = Math.max(GANHO_MIN, Math.min(g, GANHO_MAX));
  if (x <= GANHO_UNIDADE) return 0.5 * (x - GANHO_MIN) / (GANHO_UNIDADE - GANHO_MIN);
  return 0.5 + 0.5 * (x - GANHO_UNIDADE) / (GANHO_MAX - GANHO_UNIDADE);
}

export function fracParaGanho(f: number): number {
  const x = Math.max(0, Math.min(f, 1));
  const g = x <= 0.5 ? GANHO_MIN + (x / 0.5) * (GANHO_UNIDADE - GANHO_MIN) : GANHO_UNIDADE + ((x - 0.5) / 0.5) * (GANHO_MAX - GANHO_UNIDADE);
  const passo = Math.round(g / GANHO_PASSO) * GANHO_PASSO;
  return Math.max(GANHO_MIN, Math.min(passo, GANHO_MAX));
}

/** "1,0×" em português (vírgula, como o fmt_gain), "1.0×" em inglês. */
export function fmtGanho(g: number, lingua: Lingua): string {
  const s = g.toFixed(1);
  return (lingua === "pt" ? s.replace(".", ",") : s) + "×";
}

/** Passo do teclado (setas ±0,5; Page Up/Down ±2; Home/End nos extremos), ou null se a tecla não mexe no ganho. */
export function ganhoPorTecla(g: number, tecla: string): number | null {
  const d: Record<string, number> = { ArrowRight: GANHO_PASSO, ArrowUp: GANHO_PASSO, ArrowLeft: -GANHO_PASSO, ArrowDown: -GANHO_PASSO, PageUp: 2, PageDown: -2 };
  if (tecla === "Home") return GANHO_MIN;
  if (tecla === "End") return GANHO_MAX;
  if (!(tecla in d)) return null;
  return Math.max(GANHO_MIN, Math.min(GANHO_MAX, Math.round((g + d[tecla]) / GANHO_PASSO) * GANHO_PASSO));
}

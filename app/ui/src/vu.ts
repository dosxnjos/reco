// Medidores (VU): o evento `level` (50 ms) só guarda o último valor; um laço de requestAnimationFrame escreve o nível
// e o pico como variáveis CSS nas barras que já existem. Nenhum nó é criado por evento (passo 12).
// Mesma régua do VU do app velho (reco.py:2772-2799): pico = max(pico × 0,82, min(rms × 3, 1)) a cada nível.
import { variavel, type Refs } from "./dom";

const DECAI = 0.82, PICO_DECAI = 0.97;
const canais = { mic: { nivel: 0, pico: 0, novo: 0 }, sis: { nivel: 0, pico: 0, novo: 0 } };
let ativo = false, quadro = 0;

/** Valor do evento `level` (RMS já com o ganho; `null` = sem bloco do canal na janela). */
export function aoNivel(mic: number | null, sis: number | null): void {
  canais.mic.novo = mic ?? 0;
  canais.sis.novo = sis ?? 0;
  for (const c of Object.values(canais)) {
    c.nivel = Math.max(c.nivel * DECAI, Math.min(c.novo * 3, 1));
    c.pico = Math.max(c.pico * PICO_DECAI, c.nivel);
  }
}

/** Zera os medidores (fora da gravação o motor não manda nível). */
export function zerarNiveis(): void {
  for (const c of Object.values(canais)) { c.nivel = 0; c.pico = 0; c.novo = 0; }
}

/** Fixa um nível (o condutor de estados mostra medidores parados com algo dentro). */
export function fixarNiveis(mic: number, sis: number): void {
  canais.mic.nivel = mic; canais.mic.pico = Math.min(0.97, mic + 0.08);
  canais.sis.nivel = sis; canais.sis.pico = Math.min(0.97, sis + 0.08);
}

function pintar(r: Refs): void {
  for (const [nome, c] of Object.entries(canais)) {
    const barra = r["barra-" + nome];
    variavel(barra, "--nivel", Math.round(c.nivel * 100) + "%");
    variavel(barra, "--pico", Math.min(97, Math.round(c.pico * 100)) + "%");
    variavel(barra, "--pico-op", c.pico > 0.04 ? "1" : "0");
  }
}

/** Liga o laço de desenho (uma vez). */
export function ligarMedidores(r: Refs): void {
  if (ativo) return;
  ativo = true;
  const passo = () => { pintar(r); quadro = requestAnimationFrame(passo); };
  quadro = requestAnimationFrame(passo);
}

export function desligarMedidores(): void { ativo = false; cancelAnimationFrame(quadro); }

/** Pinta já (sem esperar o próximo quadro): o condutor mede logo depois de definir. */
export function pintarAgora(r: Refs): void { pintar(r); }

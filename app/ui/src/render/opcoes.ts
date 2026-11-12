// Tela Opções: Visual e Aparência no topo, dispositivos, pastas, Processar em, ao vivo, idioma, atalho, iniciar com o
// Windows e versão. Durante a gravação, dispositivos e pastas ficam bloqueados com o motivo (estado durante-gravacao).
import { t } from "../i18n";
import { usar } from "../icones";
import { desabilitar, esconder, marcar, texto, titulo, type Refs } from "../dom";
import type { Disp, Vista } from "../tipos";

/** Opções do select: Automático (padrão do Windows), Automático (comunicação) e os dispositivos; reusa os <option>. */
function preencher(sel: HTMLSelectElement, devs: Disp[], escolhido: string): void {
  const linhas: [string, string][] = [["auto:console", t("o.auto-console")], ["auto:comm", t("o.auto-comm")], ...devs.map((d) => [d.id, d.nome] as [string, string])];
  while (sel.options.length > linhas.length) sel.remove(sel.options.length - 1);
  while (sel.options.length < linhas.length) sel.add(new Option(""));
  linhas.forEach(([valor, rotulo], i) => {
    const o = sel.options[i];
    if (o.value !== valor) o.value = valor;
    texto(o, rotulo);
  });
  if (sel.value !== escolhido) sel.value = linhas.some(([x]) => x === escolhido) ? escolhido : "auto:console";
  titulo(sel, sel.options[sel.selectedIndex]?.textContent ?? "");
}

function chave(botao: HTMLElement, rotulo: HTMLElement, ligado: boolean): void {
  marcar(botao, "aria-checked", String(ligado));
  texto(rotulo, t(ligado ? "o.ligado" : "o.desligado"));
}

export function aplicarOpcoes(v: Vista, r: Refs, raiz: HTMLElement): void {
  const e = v.estado.opcoes, o = v.o, durante = e === "durante-gravacao";
  preencher(r["sel-mic"] as HTMLSelectElement, o.mics, o.selMic);
  preencher(r["sel-sis"] as HTMLSelectElement, o.siss, o.selSis);
  [r["sel-mic"], r["sel-sis"], r["atualizar-disp"], r["op-pasta-btn"], r["op-nota-btn"]].forEach((x) => desabilitar(x, durante));
  texto(r["op-pasta"], o.pasta); titulo(r["op-pasta"], o.pasta);
  const nota = o.notaDir || t("o.nota-igual");
  texto(r["op-nota"], nota); titulo(r["op-nota"], nota);
  const ajuda = r["ajuda-dispositivo"];
  if (e === "normal") { ajuda.removeAttribute("data-sinal"); texto(r["ajuda-dispositivo-texto"], ""); titulo(ajuda, ""); }
  else {
    marcar(ajuda, "data-sinal", durante ? "info" : "aviso");
    usar(r["ajuda-dispositivo-icone"], durante ? "lock" : "triangle-alert");
    const msg = durante ? t("o.bloqueado") : t("o.ausente", { padrao: o.padraoSis });
    texto(r["ajuda-dispositivo-texto"], msg); titulo(ajuda, msg);
  }
  raiz.querySelectorAll<HTMLElement>('[data-acao="processar"]').forEach((b) => marcar(b, "aria-pressed", String(b.dataset.valor === o.processar)));
  chave(r["ao-vivo"], r["ao-vivo-texto"], o.aoVivo);
  chave(r.atalho, r["atalho-texto"], o.atalho);
  chave(r.autostart, r["autostart-texto"], o.autostart);
  const ocupado = r["ajuda-atalho"];
  ocupado.toggleAttribute("data-sinal", o.atalhoOcupado);
  if (o.atalhoOcupado) marcar(ocupado, "data-sinal", "aviso");
  texto(r["ajuda-atalho-texto"], o.atalhoOcupado ? t("erro.hotkey_taken") : "Ctrl+Shift+R");
  raiz.querySelectorAll<HTMLElement>('[data-acao="aparencia"]').forEach((b) => marcar(b, "aria-pressed", String(b.dataset.tema === v.tema)));
  raiz.querySelectorAll<HTMLElement>('[data-acao="idioma"]').forEach((b) => marcar(b, "aria-pressed", String(b.dataset.idioma === v.lingua)));
  raiz.querySelectorAll<HTMLElement>('[data-acao="skin"]').forEach((b) => marcar(b, "aria-pressed", String(b.dataset.skin === v.skin)));
  texto(r["op-versao"], t("o.versao-texto", { app: o.versaoApp, motor: o.versaoMotor }));
  esconder(r["op-versao-btn"], !v.versao);
  if (v.versao) texto(r["op-versao-btn"].firstElementChild!, t("o.baixar-versao", { tag: v.versao.tag }));
}

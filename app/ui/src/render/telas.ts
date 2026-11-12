// Telas Biblioteca e Arquivo. A lista da Biblioteca reaproveita os botões de item (cria só os que faltam, nunca
// refaz a lista inteira); a raiz da janela não muda.
import { t } from "../i18n";
import { usar } from "../icones";
import { camada, desabilitar, marcar, texto, titulo, variavel, type Refs } from "../dom";
import type { ItemLib, Vista } from "../tipos";

function garantirItens(corpo: HTMLElement, n: number): void {
  while (corpo.childElementCount > n) corpo.lastElementChild!.remove();
  while (corpo.childElementCount < n) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "item lista-grade"; b.setAttribute("role", "option"); b.dataset.acao = "item";
    b.innerHTML = '<span class="corta item-nome"></span><span class="item-dur" data-num></span>'
      + '<span class="item-texto"><svg class="ic" data-lucide="file-check"><use href="#i-file-check"/></svg><span data-num></span></span>';
    corpo.append(b);
  }
}

function aplicarItem(b: HTMLButtonElement, it: ItemLib, i: number, v: Vista): void {
  b.dataset.i = String(i);
  texto(b.children[0], it.nome);
  texto(b.children[1], it.duracao);
  titulo(b, `${it.nome} (${it.quando})`);
  marcar(b, "aria-selected", String(i === v.b.sel));
  const marca = b.children[2];
  usar(marca.firstElementChild!, it.temTexto ? "file-check" : "file-minus");
  const andando = v.estado.biblioteca === "transcrevendo-item" && it.path === v.b.trPath;
  texto(marca.lastElementChild!, andando ? `${v.b.trPct ?? 0}%` : t(it.temTexto ? "b.sim" : "b.nao"));
}

export function aplicarBiblioteca(v: Vista, r: Refs, raiz: HTMLElement): void {
  const e = v.estado.biblioteca, b = v.b;
  const capa = ({ vazia: "lib-vazia", "busca-sem-resultado": "lib-sem", erro: "lib-erro" } as Record<string, string>)[e] ?? "";
  camada(raiz.querySelector('[data-area="lista"]')!, capa);
  r["lista-corpo"].inert = !!capa;
  texto(r["vazia-texto"], t("b.vazia", { pasta: b.pasta }));
  texto(r["sem-texto"], t("b.sem", { busca: b.busca }));
  const busca = r.busca as HTMLInputElement;
  if (document.activeElement !== busca && busca.value !== b.busca) busca.value = b.busca;
  texto(r["busca-conta"], capa ? "0" : String(b.itens.length));
  const corpo = r["lista-corpo"];
  garantirItens(corpo, b.itens.length);
  b.itens.forEach((it, i) => aplicarItem(corpo.children[i] as HTMLButtonElement, it, i, v));
  const sel = b.sel != null ? b.itens[b.sel] : undefined;
  raiz.querySelectorAll<HTMLButtonElement>("[data-precisa-item]").forEach((x) => desabilitar(x, !sel || !!capa));
  const trAndando = e === "transcrevendo-item";
  usar(r["lib-transcrever-icone"], trAndando ? "square" : "file-text");
  texto(r["lib-transcrever-texto"], t(trAndando ? "b.parar" : "b.transcrever"));
  if (sel && !trAndando && (v.ocupado || v.g.ocupadoFora)) desabilitar(r["lib-transcrever"], true);
  if (sel && !sel.temTexto) { desabilitar(r["lib-abrir"], true); desabilitar(r["lib-resumo"], true); }
  texto(r["lib-resumo-texto"], t(e === "resumindo" ? "b.resumindo" : "b.resumo"));
  if (e === "resumindo") desabilitar(r["lib-resumo"], true);
}

export function aplicarArquivo(v: Vista, r: Refs, raiz: HTMLElement): void {
  const e = v.estado.arquivo, a = v.a;
  const escolhido = e !== "nada-escolhido", andando = e === "transcrevendo" || e === "convertendo";
  camada(raiz.querySelector('[data-area="origem"]')!, escolhido ? "arq-escolhido" : "arq-nada");
  texto(r["arq-nome"], a.origem?.nome ?? ""); titulo(r["arq-nome"], a.origem?.nome ?? "");
  texto(r["arq-meta"], a.origem?.meta ?? "");
  const travado = !escolhido || andando || e === "erro" || v.ocupado;
  desabilitar(r["arq-transcrever"], travado);
  desabilitar(r["arq-converter"], travado);
  desabilitar(r["arq-parar"], !(andando && a.tarefa === "transcrever"));
  desabilitar(r["arq-trocar"], andando);
  desabilitar(r["arq-escolher"], v.ocupado);
  const variante = andando ? "arq-andando" : ({ pronto: "arq-pronto", erro: "arq-erro" } as Record<string, string>)[e] ?? "arq-ocioso";
  camada(raiz.querySelector('[data-area="progresso"]')!, variante);
  const conv = a.tarefa === "converter";
  texto(r["arq-tarefa"], t(conv ? "a.convertendo" : "a.transcrevendo"));
  texto(r["arq-pct"], a.pct == null ? "…" : `${a.pct}%`);
  variavel(r["arq-barra"], "--progresso", `${a.pct ?? 0}%`);
  texto(r["arq-falta"], a.falta);
  texto(r["arq-saida"], a.saida);
  usar(r["arq-abrir-icone"], conv ? "play" : "file-text");
  texto(r["arq-abrir-texto"], t(conv ? "a.abrir-mp3" : "a.abrir-transcricao"));
  texto(r["arq-erro-titulo"], a.erroTitulo);
  texto(r["arq-erro-nota"], a.erroNota);
}

// Painel ao vivo: falas como parágrafos reaproveitados (só cresce quando chega fala nova), rolagem que para no começo
// de uma linha (a 1ª linha à vista sai inteira, rolarAoVivo da vitrine) e o marcador de continuação no respiro.
import { ativar, texto, type Refs } from "./dom";
import type { Fala } from "./tipos";

const MAX_FALAS = 300;

/** Deixa o painel com um parágrafo por fala (reusa os que existem; cria só os que faltam). */
export function sincronizarFalas(box: HTMLElement, falas: Fala[]): void {
  const lista = falas.slice(-MAX_FALAS);
  while (box.childElementCount > lista.length) box.lastElementChild!.remove();
  while (box.childElementCount < lista.length) {
    const p = document.createElement("p");
    const quem = document.createElement("span"), fala = document.createElement("span");
    quem.className = "quem";
    p.append(quem, fala);
    box.append(p);
  }
  lista.forEach((f, i) => {
    const p = box.children[i] as HTMLElement, ultima = i === lista.length - 1;
    texto(p.firstElementChild!, f.quem);
    if (p.dataset.quem !== (f.eu ? "eu" : "outros")) p.dataset.quem = f.eu ? "eu" : "outros";
    const corpo = p.lastElementChild as HTMLElement;
    texto(corpo, f.texto);
    corpo.className = ultima && f.texto.endsWith("…") ? "rascunho" : "";
  });
}

/** Mostra o fim, com o topo no começo de uma linha (nunca meia linha cortada em cima). Se o fim não cai numa linha,
 *  sobra um respiro embaixo (menos de uma linha); o respiro de baixo pode encolher até 4 px para caber mais uma em cima. */
export function rolarAoVivo(box: HTMLElement): void {
  box.style.paddingBottom = "";
  const cs = getComputedStyle(box), respiro = parseFloat(cs.paddingTop), L = parseFloat(cs.lineHeight), baixo = parseFloat(cs.paddingBottom);
  const max = box.scrollHeight - box.clientHeight;
  if (max <= 0) { box.scrollTop = 0; return; }
  const fim = max - Math.max(0, baixo - 4);
  const topos: number[] = [];
  for (const p of box.children as HTMLCollectionOf<HTMLElement>) {
    for (let k = 0; k < Math.round(p.offsetHeight / L); k++) topos.push(p.offsetTop - respiro + k * L);
  }
  const alvo = topos.find((y) => y >= fim - 0.5);
  if (alvo === undefined) { box.scrollTop = max; return; }
  if (alvo > max) box.style.paddingBottom = (baixo + alvo - max) + "px";
  box.scrollTop = alvo;
}

/** Se a 1ª linha à vista é meio de uma fala, o respiro de cima diz de quem é. */
export function seguirFala(r: Refs): void {
  const box = r.aovivo, respiro = parseFloat(getComputedStyle(box).paddingTop), topo = box.scrollTop + respiro;
  const filhos = [...box.children] as HTMLElement[];
  const p = box.hasAttribute("data-ativa") && box.scrollTop > 0.5 ? filhos.find((x) => x.offsetTop + x.offsetHeight > topo + 0.5) : undefined;
  const meio = !!p && p.offsetTop < topo - 0.5;
  if (meio) texto(r["vivo-segue-quem"], p.firstElementChild!.textContent ?? "");
  ativar(r["vivo-segue"], meio);
}

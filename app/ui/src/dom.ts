// Referências e ajudantes de atualização pontual: a árvore da janela nasce no index.html e nunca é refeita; daqui só
// se troca textContent, atributo, propriedade ou variável CSS (proibido replaceChildren na raiz, passo 11).

export type Refs = Record<string, HTMLElement>;

export const janela = (): HTMLElement => document.querySelector<HTMLElement>('[data-area="janela"]')!;

/** Junta os [data-ref] da janela por nome; falta de um nome é erro de montagem (falha cedo). */
export function coletarRefs(raiz: HTMLElement): Refs {
  const r: Refs = {};
  raiz.querySelectorAll<HTMLElement>("[data-ref]").forEach((e) => { r[e.dataset.ref!] = e; });
  return new Proxy(r, {
    get(alvo, nome: string) {
      const e = alvo[nome];
      if (!e) throw new Error("data-ref ausente: " + nome);
      return e;
    },
  });
}

export const texto = (el: Element, v: string): void => { if (el.textContent !== v) el.textContent = v; };
export const ativar = (el: Element, sim: boolean): void => { el.toggleAttribute("data-ativa", sim); };
export const esconder = (el: Element, sim: boolean): void => { el.toggleAttribute("data-escondido", sim); };
export const titulo = (el: HTMLElement, v: string): void => { if (el.title !== v) el.title = v; };
export const desabilitar = (el: HTMLElement, sim: boolean): void => { (el as HTMLButtonElement).disabled = sim; };
export const marcar = (el: Element, attr: string, v: string): void => { if (el.getAttribute(attr) !== v) el.setAttribute(attr, v); };
export const variavel = (el: HTMLElement, nome: string, v: string): void => {
  if (el.style.getPropertyValue(nome) !== v) el.style.setProperty(nome, v);
};

/** Liga a camada [data-variante] certa dentro de `area` e desliga as outras. */
export function camada(area: Element, variante: string): void {
  area.querySelectorAll(":scope > [data-variante]").forEach((p) => ativar(p, (p as HTMLElement).dataset.variante === variante));
}

export const relogio = (n: number): string =>
  [Math.floor(n / 3600), Math.floor(n / 60) % 60, Math.floor(n % 60)].map((x) => String(x).padStart(2, "0")).join(":");

/** Duração curta da Biblioteca: 42:17, 1:03:40. */
export function duracaoCurta(s: number | null): string {
  if (s == null || !Number.isFinite(s)) return "—";
  const n = Math.round(s), h = Math.floor(n / 3600), m = Math.floor(n / 60) % 60, seg = n % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return (h ? h + ":" : "") + mm + ":" + String(seg).padStart(2, "0");
}

export const nomeDe = (caminho: string): string => caminho.split(/[\\/]/).pop() || caminho;
export const pastaDe = (caminho: string): string => caminho.replace(/[\\/][^\\/]*$/, "");
export const semExt = (n: string): string => n.replace(/\.[^.\\/]+$/, "");

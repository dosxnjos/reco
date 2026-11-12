// O núcleo compartilhado: a Vista, as referências da janela, o backend e o redesenho pontual. O controle (eventos do
// motor e cliques) e o condutor de estados só mudam a Vista e chamam `desenhar()`.
import type { Backend } from "./backend";
import { coletarRefs, janela, type Refs } from "./dom";
import { textoErro, t, type Chave } from "./i18n";
import { aplicarGeral, aplicarStatus } from "./render/geral";
import { aplicarGravar } from "./render/gravar";
import { aplicarOpcoes } from "./render/opcoes";
import { aplicarArquivo, aplicarBiblioteca } from "./render/telas";
import { vistaInicial } from "./vista";
import type { EngineError, EngineEvent, Sinal, Tela, Vista } from "./tipos";

export interface App {
  v: Vista; r: Refs; raiz: HTMLElement; be: Backend;
  /** true depois que o condutor de estados assumiu (backend falso): os eventos do motor não mexem mais na Vista. */
  conduzido: boolean;
  desenhar(): void;
  /** Troca o estado de uma tela (zera o aviso momentâneo) e redesenha. */
  ir<T extends Tela>(tela: T, estado: Vista["estado"][T], mostrar?: boolean): void;
  diz(sinal: Sinal, chave: Chave, vars?: Record<string, string | number>): void;
  falhou(e: unknown): void;
  /** Pedido ao motor com id próprio; `progresso` recebe os eventos `progress` desse pedido. */
  pedir<T>(cmd: string, args?: Record<string, unknown>, progresso?: (ev: EngineEvent) => void): Promise<T>;
  aoProgresso(ev: EngineEvent): boolean;
}

export function erroDe(e: unknown): EngineError {
  if (e && typeof e === "object" && "code" in e) return { code: String((e as EngineError).code), detail: String((e as EngineError).detail ?? "") };
  return { code: "internal", detail: e instanceof Error ? e.message : String(e) };
}

export function criarApp(be: Backend): App {
  const raiz = janela();
  const r = coletarRefs(raiz);
  const progresso = new Map<string, (ev: EngineEvent) => void>();
  let seq = 0;
  const app: App = {
    v: vistaInicial(), r, raiz, be, conduzido: false,
    desenhar() {
      const v = app.v;
      aplicarGeral(v, r, raiz);
      aplicarGravar(v, r, raiz);
      aplicarBiblioteca(v, r, raiz);
      aplicarArquivo(v, r, raiz);
      aplicarOpcoes(v, r, raiz);
      aplicarStatus(v, r, raiz);
    },
    ir(tela, estado, mostrar = false) {
      app.v.estado[tela] = estado;
      if (mostrar) app.v.tela = tela;
      app.v.aviso = null;
      app.desenhar();
    },
    diz(sinal, chave, vars = {}) {
      app.v.aviso = [sinal, t(chave, vars)];
      aplicarStatus(app.v, r, raiz);
    },
    falhou(e) {
      const err = erroDe(e);
      // o detalhe cru do motor fica no console e no engine.log; o status leva só a frase do código (revisão adversarial)
      console.warn("[reco] falhou:", err);
      app.diz("erro", "av.erro", { erro: textoErro(err.code) });
    },
    async pedir<T>(cmd: string, args: Record<string, unknown> = {}, cb?: (ev: EngineEvent) => void): Promise<T> {
      const id = `ui-${++seq}`;
      if (cb) progresso.set(id, cb);
      try {
        return await be.engine<T>(cmd, args, id);
      } finally {
        progresso.delete(id);
      }
    },
    aoProgresso(ev) {
      const cb = ev.id ? progresso.get(ev.id) : undefined;
      if (cb) cb(ev);
      return !!cb;
    },
  };
  return app;
}

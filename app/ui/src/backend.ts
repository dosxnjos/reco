// Ponte com o casco: comandos do Tauri (app/src-tauri/src/comandos, atalho.rs) dentro do app, e o backend falso
// (mock.ts) fora dele, para a interface inteira rodar num navegador comum e nos testes. Molde: lacre/ui/src/backend.ts.
import type { Conclusao, EngineError, EngineEvent, EngineStatus } from "./tipos";

export type EventoCasco = "reco-conclusao" | "reco-versao-nova" | "reco-gravacao-interrompida" | "reco-atalho";

export interface Backend {
  readonly isMock: boolean;
  /** Pedido ao motor (`engine_request`); `id` próprio permite casar os `progress` do pedido. */
  engine<T = unknown>(cmd: string, args?: Record<string, unknown>, id?: string): Promise<T>;
  onEngineEvent(h: (e: EngineEvent) => void): Promise<() => void>;
  onEngineStatus(h: (s: EngineStatus) => void): Promise<() => void>;
  onCasco(evento: "reco-conclusao", h: (c: Conclusao) => void): Promise<() => void>;
  onCasco(evento: "reco-versao-nova", h: (v: { tag: string; url: string }) => void): Promise<() => void>;
  onCasco(evento: "reco-gravacao-interrompida" | "reco-atalho", h: () => void): Promise<() => void>;
  status(): Promise<EngineStatus>;
  /** `rec.stop` e, se vier `auto`, a conclusão encadeada pelo Rust (F3-D13); o resultado chega por `reco-conclusao`. */
  pararGravacao(): Promise<{ path: string | null; duration_s: number | null; auto: string | null }>;
  versaoNova(): Promise<{ tag: string; url: string } | null>;
  copyPath(path: string): Promise<void>;
  openPath(path: string): Promise<void>;
  revealPath(path: string): Promise<void>;
  openExternal(url: string): Promise<void>;
  pickFile(kind: "audio" | "midia"): Promise<string | null>;
  pickFolder(): Promise<string | null>;
  windowHide(): Promise<void>;
  windowMinimize(): Promise<void>;
  windowPin(): Promise<void>;
  definirLingua(lingua: string): Promise<void>;
  definirAtalho(ligar: boolean): Promise<boolean>;
  atalhoRegistrado(): Promise<boolean>;
  autostartLigado(): Promise<boolean>;
  definirAutostart(ligar: boolean): Promise<boolean>;
}

/** Normaliza o que o invoke() lança (texto JSON `{code, detail}` vindo do Rust) em {code, detail}. */
export function toEngineError(e: unknown): EngineError {
  if (e && typeof e === "object" && "code" in e) {
    const o = e as { code: unknown; detail?: unknown };
    return { code: String(o.code), detail: String(o.detail ?? "") };
  }
  if (typeof e === "string") {
    try {
      const o: unknown = JSON.parse(e);
      if (o && typeof o === "object" && "code" in o) return toEngineError(o);
    } catch { /* não é JSON */ }
    const m = /^(\w+): (.*)$/s.exec(e);
    if (m && /^[a-z_]+$/.test(m[1])) return { code: m[1], detail: m[2] };
    return { code: "internal", detail: e };
  }
  return { code: "internal", detail: e instanceof Error ? e.message : String(e) };
}

function temTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

async function backendTauri(): Promise<Backend> {
  const { invoke } = await import("@tauri-apps/api/core");
  const { listen } = await import("@tauri-apps/api/event");
  const chamar = async <T>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
    try {
      return await invoke<T>(cmd, args);
    } catch (e) {
      throw toEngineError(e);
    }
  };
  const ouvir = async <P>(nome: string, h: (p: P) => void) => listen<P>(nome, (e) => h(e.payload));
  return {
    isMock: false,
    engine: (cmd, args = {}, id) => chamar("engine_request", { cmd, args, requestId: id ?? null }),
    onEngineEvent: (h) => ouvir<EngineEvent>("engine-event", h),
    onEngineStatus: (h) => ouvir<EngineStatus>("engine-status", h),
    onCasco: ((evento: EventoCasco, h: (p: unknown) => void) => ouvir(evento, h)) as Backend["onCasco"],
    status: () => chamar("engine_status"),
    pararGravacao: () => chamar("parar_gravacao"),
    versaoNova: () => chamar("versao_nova"),
    copyPath: (path) => chamar("copy_path", { path }),
    openPath: (path) => chamar("open_path", { path }),
    revealPath: (path) => chamar("reveal_path", { path }),
    openExternal: (url) => chamar("open_external", { url }),
    pickFile: (kind) => chamar("pick_file", { kind }),
    pickFolder: () => chamar("pick_folder"),
    windowHide: () => chamar("window_hide"),
    windowMinimize: () => chamar("window_minimize"),
    windowPin: () => chamar("window_pin"),
    definirLingua: (lingua) => chamar("definir_lingua", { lingua }),
    definirAtalho: (ligar) => chamar("definir_atalho", { ligar }),
    atalhoRegistrado: () => chamar("atalho_registrado"),
    autostartLigado: () => chamar("autostart_ligado"),
    definirAutostart: (ligar) => chamar("definir_autostart", { ligar }),
  };
}

let instancia: Promise<Backend> | null = null;

export function obterBackend(): Promise<Backend> {
  if (!instancia) instancia = temTauri() ? backendTauri() : import("./mock").then((m) => m.criarMock());
  return instancia;
}

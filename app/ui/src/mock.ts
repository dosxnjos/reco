// Backend falso (sem o casco Tauri): um motor de mentira com a mesma forma do docs/PROTOCOL.md. Simula `ready`
// atrasado, `state`, `level` a cada 50 ms, `timer` 1/s, `progress`, `live.text`, a biblioteca de nomes inventados e
// `versao_nova`/`reco-versao-nova`. Os testes (app/ui/tests) leem e mexem em window.__recoMock: `chamadas` (todo
// pedido, com o nome do comando do casco), `area` (o que foi copiado), `velocidade`, `derrubar()` e afins.
import type { Backend, EventoCasco } from "./backend";
import type { Conclusao, EngineError, EngineEvent, EngineStatus } from "./tipos";
import { DISPOSITIVOS, FALAS, PASTA, itensFalsos } from "./mock-dados";

type Args = Record<string, unknown>;
type Ouvinte = (p: unknown) => void;
const falha = (code: string, detail = ""): never => { throw { code, detail } satisfies EngineError; };

export interface ControleMock {
  chamadas: { cmd: string; args: Args }[]; area: string; velocidade: number; versao: { tag: string; url: string } | null;
  proximoArquivo: string | null; proximaPasta: string | null; atalhoOcupado: boolean; passosTranscricao: number;
  /** O condutor de estados assumiu: nenhuma resposta pendente volta mais (o controle não mexe na Vista dele). */
  congelado: boolean;
  /** Derruba o motor (engine-status running:false). `volta` em ms (null = não volta); `semAviso` não manda o
   *  reco-gravacao-interrompida (o evento perdido: a tela tem de ressincronizar sozinha). */
  derrubar(o?: { volta?: number | null; semAviso?: boolean }): void;
  emitir(e: EngineEvent): void; estado(): string; config: Args;
  /** Atraso extra (ms reais, sem a `velocidade`) antes de o motor falso atender cada comando: o motor real lento. */
  atraso: Record<string, number>;
  /** A conclusão encadeada chega antes da resposta do parar_gravacao (o Rust não garante a ordem). */
  conclusaoAntes: boolean;
  /** Recusa a próxima chamada do comando com o código dado (uma vez só), como o motor real ocupado. */
  recusar: Record<string, string>;
  /** O `state` diz `transcribing: true` sem trabalho de verdade (a checagem do modelo ocupando a vaga). */
  vagaOcupada: boolean;
  /** Menu da bandeja como o lib.rs faz: Gravar sempre no modo `rec`; Parar pelo mesmo `parar_gravacao`. */
  bandeja(item: "gravar" | "parar"): Promise<unknown>;
  /** Força o estado do motor sem evento (simula o `stopping` que o motor real mostra enquanto fecha o MP3). */
  forcarEstado(s: string): void;
  /** Evento do casco como o Rust mandaria (reco-atalho, reco-versao-nova…). */
  casco(nome: EventoCasco, p?: unknown): void;
}

class MotorFalso {
  rec = "idle"; modo = "rec"; elapsed = 0; ready = false; live = false; lastRec: string | null = null; auto: string | null = null;
  trabalho: { id: string; cancelar: () => void } | null = null;
  itens = itensFalsos();
  config: Args = { language: "pt", output_dir: null, nota_dir: null, mic_device: "auto:console", sys_device: "auto:console",
    mic_gain: 1, sys_gain: 1, live: false, device: "AUTO" };
  private relogios: number[] = [];
  private seq = 0;
  constructor(private ctl: ControleMock, private emitir: (e: EngineEvent) => void) {}

  espera = (ms: number) => new Promise<void>((ok) => setTimeout(ok, ms / this.ctl.velocidade));
  pasta = () => String(this.config.output_dir ?? PASTA);
  estadoEv = () => this.emitir({ event: "state", state: this.rec, elapsed_s: this.elapsed });

  async ligar(): Promise<void> {
    await this.espera(700);
    this.ready = true;
    this.emitir({ event: "ready", import_s: 0.7, has: { sc: true, np: true, av: true, ov: true }, lang: this.config.language, reco_version: "falso" });
  }

  private nomeDispositivo(kind: "microphone" | "speaker", chave: string) {
    const st = DISPOSITIVOS[kind], sel = String(this.config[chave]);
    const id = sel === "auto:comm" ? st.comm : sel.startsWith("auto") ? st.console : sel;
    const d = st.devs.find((x) => x.id === id) ?? st.devs[0];
    return { id: d.id, name: d.name, via: sel.startsWith("auto") ? sel.slice(5) : "manual" };
  }

  private correr(): void {
    this.parar();
    let fase = 0;
    this.relogios.push(window.setInterval(() => {
      if (this.rec !== "recording") return;
      fase += 1;
      const onda = (k: number) => 0.06 + 0.12 * Math.abs(Math.sin(fase * k) * Math.sin(fase * 0.13));
      this.emitir({ event: "level", mic: onda(0.9), sys: this.modo === "nota" ? null : onda(0.55) });
    }, 50 / this.ctl.velocidade));
    this.relogios.push(window.setInterval(() => {
      if (this.rec !== "recording") return;
      this.elapsed += 1;
      this.emitir({ event: "timer", elapsed_s: this.elapsed });
    }, 1000 / this.ctl.velocidade));
    if (this.live && this.modo === "rec") {
      let i = 0;
      this.relogios.push(window.setInterval(() => {
        if (this.rec !== "recording") return;
        const [quem, texto] = FALAS.pt[i % FALAS.pt.length];
        this.emitir({ event: "live.text", channel: quem === "eu" ? "mic" : "sys", speaker: quem === "eu" ? "Eu" : "Interlocutor(es)", text: texto });
        i += 1;
      }, 1500 / this.ctl.velocidade));
    }
  }
  parar(): void { this.relogios.forEach((r) => clearInterval(r)); this.relogios = []; }

  /** Trabalho longo com `progress` (pct 0..99) e cancelamento; devolve o `data` final. */
  private async longo<T>(id: string, pctNulo: boolean, fim: () => T): Promise<T> {
    if (this.trabalho) falha("busy", "outra transcrição em curso");
    let cancelado = false;
    this.trabalho = { id, cancelar: () => { cancelado = true; } };
    try {
      const n = this.ctl.passosTranscricao;
      for (let k = 0; k < n; k++) {
        await this.espera(300);
        if (cancelado) falha("cancelled", "cancelado pelo usuário");
        const pct = Math.min(99, Math.round(((k + 1) / n) * 100));
        this.emitir({ id, event: "progress", pct: pctNulo ? null : pct, text: pctNulo ? null : `Transcrevendo… ${pct}%` });
      }
      return fim();
    } finally {
      this.trabalho = null;
    }
  }

  async pedido(cmd: string, args: Args, id: string): Promise<unknown> {
    if (!this.ready && !["hello", "state"].includes(cmd)) await this.espera(700);
    const extra = this.ctl.atraso[cmd];
    if (extra) await new Promise<void>((ok) => setTimeout(ok, extra));
    const recusa = this.ctl.recusar[cmd];
    if (recusa) { delete this.ctl.recusar[cmd]; falha(recusa, "recusa do teste"); }
    const f =(this as unknown as Record<string, (a: Args, id: string) => unknown>)["c_" + cmd.replace(/\./g, "_")];
    if (!f) falha("internal", "comando desconhecido: " + cmd);
    return f.call(this, args, id);
  }

  c_hello() { return { engine_version: "0.1.0-falso", reco_version: "falso", protocol: 1, platform: "navegador", ready: this.ready, uptime_s: 1 }; }
  c_state() {
    return { ready: this.ready, rec_state: this.rec, elapsed_s: this.elapsed, transcribing: !!this.trabalho || this.ctl.vagaOcupada, live: this.live, last_rec: this.lastRec, auto: this.auto };
  }
  c_config_get() { return { config: { ...this.config }, output_dir_efetivo: this.pasta(), lang_efetivo: this.config.language ?? "pt" }; }
  c_config_set(a: Args) {
    const changes = (a.changes ?? {}) as Args;
    if ("language" in changes && (this.rec !== "idle" || this.trabalho)) falha("busy", "gravando ou transcrevendo");
    Object.assign(this.config, changes);
    return this.c_config_get();
  }
  c_devices_list() {
    const sel = { mic_device: String(this.config.mic_device), sys_device: String(this.config.sys_device) };
    const falta = (k: "microphone" | "speaker", s: string) => !s.startsWith("auto") && !DISPOSITIVOS[k].devs.some((d) => d.id === s);
    return { ...DISPOSITIVOS, selected: sel, missing: { mic: falta("microphone", sel.mic_device), sys: falta("speaker", sel.sys_device) } };
  }
  c_devices_refresh() { return this.c_devices_list(); }
  async c_rec_start(a: Args) {
    if (this.rec !== "idle") falha("busy", "estado " + this.rec);
    this.modo = a.mode === "nota" ? "nota" : "rec";
    if (this.modo === "nota" && this.trabalho) falha("busy", "transcrição em curso");
    this.live = this.modo === "rec" && !!this.config.live && !this.trabalho;
    this.elapsed = 0; this.rec = "recording"; this.estadoEv(); this.correr();
    return { mic: this.nomeDispositivo("microphone", "mic_device"), sys: this.nomeDispositivo("speaker", "sys_device"), live: this.live, live_suprimido: false };
  }
  c_rec_pause() { if (this.rec !== "recording") falha("refused"); this.rec = "paused"; this.estadoEv(); return { elapsed_s: this.elapsed }; }
  c_rec_resume() { if (this.rec !== "paused") falha("refused"); this.rec = "recording"; this.estadoEv(); return { elapsed_s: this.elapsed }; }
  async c_rec_stop() {
    if (this.rec !== "recording" && this.rec !== "paused") falha("refused", "fora de gravação");
    this.rec = "stopping"; this.estadoEv(); this.parar();
    await this.espera(200);
    const prefixo = this.modo === "nota" ? "nota" : "reco";
    this.lastRec = `${this.pasta()}\\2026-11-12_10${String(++this.seq).padStart(2, "0")}_${prefixo}.mp3`;
    this.auto = this.modo === "nota" ? "nota" : this.live ? "final_pass" : null;
    this.rec = "stopped"; this.estadoEv();
    return { path: this.lastRec, duration_s: this.elapsed, auto: this.auto };
  }
  c_rec_set_gain() { return { applied: true }; }
  async c_rec_conclude(a: Args, id: string) {
    if (this.rec !== "stopped" || !this.lastRec) return falha("refused", "nada parado para concluir");
    const path: string = this.lastRec, txt = path.replace(/\.mp3$/, ".txt"), acao = String(a.action);
    const fim = (s: string) => { this.rec = s; this.estadoEv(); };
    if (acao === "save") { fim("idle"); this.guardar(path); return { path }; }
    if (acao === "delete") { fim("idle"); return { path, deleted: true }; }
    if (acao === "final_pass") return this.longo(id, false, () => ({ txt, text: "…" }));
    if (acao === "nota") return this.longo(id, true, () => { fim("idle"); return { md: path.replace(/\.mp3$/, ".md") }; });
    if (acao === "transcribe" || acao === "transcribe_delete") {
      fim("idle");
      return this.longo(id, false, () => { if (acao === "transcribe") this.guardar(path, txt); return { txt, deleted: acao === "transcribe_delete" }; });
    }
    return falha("bad_args", "action " + acao);
  }
  private guardar(path: string, txt: string | null = null): void {
    const nome = path.split("\\").pop()!;
    this.itens = [{ name: nome, path, mtime: Date.now() / 1000, bytes: 1000, duration_s: this.elapsed, txt, resumo: null },
      ...this.itens.filter((i) => i.path !== path)];
  }
  c_transcribe_file(a: Args, id: string) {
    const path = String(a.path);
    if (/sem-audio/i.test(path)) falha("no_audio_stream", "sem trilha de áudio");
    return this.longo(id, false, () => {
      const txt = path.replace(/\.[^.\\]+$/, ".txt");
      this.itens = this.itens.map((i) => (i.path === path ? { ...i, txt } : i));
      return { txt };
    });
  }
  c_transcribe_cancel() { const ok = !!this.trabalho; this.trabalho?.cancelar(); return { found: ok }; }
  c_convert_extract_mp3(a: Args, id: string) {
    const path = String(a.path);
    return this.longo(id, false, () => ({ path: path.replace(/\.[^.\\]+$/, ".mp3"), src_bytes: 312_000_000, dst_bytes: 23_000_000 }));
  }
  c_library_list() { return { folder: this.pasta(), items: this.itens }; }
  c_library_search(a: Args) {
    const q = String(a.q ?? "").toLocaleLowerCase();
    return { q: a.q, items: this.itens.filter((i) => i.name.toLocaleLowerCase().includes(q)) };
  }
  c_library_delete(a: Args) {
    const path = String(a.path);
    if (!this.itens.some((i) => i.path === path)) falha("refused", "fora da biblioteca");
    this.itens = this.itens.filter((i) => i.path !== path);
    return { path, deleted: true };
  }
  async c_resumo_ia(a: Args, id: string) {
    const path = String(a.path);
    const item = this.itens.find((i) => i.path === path);
    if (!item?.txt) falha("not_found", "sem .txt");
    for (let k = 0; k < 3; k++) { await this.espera(300); this.emitir({ id, event: "progress", pct: null, text: null }); }
    return { path: path.replace(/\.mp3$/, ".resumo.md"), existia: false };
  }
  c_model_update_check() { return {}; }
  c_app_update_check() { return this.ctl.versao; }
}

export function criarMock(): Backend {
  const ouvintes = new Map<string, Set<Ouvinte>>();
  const avisar = (nome: string, p: unknown) => ouvintes.get(nome)?.forEach((h) => h(p));
  const ouvir = async (nome: string, h: Ouvinte) => {
    if (!ouvintes.has(nome)) ouvintes.set(nome, new Set());
    ouvintes.get(nome)!.add(h);
    return () => { ouvintes.get(nome)?.delete(h); };
  };
  const ctl: ControleMock = {
    chamadas: [], area: "", velocidade: 1, versao: null, proximoArquivo: "C:\\Vídeos\\reuniao-fornecedor.mp4", proximaPasta: "C:\\Notas",
    atalhoOcupado: false, passosTranscricao: 6, congelado: false, atraso: {}, conclusaoAntes: false, recusar: {}, vagaOcupada: false,
    derrubar: (o = {}) => {
      // como o estado.rs: `stopping` também tem arquivo aberto (o MP3 pode não ter fechado)
      const gravando = ["recording", "paused", "starting", "stopping"].includes(motor.rec);
      motor.parar(); motor.rec = "idle"; motor.ready = false;
      avisar("engine-status", { running: false } satisfies EngineStatus);
      if (gravando && !o.semAviso) avisar("reco-gravacao-interrompida", null);
      const volta = o.volta === undefined ? 400 / ctl.velocidade : o.volta;
      if (volta != null) setTimeout(() => { avisar("engine-status", { running: true }); void motor.ligar(); }, volta);
    },
    emitir: (e) => avisar("engine-event", { v: 1, ...e }),
    casco: (nome, p) => avisar(nome, p ?? null),
    estado: () => motor.rec,
    forcarEstado: (s) => { motor.rec = s; },
    bandeja: (item) => (item === "gravar" ? motor.pedido("rec.start", { mode: "rec" }, `falso-${++n}`) : pararCasco()),
    get config() { return motor.config; },
  };
  const motor = new MotorFalso(ctl, ctl.emitir);
  (window as unknown as { __recoMock: ControleMock }).__recoMock = ctl;
  let n = 0, atalho = false, autostart = false;
  const anotar = (cmd: string, args: Args = {}) => { ctl.chamadas.push({ cmd, args }); };
  /** O `parar_gravacao` do Rust: `rec.stop` e, com `auto`, a conclusão em segundo plano, anunciada por `reco-conclusao`. */
  const pararCasco = async () => {
    anotar("parar_gravacao");
    const parou = await motor.pedido("rec.stop", {}, `falso-${++n}`) as { path: string; duration_s: number; auto: string | null };
    if (parou.auto) {
      const action = parou.auto;
      const conclusao = motor.pedido("rec.conclude", { action }, `falso-${++n}`).then(
        (data) => { if (action === "nota") ctl.area = `"${(data as { md: string }).md}"`; avisar("reco-conclusao", { action, ok: true, data } as Conclusao); },
        (error: EngineError) => avisar("reco-conclusao", { action, ok: false, error } as Conclusao));
      if (ctl.conclusaoAntes) await conclusao;
    }
    return parou;
  };
  const nunca = () => new Promise<never>(() => undefined);
  const engine = async <T>(cmd: string, args: Args = {}, id?: string): Promise<T> => {
    anotar(cmd, args);
    if (ctl.congelado) return nunca();
    const r = (await motor.pedido(cmd, args, id ?? `falso-${++n}`)) as T;
    return ctl.congelado ? nunca() : r;
  };
  const casco = async <T>(cmd: string, args: Args, v: T): Promise<T> => { anotar(cmd, args); return ctl.congelado ? nunca() : v; };
  void motor.ligar();
  return {
    isMock: true,
    engine,
    onEngineEvent: (h) => ouvir("engine-event", h as Ouvinte),
    onEngineStatus: (h) => ouvir("engine-status", h as Ouvinte),
    onCasco: ((evento: EventoCasco, h: Ouvinte) => ouvir(evento, h)) as Backend["onCasco"],
    status: async () => ({ running: true }),
    pararGravacao: pararCasco,
    versaoNova: () => casco("versao_nova", {}, ctl.versao),
    copyPath: async (path) => { anotar("copy_path", { path }); ctl.area = `"${path}"`; },
    openPath: (path) => casco("open_path", { path }, undefined),
    revealPath: (path) => casco("reveal_path", { path }, undefined),
    openExternal: (url) => casco("open_external", { url }, undefined),
    pickFile: (kind) => casco("pick_file", { kind }, ctl.proximoArquivo),
    pickFolder: () => casco("pick_folder", {}, ctl.proximaPasta),
    windowHide: () => casco("window_hide", {}, undefined),
    windowMinimize: () => casco("window_minimize", {}, undefined),
    windowPin: () => casco("window_pin", {}, undefined),
    definirLingua: (lingua) => casco("definir_lingua", { lingua }, undefined),
    definirAtalho: async (ligar) => {
      anotar("definir_atalho", { ligar });
      if (ligar && ctl.atalhoOcupado) falha("hotkey_taken", "Ctrl+Shift+R ocupado");
      motor.config.casco_atalho = ligar; atalho = ligar;
      return atalho;
    },
    atalhoRegistrado: () => casco("atalho_registrado", {}, atalho),
    autostartLigado: () => casco("autostart_ligado", {}, autostart),
    definirAutostart: async (ligar) => { anotar("definir_autostart", { ligar }); autostart = ligar; return autostart; },
  };
}

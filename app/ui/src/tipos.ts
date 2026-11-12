// Tipos da interface: o modelo da tela (Vista), os nomes do design (telas, estados, skins) e as formas do protocolo
// (docs/PROTOCOL.md) que a interface lê. A tela é sempre uma projeção da Vista: o controle (eventos do motor) e o
// condutor de estados (backend falso, testes) só mudam a Vista e pedem o redesenho pontual.

export type Tela = "gravar" | "biblioteca" | "arquivo" | "opcoes";
export type Skin = "a" | "b" | "c";
export type Tema = "sistema" | "claro" | "escuro";
export type Lingua = "pt" | "en";
export type Sinal = "info" | "ok" | "aviso" | "erro" | "espera" | "rec";

// Estados por tela: os nomes do design/DESIGN.md (o condutor percorre todos).
export const ESTADOS = {
  gravar: ["motor-subindo", "pronto", "gravando", "gravando-ao-vivo", "nota-gravando", "pausado", "parado",
    "transcrevendo", "transcricao-pronta", "erro", "erro-detalhe"],
  biblioteca: ["vazia", "lista", "selecionada", "transcrevendo-item", "resumindo", "busca-sem-resultado", "erro"],
  arquivo: ["nada-escolhido", "escolhido", "transcrevendo", "convertendo", "pronto", "erro"],
  opcoes: ["normal", "durante-gravacao", "dispositivo-ausente"],
} as const satisfies Record<Tela, readonly string[]>;
export type EstadoDe<T extends Tela> = (typeof ESTADOS)[T][number];
export const TELAS = Object.keys(ESTADOS) as Tela[];
export const SKINS: Skin[] = ["a", "b", "c"];

/** Linha da Biblioteca (de `library.list`/`library.search`). */
export interface ItemLib { nome: string; path: string; quando: string; duracao: string; temTexto: boolean; txt: string | null }

/** Fala do painel ao vivo: quem ("Eu"/"Outros" já traduzido) e o texto; a última pode ser rascunho. */
export interface Fala { quem: string; eu: boolean; texto: string }

/** Erro mostrado na tela Gravar: título, nota, detalhe inteiro e a saída oferecida. */
export interface ErroGravar { titulo: string; nota: string; linha: string; detalhe: string; saida: "opcoes" | "pasta" }

export interface Disp { id: string; nome: string }

export interface VistaGravar {
  mic: string; sis: string; pasta: string; arquivo: string; segundos: number;
  modo: "gravacao" | "nota"; aoVivo: boolean; sisAusente: boolean; padraoSis: string;
  tarefa: "transcrever" | "passada" | "nota"; pct: number | null; txt: string; erro: ErroGravar;
  ganhoMic: number; ganhoSis: number; falas: Fala[]; ocupadoFora: boolean;
}
export interface VistaBiblioteca { itens: ItemLib[]; sel: number | null; busca: string; pasta: string; trPath: string | null; trPct: number | null; resumoPath: string | null; erro: string }
export interface VistaArquivo {
  origem: { nome: string; path: string; meta: string } | null; tarefa: "transcrever" | "converter";
  pct: number | null; falta: string; saida: string; saidaPath: string; erroTitulo: string; erroNota: string; erroLinha: string;
}
export interface VistaOpcoes {
  mics: Disp[]; siss: Disp[]; selMic: string; selSis: string; pasta: string; notaDir: string; processar: string;
  aoVivo: boolean; atalho: boolean; atalhoOcupado: boolean; autostart: boolean; versaoApp: string; versaoMotor: string; padraoSis: string;
}

export interface Vista {
  skin: Skin; tema: Tema; lingua: Lingua; versao: { tag: string; url: string } | null;
  tela: Tela; estado: { [T in Tela]: EstadoDe<T> };
  /** Recado momentâneo no status (vence a linha do estado até a próxima troca de estado). */
  aviso: [Sinal, string] | null;
  /** Gravando, pausado ou transcrevendo: a aba Arquivo fica bloqueada com o motivo (F1-D7). */
  ocupado: boolean;
  g: VistaGravar; b: VistaBiblioteca; a: VistaArquivo; o: VistaOpcoes;
}

// ---- protocolo (só o que a interface lê)
export interface EngineError { code: string; detail: string }
export interface EngineEvent { v?: number; id?: string; event: string; [k: string]: unknown }
export interface EngineStatus { running: boolean; [k: string]: unknown }
export interface Conclusao { action: string; ok: boolean; data?: Record<string, unknown>; error?: EngineError }
export interface ItemProto { name: string; path: string; mtime: number; bytes: number; duration_s: number | null; txt: string | null; resumo: string | null }
export interface DispProto { devs: { id: string; name: string }[]; console: string | null; comm: string | null }
export interface DevicesProto {
  microphone: DispProto; speaker: DispProto;
  selected: { mic_device: string | null; sys_device: string | null }; missing: { mic: boolean; sys: boolean };
}
export interface ConfigProto { config: Record<string, unknown>; output_dir_efetivo: string; lang_efetivo: string }

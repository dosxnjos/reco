// A Vista inicial (antes do motor responder) e os conjuntos de estado que mais de um módulo consulta.
import { lerAparencia } from "./aparencia";
import type { Vista } from "./tipos";

export const GRAVANDO = new Set<string>(["gravando", "gravando-ao-vivo", "nota-gravando", "pausado"]);
export const PADRAO = { gravar: "motor-subindo", biblioteca: "lista", arquivo: "nada-escolhido", opcoes: "normal" } as const;

export function vistaInicial(): Vista {
  const { skin, tema } = lerAparencia(); // o config do motor reconcilia depois do `ready`
  return {
    skin, tema, lingua: "pt", versao: null,
    tela: "gravar", estado: { ...PADRAO }, aviso: null, ocupado: false, motorFora: false,
    g: {
      mic: "", sis: "", pasta: "", arquivo: "", segundos: 0, modo: "gravacao", aoVivo: false, sisAusente: false, padraoSis: "",
      tarefa: "transcrever", pct: null, txt: "", ganhoMic: 1, ganhoSis: 1, falas: [], ocupadoFora: false,
      erro: { titulo: "", nota: "", linha: "", detalhe: "", saida: "opcoes" },
    },
    b: { itens: [], sel: null, busca: "", pasta: "", trPath: null, trPct: null, resumoPath: null, erro: "" },
    a: { origem: null, tarefa: "transcrever", pct: null, falta: "", saida: "", saidaPath: "", erroTitulo: "", erroNota: "", erroLinha: "" },
    o: {
      mics: [], siss: [], selMic: "auto:console", selSis: "auto:console", pasta: "", notaDir: "", processar: "AUTO",
      aoVivo: false, atalho: false, atalhoOcupado: false, autostart: false, versaoApp: "", versaoMotor: "…", padraoSis: "",
    },
  };
}

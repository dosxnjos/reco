// Dados inventados do backend falso e do condutor de estados (repo público: nenhum nome, caminho ou gravação real).
// Os mesmos da vitrine (design/vitrine.modelo.html): texto normal e texto longo, para os testes de anti-pulo.
import type { ItemProto } from "./tipos";

export const PASTA = "C:\\Gravações\\Reco";

export interface Conteudo {
  mic: string; sis: string; padrao: string; arquivo: string; origem: string; pasta: string; crono: number; busca: string; ausente: boolean;
}

export const CONTEUDO: Record<"normal" | "longo", Conteudo> = {
  normal: {
    mic: "Microfone (Realtek(R) Audio)", sis: "Alto-falantes (Realtek(R) Audio)", padrao: "Alto-falantes (Realtek(R) Audio)",
    arquivo: "2026-11-11_1432_reco.mp3", origem: "reuniao-fornecedor.mp4", pasta: PASTA, crono: 42 * 60 + 17,
    busca: "orçamento verão", ausente: false,
  },
  longo: {
    mic: "Microfone de matriz (Tecnologia Intel(R) Smart Sound para microfones digitais)", sis: "Fones de ouvido (QCY H3 Hands-Free AG Audio)",
    padrao: "Alto-falantes (Realtek(R) Audio)", arquivo: "2026-11-11_1432_reco_reuniao-mensal-fornecedores-calcados-planejamento-verao.mp3",
    origem: "gravacao-da-reuniao-trimestral-com-os-franqueados-da-regiao-sul-e-fornecedores.mp4",
    pasta: "C:\\Gravações\\Reco\\Reuniões com fornecedores e franqueados\\2026\\novembro", crono: 12 * 3600 + 34 * 60 + 56,
    busca: "orçamento de calçados com o fornecedor de Franca para a coleção de verão", ausente: true,
  },
};

export const FALAS: Record<"pt" | "en", [string, string][]> = {
  pt: [["eu", "Bom dia, pessoal. Vamos começar pelo pedido de verão?"], ["outros", "Bom dia. A grade fechou ontem; faltam só os tamanhos 39 e 40."],
    ["eu", "Certo. E a entrega continua para a segunda semana de dezembro?"], ["outros", "Continua, mas o frete subiu um pouco. Mando a tabela nova hoje à tarde."],
    ["eu", "Manda sim, que eu passo para o financeiro ainda hoje."], ["outros", "Outra coisa: a amostra do modelo novo chega na quinta, e aí a gente"]],
  en: [["eu", "Morning, everyone. Shall we start with the summer order?"], ["outros", "Morning. The grid closed yesterday; only sizes 39 and 40 are missing."],
    ["eu", "Right. Is delivery still on for the second week of December?"], ["outros", "It is, but freight went up a little. I will send the new table this afternoon."],
    ["eu", "Please do, I will pass it to finance today."], ["outros", "One more thing: the sample of the new model arrives on Thursday, and then we"]],
};

// [nome, mtime (s), duração (s), tem texto]
const BRUTO: [string, number, number, boolean][] = [
  ["2026-11-11_1432_reco.mp3", 1794411120, 2537, true], ["2026-11-11_0915_reco.mp3", 1794392100, 3820, false],
  ["2026-11-10_1600_reco.mp3", 1794330000, 1625, true], ["2026-11-10_1030_reco.mp3", 1794310200, 768, true],
  ["2026-11-07_1745_reco.mp3", 1794077100, 3492, true], ["2026-11-07_1100_reco.mp3", 1794052800, 391, false],
  ["2026-11-06_1415_reco.mp3", 1793978100, 4869, true], ["2026-11-05_0930_reco.mp3", 1793874600, 2090, true],
  ["2026-11-04_1620_reco.mp3", 1793812800, 1184, false], ["2026-11-04_0900_reco.mp3", 1793786400, 2702, true],
  ["2026-11-03_1500_reco.mp3", 1793721600, 497, true], ["2026-10-31_1130_reco.mp3", 1793449800, 3156, true],
];

export function itensFalsos(pasta = PASTA): ItemProto[] {
  return BRUTO.map(([name, mtime, dur, tem]) => {
    const path = pasta + "\\" + name;
    return { name, path, mtime, bytes: Math.round(dur * 12000), duration_s: dur, txt: tem ? path.replace(/\.mp3$/, ".txt") : null, resumo: null };
  });
}

export const DISPOSITIVOS = {
  microphone: { devs: [{ id: "{mic-1}", name: "Microfone (Realtek(R) Audio)" }, { id: "{mic-2}", name: "Headset (QCY H3)" }], console: "{mic-1}", comm: "{mic-2}" },
  speaker: { devs: [{ id: "{spk-1}", name: "Alto-falantes (Realtek(R) Audio)" }, { id: "{spk-2}", name: "Fones de ouvido (QCY H3)" }], console: "{spk-1}", comm: "{spk-2}" },
};

export const ERRO_DETALHE = (sis: string, pasta: string): string => [
  "Erro ao abrir o dispositivo de saída", "", "Dispositivo: " + sis, "Modo: WASAPI loopback, 16 kHz, estéreo",
  "Código: AUDCLNT_E_DEVICE_INVALIDATED (0x88890004)", "O dispositivo foi desconectado ou mudou de formato enquanto o Reco abria a captura.", "",
  "Traceback (most recent call last):", '  File "reco.py", in _open_streams', "    rec_sys = self._sys.recorder(samplerate=16000, channels=2, blocksize=352)",
  '  File "soundcard/mediafoundation.py", in recorder', "    return _Recorder(self._get_audio_client(), samplerate, channels, blocksize, True)",
  "RuntimeError: Error 0x88890004 (AUDCLNT_E_DEVICE_INVALIDATED)", "", "Pasta: " + pasta, "Gravação: nenhum arquivo criado.",
].join("\n");

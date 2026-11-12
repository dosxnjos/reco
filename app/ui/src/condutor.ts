// Condutor de estados (DESIGN.md § Condutor; F1-D12): no backend falso a página aceita
// ?direcao=&tela=&estado=&tema=&texto=&versao= e expõe window.vitrine.definir({...}) com os mesmos nomes da vitrine,
// para design/testar-anti-pulo.cjs e design/testar-contrato.cjs rodarem com --url contra a interface real.
// Cada chamada monta a Vista inteira do cenário (dados inventados de mock-dados.ts) e redesenha na hora.
import type { App } from "./app";
import { semExt } from "./dom";
import { t, definirLingua, textoErro } from "./i18n";
import { CONTEUDO, ERRO_DETALHE, FALAS, itensFalsos } from "./mock-dados";
import { paraItem } from "./controle/dados";
import { GRAVANDO, PADRAO } from "./vista";
import { fixarNiveis, pintarAgora, zerarNiveis } from "./vu";
import { ESTADOS, SKINS, TELAS, type Skin, type Tela, type Tema, type Vista } from "./tipos";

type Param = { direcao?: string; tela?: string; estado?: string; tema?: string; texto?: string; versao?: string };
const VALORES = { tema: ["sistema", "claro", "escuro"], texto: ["normal", "longo-pt", "longo-en"], versao: ["nao", "sim"] };

function gravar(v: Vista, k: (typeof CONTEUDO)["normal"], e: string): void {
  const g = v.g, rodando = GRAVANDO.has(e) || e === "parado";
  Object.assign(g, {
    mic: k.mic, sis: k.sis, pasta: k.pasta, arquivo: k.arquivo, segundos: rodando ? k.crono : 0,
    modo: e === "nota-gravando" ? "nota" : "gravacao", aoVivo: e === "gravando-ao-vivo", sisAusente: k.ausente, padraoSis: k.padrao,
    tarefa: "transcrever", pct: 42, txt: k.pasta + "\\" + semExt(k.arquivo) + ".txt", ganhoMic: 1, ganhoSis: 8, ocupadoFora: false,
    erro: { titulo: t("g.erro-comecar"), nota: t("g.erro-comecar-nota"), linha: t("g.erro-saida-linha", { sis: k.sis }), detalhe: ERRO_DETALHE(k.sis, k.pasta), saida: "opcoes" },
  });
  g.falas = FALAS[v.lingua].map(([quem, fala], i, todas) => ({
    quem: t(quem === "eu" ? "g.eu" : "g.outros"), eu: quem === "eu", texto: fala + (i === todas.length - 1 ? "…" : ""),
  }));
}

function biblioteca(v: Vista, k: (typeof CONTEUDO)["normal"], e: string): void {
  const itens = itensFalsos(k.pasta).map(paraItem);
  itens[0] = { ...itens[0], nome: k.arquivo };
  const sel = ({ selecionada: 0, "transcrevendo-item": 1, resumindo: 0 } as Record<string, number>)[e];
  v.b = { itens, sel: sel ?? null, busca: e === "busca-sem-resultado" ? k.busca : "", pasta: k.pasta,
    trPath: e === "transcrevendo-item" ? itens[1].path : null, trPct: 38, resumoPath: e === "resumindo" ? itens[0].path : null, erro: t("b.acesso-negado") };
}

function arquivo(v: Vista, k: (typeof CONTEUDO)["normal"], e: string): void {
  const conv = e === "convertendo";
  v.a = {
    origem: { nome: k.origem, path: "C:\\Vídeos\\" + k.origem, meta: t("a.meta", { tipo: t("a.tipo-video", { ext: "MP4" }), tamanho: "48:12, 312 MB" }) },
    tarefa: conv ? "converter" : "transcrever", pct: conv ? 27 : 63, falta: t("a.falta-tempo", { tempo: conv ? "40 s" : "4 min" }),
    saida: semExt(k.origem) + ".txt", saidaPath: "C:\\Vídeos\\" + semExt(k.origem) + ".txt",
    erroTitulo: t("a.erro-sem-audio"), erroNota: t("a.erro-sem-audio-nota"), erroLinha: t("a.erro-linha", { nome: k.origem, motivo: textoErro("no_audio_stream") }),
  };
}

function opcoes(v: Vista, k: (typeof CONTEUDO)["normal"], normal: boolean): void {
  Object.assign(v.o, {
    mics: [{ id: "{mic}", nome: k.mic }], siss: [{ id: "{sis}", nome: k.sis }], selMic: normal ? "auto:console" : "{mic}", selSis: normal ? "auto:console" : "{sis}",
    pasta: k.pasta, notaDir: "", processar: "AUTO", aoVivo: false, atalho: false, atalhoOcupado: false, autostart: false,
    versaoApp: "0.1.0", versaoMotor: "0.1.0", padraoSis: k.padrao,
  });
}

export function criarCondutor(app: App) {
  const s = { direcao: app.v.skin as string, tela: "gravar" as Tela, estado: "pronto", tema: app.v.tema as string, texto: "normal", versao: "nao" };
  const porTela: Record<Tela, string> = { ...PADRAO, gravar: "pronto" };

  function definir(p: Param = {}): typeof s {
    app.conduzido = true;
    const mock = (window as unknown as { __recoMock?: { congelado: boolean } }).__recoMock;
    if (mock) mock.congelado = true;
    s.direcao = app.v.skin; s.tema = app.v.tema;
    if (p.direcao && (SKINS as string[]).includes(p.direcao)) s.direcao = p.direcao;
    for (const n of ["tema", "texto", "versao"] as const) if (p[n] !== undefined && VALORES[n].includes(p[n]!)) s[n] = p[n]!;
    if (p.tela && TELAS.includes(p.tela as Tela)) s.tela = p.tela as Tela;
    const est = p.estado ?? (p.tela !== undefined ? porTela[s.tela] : s.estado);
    s.estado = (ESTADOS[s.tela] as readonly string[]).includes(est) ? est : porTela[s.tela];
    porTela[s.tela] = s.estado;
    const v = app.v, normal = s.texto === "normal", k = CONTEUDO[normal ? "normal" : "longo"];
    v.skin = s.direcao as Skin; v.tema = s.tema as Tema; v.lingua = s.texto === "longo-en" ? "en" : "pt";
    definirLingua(v.lingua);
    v.versao = s.versao === "sim" ? { tag: "2.0", url: "https://github.com/dosxnjos/reco/releases" } : null;
    v.tela = s.tela; v.aviso = null;
    (Object.keys(porTela) as Tela[]).forEach((x) => { (v.estado as Record<Tela, string>)[x] = porTela[x]; });
    const eg = v.estado.gravar;
    v.ocupado = (s.tela === "gravar" && (GRAVANDO.has(eg) || eg === "transcrevendo")) || (s.tela === "opcoes" && s.estado === "durante-gravacao");
    gravar(v, k, eg); biblioteca(v, k, v.estado.biblioteca); arquivo(v, k, v.estado.arquivo); opcoes(v, k, normal);
    if (["motor-subindo", "erro", "erro-detalhe"].includes(eg)) zerarNiveis(); else if (GRAVANDO.has(eg) && eg !== "pausado") fixarNiveis(0.42, eg === "nota-gravando" ? 0 : 0.55); else fixarNiveis(0.06, 0.04);
    app.desenhar();
    pintarAgora(app.r);
    return { ...s };
  }

  // estado(): o que a janela mostra agora (no modo normal, o que o controle levou à Vista)
  const estado = () => ({ ...s, direcao: app.v.skin, tema: app.v.tema, tela: app.v.tela, estado: app.v.estado[app.v.tela], estados: { ...app.v.estado } });
  return { direcoes: SKINS, telas: TELAS, estados: ESTADOS, definir, estado };
}

/** Os parâmetros da URL que o condutor entende (vazio = a página abre no modo normal, com o motor falso). */
export function parametrosDaUrl(): Param | null {
  const q = new URLSearchParams(location.search), ini: Param = {};
  for (const n of ["direcao", "tela", "estado", "tema", "texto", "versao"] as const) if (q.has(n)) ini[n] = q.get(n)!;
  return Object.keys(ini).length ? ini : null;
}

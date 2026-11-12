// A linha de status (R3, R12): uma por tela e estado, montada da Vista; o aviso momentâneo vence até a próxima troca.
import { t } from "../i18n";
import { relogio, semExt, nomeDe } from "../dom";
import type { Sinal, Vista } from "../tipos";

export const ICONE_SINAL: Record<Sinal, string> = { info: "info", ok: "circle-check", aviso: "triangle-alert", erro: "circle-alert", espera: "hourglass", rec: "circle" };

const pct = (p: number | null) => (p == null ? "…" : `${p}%`);

function gravar(v: Vista): [Sinal, string] {
  const g = v.g, disp = t("st.disp", { mic: g.mic, sis: g.sis });
  const ausente = g.sisAusente ? ". " + t("st.ausente", { padrao: g.padraoSis }) : "";
  const rec: Sinal = g.sisAusente ? "aviso" : "rec";
  switch (v.estado.gravar) {
    case "motor-subindo": return ["espera", t("st.g.motor-subindo")];
    case "pronto": return ["info", t("st.g.pronto", { disp })];
    case "gravando": return [rec, t("st.g.gravando", { disp }) + ausente];
    case "gravando-ao-vivo": return [rec, t("st.g.gravando-ao-vivo", { disp }) + ausente];
    case "nota-gravando": return ["rec", t("st.g.nota-gravando", { mic: g.mic })];
    case "pausado": return ["info", t("st.g.pausado", { tempo: relogio(g.segundos) })];
    case "parado": return ["info", t("st.g.parado", { nome: g.arquivo, tempo: relogio(g.segundos) })];
    case "transcrevendo": return ["espera", t("st.g.transcrevendo", { tarefa: t(`g.tarefa-${g.tarefa}`), pct: pct(g.pct), nome: g.arquivo })];
    case "transcricao-pronta": return ["ok", t(g.tarefa === "nota" ? "st.g.nota-pronta" : "st.g.transcricao-pronta", { txt: nomeDe(g.txt) })];
    default: return ["erro", g.erro.linha];
  }
}

function biblioteca(v: Vista): [Sinal, string] {
  const b = v.b, item = b.sel != null ? b.itens[b.sel] : undefined;
  const ativo = b.itens.find((i) => i.path === (b.trPath ?? b.resumoPath)) ?? item;
  switch (v.estado.biblioteca) {
    case "vazia": return ["info", t("st.b.vazia", { pasta: b.pasta })];
    case "lista": return ["info", t(b.itens.length === 1 ? "st.b.lista-1" : "st.b.lista", { n: b.itens.length, pasta: b.pasta })];
    case "selecionada": {
      if (!item) return ["info", ""];
      // gravando, o Transcrever da lista fica desabilitado (disputa o motor): o motivo vai junto (DESIGN.md)
      const espera = v.ocupado || v.g.ocupadoFora ? ". " + t("st.b.transcrever-espera") : "";
      return ["info", t(item.temTexto ? "st.b.selecionada" : "st.b.selecionada-sem", { nome: item.nome, dur: item.duracao }) + espera];
    }
    case "transcrevendo-item": return ["espera", t("st.b.transcrevendo-item", { pct: pct(b.trPct), nome: ativo?.nome ?? "" })];
    case "resumindo": return ["espera", t("st.b.resumindo", { nome: ativo?.nome ?? "" })];
    case "busca-sem-resultado": return ["info", t("st.b.busca-sem-resultado", { busca: b.busca })];
    default: return ["erro", t("st.b.erro", { pasta: b.pasta, detalhe: b.erro })];
  }
}

function arquivo(v: Vista): [Sinal, string] {
  const a = v.a, nome = a.origem?.nome ?? "";
  switch (v.estado.arquivo) {
    case "nada-escolhido": return ["info", t("st.a.nada-escolhido")];
    case "escolhido": return ["info", t("st.a.escolhido", { nome })];
    case "transcrevendo": return ["espera", t("st.a.transcrevendo", { pct: pct(a.pct), nome })];
    case "convertendo": return ["espera", t("st.a.convertendo", { pct: pct(a.pct), nome })];
    case "pronto": return ["ok", t(a.tarefa === "converter" ? "st.a.pronto-mp3" : "st.a.pronto-txt", { saida: a.saida })];
    default: return ["erro", a.erroLinha];
  }
}

function opcoes(v: Vista): [Sinal, string] {
  switch (v.estado.opcoes) {
    case "normal": return ["info", t("st.o.normal")];
    case "durante-gravacao": return ["info", t("st.o.durante-gravacao")];
    default: return ["aviso", t("st.o.dispositivo-ausente", { padrao: v.o.padraoSis })];
  }
}

export function linhaStatus(v: Vista): [Sinal, string] {
  if (v.aviso) return v.aviso;
  if (v.tela === "gravar") return gravar(v);
  if (v.tela === "biblioteca") return biblioteca(v);
  if (v.tela === "arquivo") return arquivo(v);
  return opcoes(v);
}

export const nomeTxt = (mp3: string): string => semExt(nomeDe(mp3)) + ".txt";

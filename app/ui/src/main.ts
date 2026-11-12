// Interface do Reco (Fase 3, passos 11 a 13): monta os ícones, liga os gestos e o motor, e desenha a Vista.
// Fora do Tauri usa o backend falso e expõe o condutor de estados (window.vitrine) para os testes da Fase 1.
import "./estilo/base.css";
import "./estilo/gravar.css";
import "./estilo/telas.css";
import "./estilo/skins.css";
import { obterBackend } from "./backend";
import { criarApp } from "./app";
import { criarCondutor, parametrosDaUrl } from "./condutor";
import { ligarGestos } from "./controle/cliques";
import { iniciarMotor, ouvirMotor } from "./controle/motor";
import { montarIcones } from "./icones";
import { ligarMedidores } from "./vu";
import * as ganho from "./ganho";

async function iniciar(): Promise<void> {
  montarIcones();
  const be = await obterBackend();
  const app = criarApp(be);
  app.desenhar();
  ligarGestos(app);
  ligarMedidores(app.r);
  ouvirMotor(app);
  if (be.isMock) {
    const w = window as unknown as Record<string, unknown>;
    w.vitrine = criarCondutor(app);
    w.__recoTeste = { ganho, app };
    const ini = parametrosDaUrl();
    if (ini) { (w.vitrine as ReturnType<typeof criarCondutor>).definir(ini); return; }
  }
  await iniciarMotor(app);
}

void iniciar();

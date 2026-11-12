// passo17.cjs: os defeitos do teste real (passo 17 da Fase 3) que a tela resolve, provados contra a interface real com
// o backend falso. Uso: npm --prefix app run ui:build && node app/ui/tests/passo17.cjs  →  "passo17: falhas 0" (saída 0).
// Cobre: (1) `busy` no Gravar (nota logo depois de abrir, com a checagem do modelo ocupando a vaga) nunca some calado:
// a tela fica em Pronto com o motivo no status, e o clique seguinte grava; (2) Entrada, Saída e o status de Pronto com
// os nomes dos dispositivos antes da 1ª gravação (o motor manda o NOME do padrão em `console`/`comm`, não o id), e
// "Automático (padrão do Windows)" quando o Windows não diz o padrão.
'use strict';
const { playwright, servir, placar, abrir, esperarEstado, clicar, statusTexto } = require('./comum.cjs');

const p = placar();
const texto = (page, ref) => page.$eval(`[data-ref="${ref}"]`, (e) => e.textContent);

async function busyNaoSomeCalado(page) {
  await page.click('[data-acao="modo"][data-modo="nota"]');
  await page.evaluate(() => { const m = window.__recoMock; m.recusar['rec.start'] = 'busy'; m.vagaOcupada = true; });
  await clicar(page, 'principal');
  await page.waitForTimeout(300);
  let st = await statusTexto(page);
  p.conferir('nota recusada com busy (checagem do modelo em voo): fica em Pronto e diz o motivo',
    await esperarEstado(page, 'gravar', 'pronto', 500) && /ocupado com uma transcrição ou uma atualização do modelo/.test(st), st);
  await page.evaluate(() => { window.__recoMock.vagaOcupada = false; });
  await clicar(page, 'principal');
  p.conferir('o clique seguinte grava a nota', await esperarEstado(page, 'gravar', 'nota-gravando'));
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'transcricao-pronta', 10000);
  await page.click('[data-acao="modo"][data-modo="gravacao"]');
  await page.evaluate(() => { window.__recoMock.recusar['rec.start'] = 'busy'; });
  await clicar(page, 'principal');
  await page.waitForTimeout(300);
  st = await statusTexto(page);
  p.conferir('gravação recusada com busy e o motor livre ao reler: diz para tentar de novo',
    /Não deu agora/.test(st) && !/Pronto para gravar/.test(st), st);
  await clicar(page, 'principal');
  p.conferir('e o clique seguinte grava', await esperarEstado(page, 'gravar', 'gravando'));
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'parado');
  await clicar(page, 'excluir');
  await esperarEstado(page, 'gravar', 'pronto');
}

async function nomesAntesDeGravar(page) {
  const mic = await texto(page, 'info-mic'), sis = await texto(page, 'info-sis'), st = await statusTexto(page);
  p.conferir('antes da 1ª gravação: Entrada e Saída com o nome do padrão do Windows',
    mic === 'Microfone (Realtek(R) Audio)' && sis === 'Alto-falantes (Realtek(R) Audio)', `${mic} | ${sis}`);
  p.conferir('status de Pronto com os dois nomes', st.includes('Microfone: Microfone (Realtek(R) Audio) · Sistema: Alto-falantes (Realtek(R) Audio)'), st);
}

const aba = (page, tela) => page.click(`.abas [data-tela="${tela}"]`, { force: true });

async function semPadrao(page) {
  await page.evaluate(() => { window.__recoMock.semPadrao = true; });
  await aba(page, 'opcoes');
  await clicar(page, 'atualizar-disp');
  await page.waitForTimeout(200);
  await aba(page, 'gravar');
  await page.waitForTimeout(100);
  const mic = await texto(page, 'info-mic'), sis = await texto(page, 'info-sis'), st = await statusTexto(page);
  p.conferir('Windows sem padrão: "Automático (padrão do Windows)" no lugar do nome vazio',
    mic === 'Automático (padrão do Windows)' && sis === 'Automático (padrão do Windows)' && /Microfone: Automático/.test(st), `${mic} | ${sis} | ${st}`);
  await page.evaluate(() => { window.__recoMock.semPadrao = false; });
}

(async () => {
  const srv = await servir();
  const base = `http://127.0.0.1:${srv.address().port}/`;
  const browser = await playwright().chromium.launch();
  try {
    const { ctx, page, erros } = await abrir(browser, base);
    await esperarEstado(page, 'gravar', 'pronto');
    await page.waitForTimeout(200);
    await nomesAntesDeGravar(page);
    await busyNaoSomeCalado(page);
    await semPadrao(page);
    p.conferir('nenhum erro de página', !erros.length, erros.join(' | '));
    await ctx.close();
  } finally {
    await browser.close();
    srv.close();
  }
  console.log(`passo17: falhas ${p.falhas()} em ${p.total()} verificações`);
  process.exit(p.falhas() ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });

// paridade.cjs: a tabela de paridade do md da Fase 3 vira verificação (passo 15). Lê os ids da própria tabela
// (roadmap/2026-11-11-melhoria-reco-em-rust-fase-3.md, "Tabela de paridade"): cada linha com prova "tela" tem um
// elemento [data-paridade="<id>"] na interface real; nenhum data-paridade fora da tabela. As linhas "rust" (bandeja,
// instancia) não têm elemento: a prova delas são os cargo test dos passos 7 a 9.
// Uso: npm --prefix app run ui:build && node app/ui/tests/paridade.cjs  →  "17 de 17 presentes" (saída 0).
'use strict';
const fs = require('fs');
const path = require('path');
const { playwright, servir } = require('./comum.cjs');

// PARIDADE_MD: outro md (só para o controle negativo, com uma linha a mais ou a menos)
const MD = process.env.PARIDADE_MD || path.resolve(__dirname, '..', '..', '..', 'roadmap', '2026-11-11-melhoria-reco-em-rust-fase-3.md');

function lerTabela() {
  const md = fs.readFileSync(MD, 'utf8');
  const secao = md.split(/^## Tabela de paridade.*$/m)[1];
  if (!secao) throw new Error('md sem a seção "## Tabela de paridade"');
  const linhas = secao.split(/^## /m)[0].split('\n').filter((l) => /^\| [a-z0-9-]+ \|/.test(l) && !/^\| (id|-+) \|/.test(l));
  return linhas.map((l) => { const c = l.split('|').map((x) => x.trim()); return { id: c[1], prova: c[c.length - 2] }; });
}

(async () => {
  const tabela = lerTabela();
  const tela = tabela.filter((x) => x.prova === 'tela').map((x) => x.id), rust = tabela.filter((x) => x.prova === 'rust').map((x) => x.id);
  const outras = tabela.filter((x) => x.prova !== 'tela' && x.prova !== 'rust');
  const srv = await servir();
  const browser = await playwright().chromium.launch();
  let achados;
  try {
    const page = await browser.newPage({ viewport: { width: 400, height: 560 } });
    await page.goto(`http://127.0.0.1:${srv.address().port}/`);
    await page.waitForFunction(() => window.vitrine);
    achados = await page.evaluate(() => [...document.querySelectorAll('[data-area=janela] [data-paridade]')].map((e) => e.dataset.paridade));
  } finally {
    await browser.close();
    srv.close();
  }
  const falhas = [];
  for (const id of tela) if (!achados.includes(id)) falhas.push(`falta [data-paridade="${id}"] (função do app velho sem tela no novo)`);
  for (const id of new Set(achados)) if (!tela.includes(id)) falhas.push(`sobra [data-paridade="${id}"]: não está na tabela${rust.includes(id) ? ' (é linha "rust")' : ''}`);
  for (const id of tela) if (achados.filter((x) => x === id).length > 1) falhas.push(`[data-paridade="${id}"] repetido`);
  outras.forEach((x) => falhas.push(`linha "${x.id}" com prova "${x.prova}" (esperado tela ou rust)`));
  falhas.forEach((f) => console.log('FALHA ' + f));
  const presentes = tela.filter((id) => achados.includes(id)).length;
  console.log(`linhas da tabela: ${tabela.length} (${tela.length} tela, ${rust.length} rust: ${rust.join(', ')})`);
  console.log(`${presentes} de ${tela.length} presentes`);
  process.exit(falhas.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });

// comum.cjs: o que os testes da interface (gravar.cjs, telas.cjs, paridade.cjs) dividem. Servem app/ui/dist (o build
// do `npm --prefix app run ui:build`) por HTTP local numa porta livre, com o backend falso, e abrem no Chromium do
// Playwright (mesma busca dos testes da Fase 1: PLAYWRIGHT_CORE, playwright-core, playwright, o global de `npm root -g`).
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');
const { execSync } = require('child_process');

const DIST = path.resolve(__dirname, '..', 'dist');
const TIPOS = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml' };

function playwright() {
  for (const nome of [process.env.PLAYWRIGHT_CORE, 'playwright-core', 'playwright'].filter(Boolean)) {
    try { return require(nome); } catch { /* tenta o próximo */ }
  }
  try { return require(path.join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'playwright')); } catch { /* sem global */ }
  throw new Error('Playwright não encontrado (PLAYWRIGHT_CORE, playwright-core, playwright ou o global de `npm root -g`)');
}

function servir() {
  if (!fs.existsSync(path.join(DIST, 'index.html'))) throw new Error('app/ui/dist não existe: rode antes npm --prefix app run ui:build');
  const srv = http.createServer((q, s) => {
    let p = path.join(DIST, decodeURIComponent(q.url.split('?')[0]));
    if (p.endsWith(path.sep)) p = path.join(p, 'index.html');
    if (!p.startsWith(DIST) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { s.writeHead(404); s.end(); return; }
    s.writeHead(200, { 'content-type': TIPOS[path.extname(p)] || 'application/octet-stream' });
    fs.createReadStream(p).pipe(s);
  });
  return new Promise((ok) => srv.listen(0, '127.0.0.1', () => ok(srv)));
}

/** Contador de falhas com uma linha "ok"/"FALHA" por verificação. */
function placar() {
  let falhas = 0, n = 0;
  const conferir = (nome, ok, detalhe = '') => {
    n += 1;
    if (ok) console.log(`ok    ${nome}`);
    else { falhas += 1; console.log(`FALHA ${nome}${detalhe ? ': ' + detalhe : ''}`); }
    return ok;
  };
  return { conferir, falhas: () => falhas, total: () => n };
}

/** Abre a interface (sem condutor: o controle de verdade dirigindo o backend falso) e espera o motor falso ficar pronto. */
async function abrir(browser, base, { velocidade = 10, query = '' } = {}) {
  const ctx = await browser.newContext({ viewport: { width: 400, height: 560 } });
  const page = await ctx.newPage();
  const erros = [];
  page.on('pageerror', (e) => erros.push(e.message));
  await page.goto(base + query);
  await page.waitForFunction(() => window.__recoMock && window.vitrine);
  await page.evaluate((v) => { window.__recoMock.velocidade = v; }, velocidade);
  return { ctx, page, erros };
}

/** Espera a tela `tela` chegar ao `estado` (pela Vista, window.vitrine.estado()). */
async function esperarEstado(page, tela, estado, ms = 8000) {
  try {
    await page.waitForFunction(([t, e]) => window.vitrine.estado().estados[t] === e, [tela, estado], { timeout: ms });
    return true;
  } catch {
    return false;
  }
}

const estadoAgora = (page, tela) => page.evaluate((t) => window.vitrine.estado().estados[t], tela);
const chamadas = (page) => page.evaluate(() => window.__recoMock.chamadas.map((c) => ({ cmd: c.cmd, args: c.args })));
const clicar = (page, acao) => page.click(`.tela[data-ativa] [data-acao="${acao}"], .titulo [data-acao="${acao}"], .abas [data-acao="${acao}"]`);
const statusTexto = (page) => page.$eval('[data-ref="status-texto"]', (e) => e.textContent);

module.exports = { playwright, servir, placar, abrir, esperarEstado, estadoAgora, chamadas, clicar, statusTexto };

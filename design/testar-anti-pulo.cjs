// testar-anti-pulo.cjs: prova que a janela e cada área (data-area) não mudam de tamanho nem de lugar (DESIGN.md R1, R2).
// Uso (da raiz do repo, depois de node design/montar-vitrine.cjs):
//   node design/testar-anti-pulo.cjs                 percorre a vitrine (design/vitrine.html servida por HTTP local)
//   node design/testar-anti-pulo.cjs --url <endereço> outro alvo com o mesmo condutor de estados (Fase 3: a interface real)
//   node design/testar-anti-pulo.cjs --sabotar       controle negativo: tira a linha única do status; tem de sair 1
//                                                    (e acusar em cada skin; se uma não acusa, ela não foi medida: sai 2)
// Cada medida confere que há uma janela visível só e que ela está na skin pedida (data-direcao).
// Matriz: direção × escala (1; 1,25; 1,5) × tema × texto (normal, longo PT, longo EN) × versão nova × tela × estado.
// Linha de base por direção e escala; tema, texto, versão e estado mudam conteúdo, nunca caixa. Saída 0 = nada pulou.
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');
const { execSync } = require('child_process');

const args = process.argv.slice(2);
const SABOTAR = args.includes('--sabotar');
const URL_ALVO = args.includes('--url') ? args[args.indexOf('--url') + 1] : null;
const ESCALAS = [1, 1.25, 1.5];
const SABOTAGEM = '[data-area=status]{white-space:normal!important;height:auto!important;overflow:visible!important}';

// Playwright na ordem combinada com a Fase 3: PLAYWRIGHT_CORE, playwright-core, playwright, global de `npm root -g`.
function playwright() {
  for (const nome of [process.env.PLAYWRIGHT_CORE, 'playwright-core', 'playwright'].filter(Boolean)) {
    try { return require(nome); } catch { /* tenta o próximo */ }
  }
  try { return require(path.join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'playwright')); } catch { /* sem global */ }
  throw new Error('Playwright não encontrado (PLAYWRIGHT_CORE, playwright-core, playwright ou o global de `npm root -g`)');
}

// serve design/ por HTTP local numa porta livre (o Chromium do MCP bloqueia file://)
function servir() {
  const pasta = __dirname;
  const srv = http.createServer((q, s) => {
    const p = path.join(pasta, decodeURIComponent(q.url.split('?')[0]));
    if (!p.startsWith(pasta) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { s.writeHead(404); s.end(); return; }
    s.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    fs.createReadStream(p).pipe(s);
  });
  return new Promise((ok) => srv.listen(0, '127.0.0.1', () => ok(srv)));
}

// roda dentro da página: percorre a matriz de uma direção e compara cada caixa com a linha de base
function percorrer({ direcao, globais }) {
  const v = window.vitrine;
  const visivel = (e) => e.checkVisibility({ visibilityProperty: true });
  const caixa = (e) => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; };
  const base = {}, falhas = [];
  let n = 0;
  for (const tema of ['claro', 'escuro']) for (const texto of ['normal', 'longo-pt', 'longo-en']) for (const versao of ['nao', 'sim']) {
    for (const tela of v.telas) for (const estado of v.estados[tela]) {
      const p = { tela, estado, tema, texto, versao };
      if (direcao) p.direcao = direcao;
      v.definir(p);
      const vistas = [...document.querySelectorAll('[data-area="janela"]')].filter(visivel), janela = vistas[0];
      if (vistas.length !== 1) { falhas.push({ combo: p, area: `janela (${vistas.length} visíveis, o esperado é 1)`, base: null, agora: null }); continue; }
      // a janela medida tem de estar na skin pedida (no atributo dela, na vitrine, ou no <html>, no app); senão B e C passariam medindo a A
      const skin = (janela.closest('[data-direcao]') || document.documentElement).dataset.direcao;
      if (direcao && skin !== direcao) { falhas.push({ combo: p, area: `skin (medida a ${skin || 'nenhuma'})`, base: null, agora: null }); continue; }
      const areas = [janela, ...[...janela.querySelectorAll('[data-area]')].filter(visivel)];
      for (const a of areas) {
        const nome = a.dataset.area;
        const chave = globais.includes(nome) ? nome : tela + '/' + nome;
        const agora = caixa(a);
        n += 1;
        if (!base[chave]) { base[chave] = agora; continue; }
        if (agora.some((x, i) => x !== base[chave][i])) falhas.push({ combo: p, area: nome, base: base[chave], agora });
      }
    }
  }
  const j = base.janela;
  if (j && v.direcoes && (j[2] !== 400 || j[3] !== 560)) falhas.push({ combo: { direcao }, area: 'janela-tamanho', base: [0, 0, 400, 560], agora: j });
  return { n, falhas };
}

(async () => {
  const srv = URL_ALVO ? null : await servir();
  const alvo = URL_ALVO || `http://127.0.0.1:${srv.address().port}/vitrine.html`;
  const browser = await playwright().chromium.launch();
  let total = 0;
  const falhas = [], medidas = new Set();
  try {
    for (const escala of ESCALAS) {
      const ctx = await browser.newContext({ viewport: { width: 1400, height: 1200 }, deviceScaleFactor: escala });
      const page = await ctx.newPage();
      const erros = [];
      page.on('pageerror', (e) => erros.push(e.message));
      await page.goto(alvo);
      await page.waitForFunction(() => window.vitrine && typeof window.vitrine.definir === 'function');
      if (SABOTAR) await page.addStyleTag({ content: SABOTAGEM });
      const direcoes = (await page.evaluate(() => window.vitrine.direcoes)) || [null];
      for (const direcao of direcoes) {
        medidas.add(direcao);
        const r = await page.evaluate(percorrer, { direcao, globais: ['janela', 'titulo', 'abas', 'conteudo', 'status'] });
        total += r.n;
        r.falhas.forEach((f) => falhas.push({ ...f, escala }));
      }
      if (erros.length) falhas.push({ combo: { escala }, area: 'erro-de-pagina: ' + erros.join(' | '), base: null, agora: null });
      await ctx.close();
    }
  } finally {
    await browser.close();
    if (srv) srv.close();
  }
  const fmt = (c) => (c ? c.map((x) => Math.round(x * 100) / 100).join(',') : '-');
  const combo = (f) => Object.entries({ escala: f.escala, ...f.combo }).map(([k, v]) => `${k}=${v}`).join(' ');
  falhas.slice(0, 60).forEach((f) => console.log(`FALHA ${combo(f)} área=${f.area} base=${fmt(f.base)} agora=${fmt(f.agora)}`));
  if (falhas.length > 60) console.log(`… mais ${falhas.length - 60} falhas`);
  console.log(`anti-pulo: ${falhas.length} diferenças em ${total} medições`);
  // controle negativo por skin: a sabotagem tem de aparecer em cada direção; se uma não acusa, ela não foi medida (saída 2)
  const mudas = SABOTAR ? [...medidas].filter((d) => !falhas.some((f) => f.area === 'status' && (f.combo.direcao || null) === d)) : [];
  if (mudas.length) { console.log(`sabotagem sem efeito na direção ${mudas.join(', ')}: o teste não mede essa skin`); process.exit(2); }
  process.exit(falhas.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });

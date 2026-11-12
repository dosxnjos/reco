// testar-contrato.cjs: confere as regras R3 a R15 do DESIGN.md que não são caixa de área (essas são do testar-anti-pulo).
// Uso (da raiz do repo, depois de node design/montar-vitrine.cjs):
//   node design/testar-contrato.cjs                  vitrine local (design/vitrine.html por HTTP local)
//   node design/testar-contrato.cjs --url <endereço>  outro alvo com o mesmo condutor de estados (Fase 3)
//   node design/testar-contrato.cjs --sabotar        controle negativo: botão que encolhe no clique; tem de sair 1
// Uma linha "ok" ou "FALHA" por regra e direção; a última diz o total. Saída 0 = contrato cumprido.
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');
const { execSync } = require('child_process');

const args = process.argv.slice(2);
const SABOTAR = args.includes('--sabotar');
const URL_ALVO = args.includes('--url') ? args[args.indexOf('--url') + 1] : null;
const SABOTAGEM = 'button:active{transform:scale(.98)}';
const TRANSICAO_OK = ['opacity', 'color', 'background-color', 'border-color', 'outline-color', 'fill', 'stroke'];

function playwright() {
  for (const nome of [process.env.PLAYWRIGHT_CORE, 'playwright-core', 'playwright'].filter(Boolean)) {
    try { return require(nome); } catch { /* tenta o próximo */ }
  }
  try { return require(path.join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'playwright')); } catch { /* sem global */ }
  throw new Error('Playwright não encontrado (PLAYWRIGHT_CORE, playwright-core, playwright ou o global de `npm root -g`)');
}

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

let falhas = 0;
const relatar = (regra, dir, problemas, resumo) => {
  const rotulo = `${regra} [${dir || 'alvo'}]`;
  if (!problemas.length) { console.log(`ok    ${rotulo}${resumo ? ' ' + resumo : ''}`); return; }
  falhas += problemas.length;
  problemas.slice(0, 8).forEach((p) => console.log(`FALHA ${regra.startsWith('R6') ? 'clique-move' : regra} [${dir || 'alvo'}] ${p}`));
  if (problemas.length > 8) console.log(`FALHA ${rotulo} … mais ${problemas.length - 8}`);
};

// ---- funções que rodam dentro da página (recebem a direção e devolvem a lista de problemas)
const NA_PAGINA = `
window.__t = {
  combos() { const v = window.vitrine; return v.telas.flatMap((tela) => v.estados[tela].map((estado) => ({ tela, estado }))); },
  ir(p, dir) { if (dir) p.direcao = dir; window.vitrine.definir(p); },
  janela() { return [...document.querySelectorAll('[data-area="janela"]')].find((e) => e.checkVisibility({ visibilityProperty: true })); },
  visivel(e) { return e.checkVisibility({ visibilityProperty: true, opacityProperty: true }) && !e.closest('[inert]'); },
  nome(e) { return String(e.getAttribute('aria-label') || e.innerText || e.getAttribute('class') || e.tagName).trim().replace(/\\s+/g, ' ').slice(0, 40); },
};`;

function porEstado({ dir, texto, permitidas }) {
  const t = window.__t, out = [];
  const displays = new Map();
  for (const c of t.combos()) {
    t.ir({ ...c, texto, tema: 'claro', versao: 'sim' }, dir);
    const j = t.janela(), onde = `${c.tela}/${c.estado}`;
    j.querySelectorAll('[data-num]').forEach((e) => { if (!getComputedStyle(e).fontVariantNumeric.includes('tabular-nums')) out.push(['R4', `${onde} sem tabular-nums: ${t.nome(e)}`]); });
    [j, ...j.querySelectorAll('*')].forEach((e, i) => {
      const cs = getComputedStyle(e);
      const props = cs.transitionProperty.split(',').map((x) => x.trim()), durs = cs.transitionDuration.split(',').map((x) => parseFloat(x));
      props.forEach((p, k) => { if (durs[k % durs.length] > 0 && !permitidas.includes(p)) out.push(['R5', `${onde} transição de "${p}" em ${t.nome(e)}`]); });
      const chave = i + ':' + e.tagName;
      if (!displays.has(chave)) displays.set(chave, cs.display);
      else if (displays.get(chave) !== cs.display) out.push(['R7', `${onde} display ${displays.get(chave)} -> ${cs.display} em ${t.nome(e)}`]);
      if (/(auto|scroll)/.test(cs.overflowX + cs.overflowY) && !cs.scrollbarGutter.includes('stable')) out.push(['R8', `${onde} rola sem scrollbar-gutter: stable: ${t.nome(e)}`]);
      if (e.tagName === 'IMG' || /url\([^)]*\.(png|jpe?g|gif|bmp)/i.test(cs.backgroundImage)) out.push(['R10', `${onde} bitmap em ${t.nome(e)}`]);
      if (e.tagName === 'A') out.push(['R15', `${onde} link <a> na janela: ${t.nome(e)}`]);
      if (e.tagName === 'svg' && !e.hasAttribute('data-marca') && !e.hasAttribute('data-lucide') && !e.closest('symbol')) out.push(['R13', `${onde} svg sem data-lucide`]);
      if (e.tagName === 'use') { const h = e.getAttribute('href'); if (!h || !document.querySelector(h)) out.push(['R13', `${onde} ícone inexistente ${h}`]); }
    });
    j.querySelectorAll('[data-sinal]').forEach((e) => { if (!e.querySelector('svg') || !e.textContent.trim()) out.push(['R12', `${onde} sinal sem ícone ou sem texto: ${t.nome(e)}`]); });
    const emoji = (j.innerText.match(/\p{Extended_Pictographic}/gu) || []);
    if (emoji.length) out.push(['R13', `${onde} emoji no texto: ${emoji.join(' ')}`]);
    j.querySelectorAll('[role="tablist"] button').forEach((b) => { if (b.getAttribute('role') !== 'tab') out.push(['R15', `${onde} aba sem role=tab: ${t.nome(b)}`]); });
    j.querySelectorAll('button').forEach((b) => { if (!b.closest('[data-area="titulo"]') && t.visivel(b) && !b.innerText.trim()) out.push(['R15', `${onde} botão sem texto visível: ${b.outerHTML.slice(0, 60)}`]); });
    const st = j.querySelector('[data-area="status"]');
    if (st) {
      const tx = st.querySelector('.status-texto') || st, cs = getComputedStyle(tx);
      if (cs.whiteSpace !== 'nowrap' || cs.textOverflow !== 'ellipsis' || cs.overflowX !== 'hidden') out.push(['R3', `${onde} status sem nowrap/ellipsis/hidden`]);
      if (st.title !== tx.textContent) out.push(['R3', `${onde} title do status diferente do texto`]);
      if (texto !== 'normal' && c.tela === 'gravar' && c.estado === 'gravando' && !(tx.scrollWidth > tx.clientWidth)) out.push(['R3', `${onde} texto longo não corta`]);
    }
  }
  // regras de folha: keyframes só com opacity; :hover não mexe em display/visibility/opacity de outro elemento
  for (const folha of document.styleSheets) for (const r of folha.cssRules) {
    if (r instanceof CSSKeyframesRule) for (const k of r.cssRules) for (let i = 0; i < k.style.length; i++) if (k.style[i] !== 'opacity') out.push(['R5', `@keyframes ${r.name} anima ${k.style[i]}`]);
    if (r instanceof CSSStyleRule && r.selectorText.includes(':hover')) {
      const outro = r.selectorText.split(',').some((sel) => /:hover[^,]*[\s>+~]\S/.test(sel.trim()));
      if (outro && ['display', 'visibility', 'opacity'].some((p) => r.style.getPropertyValue(p))) out.push(['R15', `:hover mostra ou esconde outro elemento: ${r.selectorText}`]);
    }
  }
  return out;
}

function contraste({ dir, tema }) {
  const t = window.__t, out = [];
  const rgba = (s) => { const m = s.match(/[\d.]+/g).map(Number); return [m[0], m[1], m[2], m.length > 3 ? m[3] : 1]; };
  const lum = (c) => { const f = c.slice(0, 3).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
  const misturar = (a, b) => [0, 1, 2].map((i) => a[i] * a[3] + b[i] * (1 - a[3])).concat(1);
  const fundo = (e) => { const pilha = []; for (let x = e; x; x = x.parentElement) { const c = rgba(getComputedStyle(x).backgroundColor); if (c[3] > 0) { pilha.push(c); if (c[3] >= 1) break; } } let r = [255, 255, 255, 1]; for (const c of pilha.reverse()) r = misturar(c, r); return r; };
  for (const c of t.combos()) {
    t.ir({ ...c, tema, texto: 'normal', versao: 'sim' }, dir);
    const j = t.janela();
    for (const e of j.querySelectorAll('*')) {
      if (![...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
      if (e.tagName === 'OPTION' || !t.visivel(e) || e.closest(':disabled,[aria-disabled="true"],[aria-hidden="true"]')) continue;
      const cs = getComputedStyle(e), cor = misturar(rgba(cs.color), fundo(e)), bg = fundo(e);
      const a = lum(cor), b = lum(bg), razao = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      const px = parseFloat(cs.fontSize), grande = px >= 24 || (px >= 18.66 && Number(cs.fontWeight) >= 700);
      if (razao < (grande ? 3 : 4.5)) out.push(`${tema} ${c.tela}/${c.estado} ${razao.toFixed(2)}:1 em "${t.nome(e)}" (${cs.color} sobre rgb(${bg.slice(0, 3).map(Math.round).join(',')}))`);
    }
  }
  return [...new Set(out)];
}

async function cliqueParado(page, dir) {
  const out = [];
  let n = 0;
  const combos = await page.evaluate(() => window.__t.combos());
  for (const c of combos) {
    await page.evaluate(([p, d]) => window.__t.ir({ ...p, tema: 'claro', texto: 'normal', versao: 'sim' }, d), [c, dir]);
    const qtd = await page.evaluate(() => {
      const t = window.__t, j = t.janela();
      const vista = (e) => { const r = e.getBoundingClientRect(); for (let x = e.parentElement; x && x !== j; x = x.parentElement) { if (getComputedStyle(x).overflowY !== 'visible') { const q = x.getBoundingClientRect(); if (r.top < q.top || r.bottom > q.bottom) return false; } } return true; };
      const bs = [...j.querySelectorAll('button')].filter((b) => t.visivel(b) && !b.disabled && vista(b));
      document.querySelectorAll('[data-teste-botao]').forEach((b) => b.removeAttribute('data-teste-botao'));
      bs.forEach((b, i) => b.setAttribute('data-teste-botao', i));
      return bs.length;
    });
    for (let i = 0; i < qtd; i++) {
      const sel = `[data-teste-botao="${i}"]`;
      const caixa = () => page.$eval(sel, (e) => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map((x) => Math.round(x * 100) / 100).join(','); });
      const nome = await page.$eval(sel, (e) => window.__t.nome(e));
      const antes = await caixa();
      const [x, y] = antes.split(',').map(Number);
      const [w, h] = antes.split(',').slice(2).map(Number);
      await page.mouse.move(x + w / 2, y + h / 2);
      const hover = await caixa();
      await page.mouse.down();
      const apertado = await caixa();
      await page.mouse.move(2, 2);
      await page.mouse.up();
      const depois = await caixa();
      n += 1;
      if (hover !== antes || apertado !== antes || depois !== antes) out.push(`${c.tela}/${c.estado} "${nome}" base=${antes} hover=${hover} apertado=${apertado} depois=${depois}`);
    }
  }
  return { out, n };
}

async function teclado(page, dir) {
  const out = [];
  const telas = [['gravar', 'pronto'], ['gravar', 'gravando'], ['gravar', 'parado'], ['gravar', 'transcricao-pronta'], ['gravar', 'erro'], ['gravar', 'erro-detalhe'],
    ['biblioteca', 'selecionada'], ['biblioteca', 'vazia'], ['arquivo', 'escolhido'], ['opcoes', 'normal']];
  for (const [tela, estado] of telas) {
    const esperado = await page.evaluate(([p, d]) => {
      const t = window.__t; t.ir({ ...p, tema: 'claro', texto: 'normal', versao: 'sim' }, d);
      const j = t.janela();
      document.querySelectorAll('[data-teste-tab]').forEach((e) => e.removeAttribute('data-teste-tab'));
      return [...j.querySelectorAll('button')].filter((b) => t.visivel(b) && !b.disabled).map((b, i) => { b.setAttribute('data-teste-tab', i); return i; }).length;
    }, [{ tela, estado }, dir]);
    await page.evaluate(() => { const b = [...document.querySelectorAll('.controles button, body > *:first-child')].filter((e) => e.checkVisibility()).pop(); if (b) b.focus(); });
    const vistos = new Set();
    let entrou = false;
    for (let k = 0; k < 120; k++) {
      await page.keyboard.press('Tab');
      const r = await page.evaluate(() => {
        const a = document.activeElement, j = window.__t.janela();
        if (!a || !j.contains(a)) return null;
        const cs = getComputedStyle(a);
        return { i: a.getAttribute('data-teste-tab'), larg: cs.outlineStyle === 'none' ? 0 : parseFloat(cs.outlineWidth), nome: window.__t.nome(a) };
      });
      if (!r) { if (entrou) break; continue; }
      entrou = true;
      if (r.larg < 2) out.push(`${tela}/${estado} foco sem contorno de 2 px em "${r.nome}"`);
      if (r.i !== null) vistos.add(Number(r.i));
    }
    if (vistos.size !== esperado) out.push(`${tela}/${estado} Tab alcançou ${vistos.size} de ${esperado} botões`);
  }
  return [...new Set(out)];
}

(async () => {
  const srv = URL_ALVO ? null : await servir();
  const alvo = URL_ALVO || `http://127.0.0.1:${srv.address().port}/vitrine.html`;
  const browser = await playwright().chromium.launch();
  const abrir = async (opcoes, query = '') => {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 1200 }, ...opcoes });
    const page = await ctx.newPage();
    const erros = [];
    page.on('pageerror', (e) => erros.push(e.message));
    const u = new URL(alvo);
    new URLSearchParams(query).forEach((v, k) => u.searchParams.set(k, v));
    await page.goto(u.toString());
    await page.waitForFunction(() => window.vitrine && typeof window.vitrine.definir === 'function');
    await page.addScriptTag({ content: NA_PAGINA });
    if (SABOTAR) await page.addStyleTag({ content: SABOTAGEM });
    return { ctx, page, erros };
  };
  try {
    const { ctx, page, erros } = await abrir({ colorScheme: 'light' });
    const direcoes = (await page.evaluate(() => window.vitrine.direcoes)) || [null];
    for (const dir of direcoes) {
      const lista = [];
      for (const texto of ['normal', 'longo-pt', 'longo-en']) lista.push(...await page.evaluate(porEstado, { dir, texto, permitidas: TRANSICAO_OK }));
      for (const r of ['R3', 'R4', 'R5', 'R7', 'R8', 'R10', 'R12', 'R13', 'R15']) relatar(r, dir, [...new Set(lista.filter(([x]) => x === r).map(([, m]) => m))]);
      const clique = await cliqueParado(page, dir);
      relatar('R6 clique-move', dir, clique.out, `(${clique.n} botões, antes, hover, apertado e depois)`);
      relatar('R9', dir, await teclado(page, dir));
    }
    relatar('erros-de-pagina', null, erros);
    await ctx.close();

    // R11: o sistema manda quando não há escolha; a escolha manual vence o sistema
    const fundos = {};
    for (const esquema of ['light', 'dark']) {
      const a = await abrir({ colorScheme: esquema });
      for (const dir of direcoes) for (const tema of ['sistema', 'claro', 'escuro']) {
        fundos[`${dir}|${esquema}|${tema}`] = await a.page.evaluate(([d, tm]) => { window.__t.ir({ tela: 'gravar', estado: 'pronto', tema: tm }, d); return getComputedStyle(window.__t.janela()).backgroundColor; }, [dir, tema]);
      }
      await a.ctx.close();
    }
    for (const dir of direcoes) {
      const f = (e, t) => fundos[`${dir}|${e}|${t}`], p = [];
      if (f('light', 'sistema') === f('dark', 'sistema')) p.push('claro e escuro do sistema dão o mesmo fundo');
      if (f('dark', 'claro') !== f('light', 'sistema') || f('light', 'claro') !== f('light', 'sistema')) p.push('tema=claro não vence o sistema escuro');
      if (f('light', 'escuro') !== f('dark', 'sistema') || f('dark', 'escuro') !== f('dark', 'sistema')) p.push('tema=escuro não vence o sistema claro');
      relatar('R11', dir, p);
    }

    // R14 e contraste: com movimento reduzido (sem transição no meio da medida)
    const m = await abrir({ colorScheme: 'light', reducedMotion: 'reduce' });
    for (const dir of direcoes) {
      const p = await m.page.evaluate((d) => {
        const t = window.__t, out = [];
        for (const estado of ['motor-subindo', 'gravando', 'transcrevendo']) {
          t.ir({ tela: 'gravar', estado, tema: 'claro' }, d);
          const j = t.janela();
          [j, ...j.querySelectorAll('*')].forEach((e) => {
            const cs = getComputedStyle(e);
            if (cs.transitionDuration.split(',').some((x) => parseFloat(x) > 0)) out.push(`${estado} transição com duração em ${t.nome(e)}`);
            if (e.getAnimations().length) out.push(`${estado} animação rodando em ${t.nome(e)}`);
          });
        }
        return [...new Set(out)];
      }, dir);
      relatar('R14', dir, p);
      for (const tema of ['claro', 'escuro']) relatar(`contraste ${tema}`, dir, await m.page.evaluate(contraste, { dir, tema }));
    }
    await m.ctx.close();
  } finally {
    await browser.close();
    if (srv) srv.close();
  }
  // tokens: nenhuma cor hexadecimal no modelo da vitrine, fora de tokens.css
  if (URL_ALVO) console.log('ok    tokens (não se aplica com --url)');
  else {
    const modelo = fs.readFileSync(path.join(__dirname, 'vitrine.modelo.html'), 'utf8');
    relatar('tokens', null, (modelo.match(/#[0-9a-fA-F]{3,8}\b/g) || []).map((h) => `hexadecimal ${h} em vitrine.modelo.html`));
  }
  console.log(`contrato: ${falhas} falhas`);
  process.exit(falhas ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });

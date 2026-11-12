// revisao.cjs: os achados da revisão adversarial da Fase 3 que a tela resolve, provados contra a interface real com o
// backend falso. Uso: npm --prefix app run ui:build && node app/ui/tests/revisao.cjs  →  "revisao: falhas 0" (saída 0).
// Cobre: duplo clique no principal em cada estado (um comando só), trava de pedido em voo com o motor lento, aperto
// que começou antes de o botão trocar de papel, motor fora do ar ocioso (aviso e Gravar desabilitado até voltar),
// motor caído em `stopping` sem o evento do casco (a tela não segue "gravando"), medidores zerados e tempo no alarme,
// Gravar pela bandeja com a tela em Nota, conclusão que chega antes da resposta do parar, motivo do Transcrever
// desabilitado na Biblioteca, ordem do painel igual em pronto e gravando, e skin/tema do cache antes do motor.
'use strict';
const { playwright, servir, placar, abrir, esperarEstado, chamadas, clicar, statusTexto } = require('./comum.cjs');

const p = placar();
const conta = async (page, cmd, desde = 0) => (await chamadas(page)).slice(desde).filter((c) => c.cmd === cmd).length;
const total = async (page) => (await chamadas(page)).length;
const principal = (page) => page.locator('[data-ref=principal]');
const vista = (page) => page.evaluate(() => ({ e: window.vitrine.estado().estados.gravar, d: document.querySelector('[data-ref=principal]').disabled,
  titulo: document.querySelector('[data-ref=erro-titulo]').textContent, rec: document.querySelector('[data-ref=rec-texto]').textContent,
  arquivoTravado: document.querySelector('[data-tela=arquivo]').getAttribute('aria-disabled') }));

async function limparParado(page) {
  await clicar(page, 'excluir');
  await esperarEstado(page, 'gravar', 'pronto');
}

async function duploClique(page) {
  let k = await total(page);
  await principal(page).dblclick();
  await esperarEstado(page, 'gravar', 'gravando');
  await page.waitForTimeout(200);
  p.conferir('duplo clique em Gravar: um rec.start e nenhum parar', (await conta(page, 'rec.start', k)) === 1 && (await conta(page, 'parar_gravacao', k)) === 0
    && await esperarEstado(page, 'gravar', 'gravando', 500));
  k = await total(page);
  await principal(page).dblclick();
  await esperarEstado(page, 'gravar', 'parado');
  await page.waitForTimeout(200);
  p.conferir('duplo clique em Parar: um parar_gravacao, tela em Parado e nenhum rec.conclude', (await conta(page, 'parar_gravacao', k)) === 1
    && (await conta(page, 'rec.conclude', k)) === 0 && await esperarEstado(page, 'gravar', 'parado', 500));
  k = await total(page);
  await principal(page).dblclick();
  await esperarEstado(page, 'gravar', 'pronto');
  await page.waitForTimeout(200);
  p.conferir('duplo clique em Salvar e copiar: um save e um copy_path, nenhuma gravação nova', (await conta(page, 'rec.conclude', k)) === 1
    && (await conta(page, 'copy_path', k)) === 1 && (await conta(page, 'rec.start', k)) === 0 && /Caminho copiado/.test(await statusTexto(page)));
}

async function emVoo(page) {
  const estados = [];
  await page.exposeFunction('__anotarEstado', (e) => estados.push(e));
  await page.evaluate(() => { setInterval(() => window.__anotarEstado(window.vitrine.estado().estados.gravar), 10); });
  await page.evaluate(() => { window.__recoMock.atraso['rec.start'] = 700; });
  let k = await total(page);
  await clicar(page, 'principal');
  await page.waitForTimeout(150);
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'gravando');
  await page.waitForTimeout(300);
  p.conferir('motor lento no rec.start: o 2º clique é ignorado (um rec.start, nenhum parar)', (await conta(page, 'rec.start', k)) === 1
    && (await conta(page, 'parar_gravacao', k)) === 0 && await esperarEstado(page, 'gravar', 'gravando', 500));
  await page.evaluate(() => { delete window.__recoMock.atraso['rec.start']; window.__recoMock.atraso['rec.stop'] = 700; });
  k = await total(page); estados.length = 0;
  await clicar(page, 'principal');
  await page.waitForTimeout(150);
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'parado');
  await page.waitForTimeout(200);
  p.conferir('motor lento no rec.stop: um parar_gravacao e nunca o aviso de interrompida', (await conta(page, 'parar_gravacao', k)) === 1
    && !estados.includes('erro') && await esperarEstado(page, 'gravar', 'parado', 500), JSON.stringify([...new Set(estados)]));
  await page.evaluate(() => { delete window.__recoMock.atraso['rec.stop']; });
  await limparParado(page);
}

async function apertoAntes(page) {
  const b = await principal(page).boundingBox();
  const k = await total(page);
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  await page.mouse.down();
  await page.evaluate(() => window.__recoMock.bandeja('gravar'));
  await esperarEstado(page, 'gravar', 'gravando');
  await page.mouse.up();
  await page.waitForTimeout(200);
  p.conferir('aperto em Gravar que solta depois de a bandeja começar: não vira Parar', (await conta(page, 'parar_gravacao', k)) === 0
    && await esperarEstado(page, 'gravar', 'gravando', 500));
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'parado');
  await limparParado(page);
}

async function bandejaComNota(page) {
  await page.click('[data-acao="modo"][data-modo="nota"]');
  await page.evaluate(() => window.__recoMock.bandeja('gravar'));
  const ok = await esperarEstado(page, 'gravar', 'gravando');
  const op = await page.evaluate(() => window.vitrine.estado().estados.opcoes);
  p.conferir('Gravar pela bandeja com a tela em Nota: mostra "gravando" (o modo real) e Opções em durante-gravacao', ok && op === 'durante-gravacao', op);
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'parado');
  await limparParado(page);
  await page.click('[data-acao="modo"][data-modo="gravacao"]');
}

async function conclusaoAntes(page) {
  await page.evaluate(() => { window.__recoMock.conclusaoAntes = true; });
  await page.click('[data-acao="modo"][data-modo="nota"]');
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'nota-gravando');
  await clicar(page, 'principal');
  p.conferir('conclusão antes da resposta do parar: a nota chega a "pronta" (não fica presa em transcrevendo)',
    await esperarEstado(page, 'gravar', 'transcricao-pronta', 10000));
  await page.evaluate(() => { window.__recoMock.conclusaoAntes = false; });
  await page.click('[data-acao="modo"][data-modo="gravacao"]');
}

async function motorFora(page) {
  await page.evaluate(() => window.__recoMock.derrubar({ volta: 1500 }));
  await page.waitForTimeout(100);
  const fora = await vista(page);
  p.conferir('motor caído ocioso: aviso visível na hora e Gravar desabilitado', fora.e === 'erro' && fora.d && fora.titulo === 'O motor de gravação parou'
    && /Motor fora do ar/.test(await statusTexto(page)), JSON.stringify(fora));
  const volta = await esperarEstado(page, 'gravar', 'pronto', 8000);
  p.conferir('motor de volta: o aviso some e Gravar habilita', volta && !(await vista(page)).d);
}

async function caiuParando(page) {
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'gravando');
  await page.waitForTimeout(300);
  // o motor real mostra `stopping` enquanto drena e fecha o MP3; o evento do casco se perde (achado 13)
  await page.evaluate(() => { window.__recoMock.forcarEstado('stopping'); window.__recoMock.derrubar({ semAviso: true, volta: 300 }); });
  await page.waitForTimeout(50);
  const t = await vista(page);
  const vu = await page.evaluate(() => ['mic', 'sis'].map((c) => document.querySelector(`[data-ref=barra-${c}]`).style.getPropertyValue('--nivel')));
  const st = await statusTexto(page);
  p.conferir('motor caído parando, sem o evento do casco: alarme de interrompida, nunca "Gravando", aba Arquivo livre',
    t.e === 'erro' && t.titulo === 'A gravação foi interrompida' && t.rec !== 'Gravando' && t.arquivoTravado === 'false', JSON.stringify(t));
  p.conferir('alarme: medidores zerados na hora e o tempo gravado no status', vu.every((x) => x === '0%') && /interrompida em 00:00:0\d/.test(st), JSON.stringify(vu) + ' ' + st);
  await page.waitForTimeout(1500);
  const depois = await vista(page);
  p.conferir('depois do reinício: o alarme fica e Gravar volta a habilitar', depois.e === 'erro' && depois.titulo === 'A gravação foi interrompida' && !depois.d, JSON.stringify(depois));
}

async function bibliotecaMotivo(page) {
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'gravando');
  await page.click('[data-acao="aba"][data-tela="biblioteca"]');
  await page.waitForSelector('.lista-corpo .item');
  await page.click('.lista-corpo .item');
  const r = await page.evaluate(() => ({ d: document.querySelector('[data-ref=lib-transcrever]').disabled, st: document.querySelector('[data-ref=status-texto]').textContent }));
  p.conferir('Biblioteca gravando: Transcrever desabilitado com o motivo no status', r.d && /Transcrever volta quando a gravação/.test(r.st), JSON.stringify(r));
  await page.click('[data-acao="aba"][data-tela="gravar"]');
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'parado');
  await limparParado(page);
}

async function ordemPainel(page) {
  const o = await page.evaluate(() => ['pronto', 'gravando'].map((v) => [...document.querySelectorAll(`.camada[data-variante=${v}] .linha-info b`)].map((b) => b.dataset.t).join(',')));
  p.conferir('painel: mesma ordem em pronto e gravando (Entrada, Saída, Pasta)', o[0] === o[1] && o[0] === 'g.entrada,g.saida,g.pasta', JSON.stringify(o));
}

async function cacheAparencia(browser, base) {
  const ctx = await browser.newContext({ viewport: { width: 400, height: 560 } });
  await ctx.addInitScript(() => {
    if (location.protocol.startsWith('http')) localStorage.setItem('reco.aparencia', JSON.stringify({ skin: 'c', tema: 'escuro' }));
    document.addEventListener('DOMContentLoaded', () => { window.__noDCL = [document.documentElement.dataset.direcao, document.documentElement.dataset.tema]; });
  });
  const page = await ctx.newPage();
  await page.goto(base);
  await page.waitForFunction(() => window.__recoMock && window.vitrine);
  const dcl = await page.evaluate(() => window.__noDCL);
  p.conferir('skin e tema do cache já no primeiro desenho (antes do motor responder)', dcl[0] === 'c' && dcl[1] === 'escuro', JSON.stringify(dcl));
  await esperarEstado(page, 'gravar', 'pronto');
  const depois = await page.evaluate(() => [document.documentElement.dataset.direcao, document.documentElement.dataset.tema]);
  p.conferir('depois do config do motor: a escolha guardada continua (sem trocar de cara)', depois[0] === 'c' && depois[1] === 'escuro', JSON.stringify(depois));
  await ctx.close();
}

(async () => {
  const srv = await servir();
  const base = `http://127.0.0.1:${srv.address().port}/`;
  const browser = await playwright().chromium.launch();
  try {
    const { ctx, page, erros } = await abrir(browser, base);
    await esperarEstado(page, 'gravar', 'pronto');
    await ordemPainel(page);
    await duploClique(page);
    await emVoo(page);
    await apertoAntes(page);
    await bandejaComNota(page);
    await conclusaoAntes(page);
    await bibliotecaMotivo(page);
    await motorFora(page);
    await caiuParando(page);
    p.conferir('nenhum erro de página', !erros.length, erros.join(' | '));
    await ctx.close();
    await cacheAparencia(browser, base);
  } finally {
    await browser.close();
    srv.close();
  }
  console.log(`revisao: falhas ${p.falhas()} em ${p.total()} verificações`);
  process.exit(p.falhas() ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });

// gravar.cjs: prova da tela Gravar (Fase 3, passo 12) contra a interface real com o backend falso.
// Uso: npm --prefix app run ui:build && node app/ui/tests/gravar.cjs  →  última linha "gravar: falhas 0" (saída 0).
// Cobre: motor subindo (Gravar no lugar, desabilitado), gravar/pausar/continuar/parar (sempre por parar_gravacao),
// cada saída depois de parar, nota, ao vivo com passada final, parar a transcrição, D11 (motor caído gravando),
// ganho (arrasto e teclado: rec.set_gain no máximo a cada 150 ms e config.set só ao soltar), atualização pontual
// (MutationObserver: VU sem nó criado, cronômetro só com texto), rótulos sem corte na fileira de botões do painel e a
// 1ª linha inteira do ao vivo nas 3 skins.
'use strict';
const { playwright, servir, placar, abrir, esperarEstado, chamadas, clicar, statusTexto } = require('./comum.cjs');

const p = placar();
const ultimo = async (page, cmd) => (await chamadas(page)).filter((c) => c.cmd === cmd).pop();
const conta = async (page, cmd, filtro = () => true) => (await chamadas(page)).filter((c) => c.cmd === cmd && filtro(c.args)).length;

async function gravarEParar(page) {
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'gravando');
  await page.waitForTimeout(150);
  await clicar(page, 'principal');
  return esperarEstado(page, 'gravar', 'parado');
}

async function ganhoPuro(page) {
  const r = await page.evaluate(() => {
    const g = window.__recoTeste.ganho;
    return { f: [0, 0.5, 1, 5, 10].map(g.ganhoParaFrac), g: [0, 0.25, 0.5, 0.75, 1].map(g.fracParaGanho), fmt: g.fmtGanho(1, 'pt') };
  });
  const quase = (a, b) => a.every((x, i) => Math.abs(x - b[i]) < 1e-9);
  p.conferir('ganho: gain_to_frac(0; 0,5; 1; 5; 10) = 0; 0,25; 0,5; 0,7222; 1', quase(r.f, [0, 0.25, 0.5, 0.5 + 0.5 * 4 / 9, 1]), JSON.stringify(r.f));
  p.conferir('ganho: frac_to_gain(0; 0,25; 0,5; 0,75; 1) = 0; 0,5; 1; 5,5; 10', quase(r.g, [0, 0.5, 1, 5.5, 10]), JSON.stringify(r.g));
  p.conferir('ganho: fmt_gain(1) = "1,0×"', r.fmt === '1,0×', r.fmt);
}

async function partida(page) {
  const ini = await page.evaluate(() => ({ e: window.vitrine.estado().estados.gravar, d: document.querySelector('[data-ref=principal]').disabled }));
  p.conferir('motor subindo: Gravar no lugar e desabilitado', ini.e === 'motor-subindo' && ini.d, JSON.stringify(ini));
  p.conferir('motor subindo: status "Preparando o motor…"', /Preparando o motor/.test(await statusTexto(page)));
  p.conferir('ready: Gravar habilitado', await esperarEstado(page, 'gravar', 'pronto') && !(await page.$eval('[data-ref=principal]', (e) => e.disabled)));
}

async function ciclo(page) {
  await clicar(page, 'principal');
  p.conferir('Gravar → gravando (rec.start mode rec)', await esperarEstado(page, 'gravar', 'gravando') && (await ultimo(page, 'rec.start'))?.args.mode === 'rec');
  p.conferir('gravando: aba Arquivo bloqueada com o motivo (cadeado e title)', await page.$eval('[data-tela="arquivo"]', (a) =>
    a.getAttribute('aria-disabled') === 'true' && a.title.length > 0 && a.querySelector('svg').dataset.lucide === 'lock'));
  p.conferir('clique dentro da janela chama window_pin', (await conta(page, 'window_pin')) > 0);
  await clicar(page, 'secundario');
  p.conferir('Pausar → pausado (rec.pause)', await esperarEstado(page, 'gravar', 'pausado') && (await conta(page, 'rec.pause')) === 1);
  await clicar(page, 'secundario');
  p.conferir('Continuar → gravando (rec.resume)', await esperarEstado(page, 'gravar', 'gravando') && (await conta(page, 'rec.resume')) === 1);
  await clicar(page, 'principal');
  p.conferir('Parar → parado por parar_gravacao (nunca rec.stop direto)', await esperarEstado(page, 'gravar', 'parado')
    && (await conta(page, 'parar_gravacao')) === 1 && (await conta(page, 'rec.stop')) === 0);
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'pronto');
  const area = await page.evaluate(() => window.__recoMock.area);
  p.conferir('Salvar e copiar caminho: rec.conclude save + copy_path, "<mp3>" entre aspas no colar',
    (await ultimo(page, 'rec.conclude'))?.args.action === 'save' && (await conta(page, 'copy_path')) === 1 && /^".+\.mp3"$/.test(area), area);
  p.conferir('status diz "Caminho copiado"', /Caminho copiado/.test(await statusTexto(page)));
}

async function saidas(page) {
  const casos = [['salvar-transcrever', 'transcribe', 'transcricao-pronta'], ['transcrever-apagar', 'transcribe_delete', 'transcricao-pronta'],
    ['so-salvar', 'save', 'pronto'], ['excluir', 'delete', 'pronto']];
  for (const [acao, action, fim] of casos) {
    await gravarEParar(page);
    await clicar(page, acao);
    const ok = await esperarEstado(page, 'gravar', fim, 10000);
    p.conferir(`saída "${acao}" → ${fim} (rec.conclude ${action})`, ok && (await ultimo(page, 'rec.conclude'))?.args.action === action);
    if (fim === 'transcricao-pronta') {
      await clicar(page, 'abrir-transcricao');
      p.conferir(`"${acao}": Abrir transcrição abre o .txt`, /\.txt$/.test((await ultimo(page, 'open_path'))?.args.path || ''));
    }
  }
  await gravarEParar(page);
  await clicar(page, 'secundario');
  p.conferir('parado: Ouvir abre o .mp3', /\.mp3$/.test((await ultimo(page, 'open_path'))?.args.path || ''));
  await clicar(page, 'salvar-transcrever');
  await esperarEstado(page, 'gravar', 'transcrevendo');
  await clicar(page, 'parar-transcricao');
  p.conferir('Parar transcrição: transcribe.cancel e volta a pronto', await esperarEstado(page, 'gravar', 'pronto') && (await conta(page, 'transcribe.cancel')) === 1);
}

async function nota(page) {
  await page.click('[data-acao="modo"][data-modo="nota"]');
  p.conferir('modo Nota: o principal vira "Gravar nota"', (await page.$eval('[data-ref=principal-texto]', (e) => e.textContent)) === 'Gravar nota');
  await clicar(page, 'principal');
  p.conferir('Gravar nota → nota-gravando (rec.start mode nota)', await esperarEstado(page, 'gravar', 'nota-gravando') && (await ultimo(page, 'rec.start'))?.args.mode === 'nota');
  await clicar(page, 'principal');
  const pronta = await esperarEstado(page, 'gravar', 'transcricao-pronta', 10000);
  const area = await page.evaluate(() => window.__recoMock.area);
  p.conferir('nota: parar encadeia a conclusão (reco-conclusao) e o "<md>" vai para o colar', pronta && /^".+\.md"$/.test(area), area);
  await page.click('[data-acao="modo"][data-modo="gravacao"]');
}

async function aoVivo(page) {
  await page.evaluate(() => { window.__recoMock.config.live = true; });
  await clicar(page, 'principal');
  p.conferir('ao vivo: gravando-ao-vivo', await esperarEstado(page, 'gravar', 'gravando-ao-vivo'));
  await page.waitForFunction(() => document.querySelector('[data-ref=aovivo]').childElementCount >= 3, null, { timeout: 8000 }).catch(() => undefined);
  p.conferir('ao vivo: falas chegam ao painel', (await page.$eval('[data-ref=aovivo]', (e) => e.childElementCount)) >= 3);
  await clicar(page, 'principal');
  p.conferir('ao vivo: parar → passada final (transcrevendo) → parado', await esperarEstado(page, 'gravar', 'transcrevendo') && await esperarEstado(page, 'gravar', 'parado', 10000));
  await clicar(page, 'excluir');
  await esperarEstado(page, 'gravar', 'pronto');
  await page.evaluate(() => { window.__recoMock.config.live = false; });
}

async function d11(page) {
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'gravando');
  await page.evaluate(() => window.__recoMock.derrubar());
  const erro = await esperarEstado(page, 'gravar', 'erro');
  const tela = await page.evaluate(() => ({ titulo: document.querySelector('[data-ref=erro-titulo]').textContent, rec: document.querySelector('[data-ref=rec-texto]').textContent,
    botao: document.querySelector('[data-ref=erro-botao-texto]').textContent, arquivo: document.querySelector('[data-tela=arquivo]').getAttribute('aria-disabled') }));
  p.conferir('D11: motor caído gravando → aviso "A gravação foi interrompida" com Abrir pasta, nunca "Gravando"',
    erro && tela.titulo === 'A gravação foi interrompida' && tela.rec !== 'Gravando' && tela.botao === 'Abrir pasta' && tela.arquivo === 'false', JSON.stringify(tela));
  await page.waitForTimeout(400);
  p.conferir('D11: o reinício do motor não religa a gravação', (await page.evaluate(() => window.__recoMock.estado())) === 'idle'
    && (await page.evaluate(() => window.vitrine.estado().estados.gravar)) === 'erro');
  await clicar(page, 'erro-saida');
  p.conferir('D11: Abrir pasta revela a pasta das gravações', (await ultimo(page, 'reveal_path'))?.args.path.length > 0);
}

async function ganhoGesto(page) {
  const antes = await chamadas(page).then((c) => c.length);
  const r = await page.$eval('[data-ref=ganho-mic]', (e) => { const b = e.getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; });
  const t0 = Date.now();
  await page.mouse.move(r[0] + r[2] / 2, r[1] + r[3] / 2);
  await page.mouse.down();
  for (let k = 1; k <= 20; k++) { await page.mouse.move(r[0] + r[2] / 2 + k * (r[2] / 45), r[1] + r[3] / 2); await page.waitForTimeout(20); }
  const meio = (await chamadas(page)).slice(antes);
  await page.mouse.up();
  const dur = Date.now() - t0;
  await page.waitForTimeout(250);
  const depois = (await chamadas(page)).slice(antes);
  const sets = depois.filter((c) => c.cmd === 'rec.set_gain').length, cfg = depois.filter((c) => c.cmd === 'config.set' && 'mic_gain' in c.args.changes);
  p.conferir(`ganho (arrasto): rec.set_gain no máximo a cada 150 ms (${sets} em ${dur} ms)`, sets >= 1 && sets <= Math.ceil(dur / 150) + 1);
  p.conferir('ganho (arrasto): nenhum config.set no arrasto, um só ao soltar', meio.every((c) => c.cmd !== 'config.set') && cfg.length === 1, JSON.stringify(cfg));
  const rotulo = await page.$eval('[data-ref=ganho-mic-valor]', (e) => e.textContent);
  p.conferir('ganho (arrasto): rótulo com vírgula e o mesmo valor gravado', rotulo === String(cfg[0]?.args.changes.mic_gain.toFixed(1)).replace('.', ',') + '×', rotulo);
  await page.focus('[data-ref=ganho-sis]');
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(250);
  p.conferir('ganho (teclado): Home e 2× seta → 1,0× no rótulo e config.set sys_gain 1', (await page.$eval('[data-ref=ganho-sis-valor]', (e) => e.textContent)) === '1,0×'
    && (await ultimo(page, 'config.set'))?.args.changes.sys_gain === 1);
}

async function pontual(page) {
  await page.evaluate(() => { window.__recoMock.velocidade = 1; });
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'gravando');
  const r = await page.evaluate(() => new Promise((ok) => {
    const raiz = document.querySelector('[data-area=janela]'), filhos = [...raiz.children];
    const crono = document.querySelector('[data-ref=crono]'), med = document.querySelector('[data-area=medidores]');
    let vuNos = 0, cronoTexto = 0, outrosNos = 0, vuVars = 0;
    const obs = new MutationObserver((ms) => ms.forEach((m) => {
      if (med.contains(m.target) && m.type === 'childList') vuNos += 1;
      else if (med.contains(m.target) && m.type === 'attributes') vuVars += 1;
      else if (crono.contains(m.target)) cronoTexto += 1;
      else if (m.type === 'childList') outrosNos += 1;
    }));
    obs.observe(raiz, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['style'] });
    setTimeout(() => { obs.disconnect(); ok({ vuNos, vuVars, cronoTexto, outrosNos, mesmos: filhos.length === raiz.children.length && filhos.every((f, i) => raiz.children[i] === f) }); }, 3000);
  }));
  p.conferir('pontual: VU sem nó criado em 3 s gravando (e as barras mudam)', r.vuNos === 0 && r.vuVars > 0, JSON.stringify(r));
  p.conferir('pontual: cronômetro com até 4 mudanças de texto em 3 s', r.cronoTexto >= 1 && r.cronoTexto <= 4, JSON.stringify(r));
  p.conferir('pontual: nenhum outro nó criado e a raiz com os mesmos filhos', r.outrosNos === 0 && r.mesmos, JSON.stringify(r));
  await page.evaluate(() => { window.__recoMock.velocidade = 10; });
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'parado');
  await clicar(page, 'excluir');
  await esperarEstado(page, 'gravar', 'pronto');
}

async function atalho(page) {
  await page.evaluate(() => window.__recoMock.casco('reco-atalho'));
  await page.waitForTimeout(100);
  p.conferir('reco-atalho (Ctrl+Shift+R): foco no botão principal', await page.evaluate(() => document.activeElement === document.querySelector('[data-ref=principal]')));
}

// rótulos inteiros nos botões do painel (pendência da Fase 1) e a 1ª linha do ao vivo, pelo condutor, em cada skin
async function porSkin(page) {
  for (const direcao of ['a', 'b', 'c']) for (const texto of ['normal', 'longo-en']) {
    const cortes = await page.evaluate(([d, tx]) => {
      const out = [];
      for (const estado of ['parado', 'transcricao-pronta', 'transcrevendo', 'erro']) {
        window.vitrine.definir({ direcao: d, tela: 'gravar', estado, texto: tx, tema: 'claro' });
        // tolerância de 1 px: scrollHeight e clientHeight são inteiros (linha de 14,375 px dá 15 × 14 sem corte nenhum);
        // um corte de verdade esconde uma linha inteira (≈ 14 px) ou letras (reticências)
        document.querySelectorAll('.painel .camada[data-ativa] .botao .corta').forEach((s) => {
          if (s.scrollWidth > s.clientWidth + 1 || s.scrollHeight > s.clientHeight + 1) out.push(`${estado}: "${s.textContent}"`);
        });
      }
      return out;
    }, [direcao, texto]);
    p.conferir(`skin ${direcao} (${texto}): nenhum rótulo cortado nos botões do painel`, !cortes.length, cortes.join(' | '));
    const linha = await page.evaluate(([d, tx]) => {
      window.vitrine.definir({ direcao: d, tela: 'gravar', estado: 'gravando-ao-vivo', texto: tx, tema: 'claro' });
      const box = document.querySelector('[data-ref=aovivo]'), cs = getComputedStyle(box), resp = parseFloat(cs.paddingTop), L = parseFloat(cs.lineHeight);
      const topos = [...box.children].flatMap((q) => [...Array(Math.round(q.offsetHeight / L)).keys()].map((k) => q.offsetTop - resp + k * L));
      return { rola: box.scrollHeight > box.clientHeight, alinhado: topos.some((y) => Math.abs(y - box.scrollTop) < 0.5), st: box.scrollTop };
    }, [direcao, texto]);
    p.conferir(`skin ${direcao} (${texto}): ao vivo rola e a 1ª linha à vista sai inteira`, linha.rola && linha.alinhado, JSON.stringify(linha));
  }
}

(async () => {
  const srv = await servir();
  const base = `http://127.0.0.1:${srv.address().port}/`;
  const browser = await playwright().chromium.launch();
  try {
    const { ctx, page, erros } = await abrir(browser, base);
    await ganhoPuro(page);
    await partida(page);
    await ciclo(page);
    await saidas(page);
    await nota(page);
    await aoVivo(page);
    await ganhoGesto(page);
    await pontual(page);
    await atalho(page);
    await d11(page);
    p.conferir('nenhum erro de página', !erros.length, erros.join(' | '));
    await ctx.close();
    const c = await abrir(browser, base);
    await porSkin(c.page);
    p.conferir('nenhum erro de página (condutor)', !c.erros.length, c.erros.join(' | '));
    await c.ctx.close();
  } finally {
    await browser.close();
    srv.close();
  }
  console.log(`gravar: falhas ${p.falhas()} em ${p.total()} verificações`);
  process.exit(p.falhas() ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });

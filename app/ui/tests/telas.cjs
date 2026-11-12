// telas.cjs: prova das abas Biblioteca, Arquivo e Opções e da navegação bloqueada (Fase 3, passo 13), contra a
// interface real com o backend falso. Uso: npm --prefix app run ui:build && node app/ui/tests/telas.cjs
// → última linha "telas: falhas 0" (saída 0). Cada ação confere o comando que chegou ao backend falso.
'use strict';
const { playwright, servir, placar, abrir, esperarEstado, chamadas, clicar, statusTexto } = require('./comum.cjs');

const p = placar();
const ultimo = async (page, cmd) => (await chamadas(page)).filter((c) => c.cmd === cmd).pop();
const conta = async (page, cmd) => (await chamadas(page)).filter((c) => c.cmd === cmd).length;
// force: o Playwright trata aria-disabled como desabilitado e esperaria a aba destravar; aqui o clique na aba
// bloqueada é justamente o que se quer provar
const aba = (page, tela) => page.click(`.abas [data-tela="${tela}"]`, { force: true });
const item = (page, i) => page.click(`.tela[data-ativa] .lista-corpo .item[data-i="${i}"]`);

async function biblioteca(page) {
  const antes = await conta(page, 'library.list');
  await aba(page, 'biblioteca');
  p.conferir('Biblioteca: abrir a aba pede library.list e mostra a lista', await esperarEstado(page, 'biblioteca', 'lista') && (await conta(page, 'library.list')) > antes);
  p.conferir('Biblioteca: 12 itens e status com a contagem', (await page.$$eval('.lista-corpo .item', (x) => x.length)) === 12 && /12 gravações/.test(await statusTexto(page)));
  await item(page, 0);
  p.conferir('Biblioteca: clicar seleciona', await esperarEstado(page, 'biblioteca', 'selecionada'));
  const alvo = await page.evaluate(() => window.__recoTeste.app.v.b.itens[0]);
  await clicar(page, 'lib-ouvir');
  p.conferir('Biblioteca: Ouvir → open_path do áudio', (await ultimo(page, 'open_path'))?.args.path === alvo.path);
  await page.dblclick('.lista-corpo .item[data-i="2"]');
  const it2 = await page.evaluate(() => window.__recoTeste.app.v.b.itens[2].path);
  p.conferir('Biblioteca: duplo clique toca a gravação (open_path)', (await ultimo(page, 'open_path'))?.args.path === it2);
  await item(page, 0);
  await clicar(page, 'lib-abrir');
  p.conferir('Biblioteca: Abrir texto → open_path do .txt', (await ultimo(page, 'open_path'))?.args.path === alvo.txt);
  await clicar(page, 'lib-resumo');
  const resumindo = await esperarEstado(page, 'biblioteca', 'resumindo');
  p.conferir('Biblioteca: Resumo IA → resumo.ia, resumindo e abre o .resumo.md', resumindo && await esperarEstado(page, 'biblioteca', 'selecionada')
    && (await ultimo(page, 'resumo.ia'))?.args.path === alvo.path && /\.resumo\.md$/.test((await ultimo(page, 'open_path'))?.args.path));
  await item(page, 1);
  await page.evaluate(() => { window.__recoMock.passosTranscricao = 40; }); // ~1,2 s: dá tempo de conferir o bloqueio
  await clicar(page, 'lib-transcrever');
  p.conferir('Biblioteca: Transcrever → transcribe.file e transcrevendo-item', await esperarEstado(page, 'biblioteca', 'transcrevendo-item') && !!(await ultimo(page, 'transcribe.file')));
  p.conferir('transcrevendo na Biblioteca: aba Arquivo bloqueada com o motivo', await page.$eval('[data-tela="arquivo"]', (a) =>
    a.getAttribute('aria-disabled') === 'true' && a.title.length > 0 && a.querySelector('svg').dataset.lucide === 'lock'));
  await aba(page, 'arquivo');
  p.conferir('aba bloqueada: o clique não troca de tela e o status diz o motivo', (await page.evaluate(() => window.vitrine.estado().tela)) === 'biblioteca'
    && /bloqueado/.test(await statusTexto(page)));
  await clicar(page, 'lib-transcrever');
  p.conferir('Biblioteca: Parar → transcribe.cancel', await esperarEstado(page, 'biblioteca', 'selecionada') && (await conta(page, 'transcribe.cancel')) === 1);
  await clicar(page, 'lib-transcrever');
  p.conferir('Biblioteca: transcrição até o fim volta a selecionada com o item transcrito', await esperarEstado(page, 'biblioteca', 'transcrevendo-item')
    && await page.waitForFunction(() => window.__recoTeste.app.v.b.itens.find((i) => i.nome === '2026-11-11_0915_reco.mp3')?.temTexto, null, { timeout: 8000 }).then(() => true, () => false));
  await item(page, 3);
  await clicar(page, 'lib-excluir');
  await page.waitForFunction(() => window.__recoTeste.app.v.b.itens.length === 11, null, { timeout: 5000 }).catch(() => undefined);
  p.conferir('Biblioteca: Excluir → library.delete e a lista relida', !!(await ultimo(page, 'library.delete')) && (await page.$$eval('.lista-corpo .item', (x) => x.length)) === 11);
  await clicar(page, 'lib-pasta');
  p.conferir('Biblioteca: Abrir pasta → reveal_path da pasta', !!(await ultimo(page, 'reveal_path')));
  const n = await conta(page, 'library.list');
  await clicar(page, 'lib-atualizar');
  await page.waitForTimeout(200);
  p.conferir('Biblioteca: Atualizar → library.list', (await conta(page, 'library.list')) === n + 1);
  await page.fill('[data-ref=busca]', '1432');
  await page.waitForTimeout(500);
  p.conferir('Biblioteca: busca → library.search {q} e 1 resultado', (await ultimo(page, 'library.search'))?.args.q === '1432' && (await page.$$eval('.lista-corpo .item', (x) => x.length)) === 1);
  await page.fill('[data-ref=busca]', 'nada-disso');
  p.conferir('Biblioteca: busca sem resultado', await esperarEstado(page, 'biblioteca', 'busca-sem-resultado', 3000));
  await clicar(page, 'limpar-busca');
  p.conferir('Biblioteca: Limpar busca volta à lista', await esperarEstado(page, 'biblioteca', 'lista', 3000));
}

async function arquivo(page) {
  await aba(page, 'arquivo');
  await clicar(page, 'arq-escolher');
  p.conferir('Arquivo: Escolher → pick_file midia e escolhido', await esperarEstado(page, 'arquivo', 'escolhido') && (await ultimo(page, 'pick_file'))?.args.kind === 'midia');
  await clicar(page, 'arq-transcrever');
  const andando = await esperarEstado(page, 'arquivo', 'transcrevendo');
  p.conferir('Arquivo: Transcrever → transcribe.file, progresso e Parar habilitado', andando && !!(await ultimo(page, 'transcribe.file'))
    && !(await page.$eval('[data-ref=arq-parar]', (b) => b.disabled)));
  p.conferir('Arquivo: transcrição pronta', await esperarEstado(page, 'arquivo', 'pronto', 10000));
  await clicar(page, 'arq-abrir');
  p.conferir('Arquivo: Abrir transcrição → open_path .txt', /\.txt$/.test((await ultimo(page, 'open_path'))?.args.path));
  await clicar(page, 'arq-copiar');
  p.conferir('Arquivo: Copiar caminho → copy_path entre aspas', /^".+\.txt"$/.test(await page.evaluate(() => window.__recoMock.area)));
  await clicar(page, 'arq-converter');
  const conv = await esperarEstado(page, 'arquivo', 'convertendo');
  p.conferir('Arquivo: Converter → convert.extract_mp3, sem Parar (a Fase 2 não cancela conversão)', conv && !!(await ultimo(page, 'convert.extract_mp3'))
    && await page.$eval('[data-ref=arq-parar]', (b) => b.disabled));
  p.conferir('Arquivo: conversão pronta e Ouvir o MP3', await esperarEstado(page, 'arquivo', 'pronto', 10000)
    && (await page.$eval('[data-ref=arq-abrir-texto]', (e) => e.textContent)) === 'Ouvir o MP3');
  await clicar(page, 'arq-transcrever');
  await esperarEstado(page, 'arquivo', 'transcrevendo');
  await clicar(page, 'arq-parar');
  p.conferir('Arquivo: Parar → transcribe.cancel e volta a escolhido', await esperarEstado(page, 'arquivo', 'escolhido') && (await conta(page, 'transcribe.cancel')) >= 2);
  await clicar(page, 'arq-pasta');
  p.conferir('Arquivo: Abrir pasta → reveal_path', /reuniao-fornecedor/.test((await ultimo(page, 'reveal_path'))?.args.path));
  await page.evaluate(() => { window.__recoMock.proximoArquivo = 'C:\\Vídeos\\sem-audio.mp4'; });
  await clicar(page, 'arq-escolher');
  await clicar(page, 'arq-transcrever');
  p.conferir('Arquivo: vídeo sem trilha de som → erro "Esse arquivo não tem áudio"', await esperarEstado(page, 'arquivo', 'erro')
    && (await page.$eval('[data-ref=arq-erro-titulo]', (e) => e.textContent)) === 'Esse arquivo não tem áudio');
}

async function opcoes(page) {
  await aba(page, 'opcoes');
  const cfg = async (chave) => (await chamadas(page)).filter((c) => c.cmd === 'config.set' && chave in c.args.changes).pop()?.args.changes[chave];
  const topo = await page.evaluate(() => [...document.querySelectorAll('[data-area=opcoes-lista] .opcao-nome span')].slice(0, 2).map((e) => e.textContent));
  p.conferir('Opções: Visual e Aparência no topo', topo[0] === 'Visual' && topo[1] === 'Aparência', topo.join(', '));
  await page.click('[data-acao=skin][data-skin=c]');
  p.conferir('Opções: skin Instrumento → casco_skin c e data-direcao no <html>', (await cfg('casco_skin')) === 'c' && await page.evaluate(() => document.documentElement.dataset.direcao === 'c'));
  await page.click('[data-acao=skin][data-skin=a]');
  await page.click('[data-acao=aparencia][data-tema=escuro]');
  p.conferir('Opções: Aparência Escuro → casco_tema e data-tema', (await cfg('casco_tema')) === 'escuro' && await page.evaluate(() => document.documentElement.dataset.tema === 'escuro'));
  await page.click('[data-acao=aparencia][data-tema=sistema]');
  await page.selectOption('[data-ref=sel-mic]', '{mic-2}');
  await page.waitForTimeout(200);
  p.conferir('Opções: Entrada manual → config.set mic_device', (await cfg('mic_device')) === '{mic-2}');
  await clicar(page, 'atualizar-disp');
  await page.waitForTimeout(100);
  p.conferir('Opções: Atualizar dispositivos → devices.refresh', (await conta(page, 'devices.refresh')) === 1);
  await clicar(page, 'op-pasta');
  await page.waitForTimeout(200);
  p.conferir('Opções: Pasta das gravações → pick_folder e config.set output_dir', (await cfg('output_dir')) === 'C:\\Notas');
  await clicar(page, 'op-nota');
  await page.waitForTimeout(200);
  p.conferir('Opções: Pasta das notas → config.set nota_dir', (await cfg('nota_dir')) === 'C:\\Notas');
  await page.click('[data-acao=processar][data-valor=GPU]');
  await page.waitForTimeout(100);
  p.conferir('Opções: Processar em GPU → config.set device', (await cfg('device')) === 'GPU' && await page.$eval('[data-valor=GPU]', (b) => b.getAttribute('aria-pressed') === 'true'));
  await clicar(page, 'ao-vivo');
  await page.waitForTimeout(100);
  p.conferir('Opções: Texto ao vivo → config.set live', (await cfg('live')) === true && await page.$eval('[data-ref=ao-vivo]', (b) => b.getAttribute('aria-checked') === 'true'));
  await clicar(page, 'ao-vivo');
  await page.click('[data-acao=idioma][data-idioma=en]');
  await page.waitForTimeout(150);
  p.conferir('Opções: English → config.set language, definir_lingua e textos em inglês', (await cfg('language')) === 'en' && (await ultimo(page, 'definir_lingua'))?.args.lingua === 'en'
    && (await page.$eval('.abas [data-tela=gravar] .aba-rotulo', (e) => e.textContent)) === 'Record');
  await page.click('[data-acao=idioma][data-idioma=pt]');
  await page.waitForTimeout(150);
  await clicar(page, 'atalho');
  await page.waitForTimeout(100);
  p.conferir('Opções: Atalho → definir_atalho ligar', (await ultimo(page, 'definir_atalho'))?.args.ligar === true && await page.$eval('[data-ref=atalho]', (b) => b.getAttribute('aria-checked') === 'true'));
  await clicar(page, 'atalho');
  await page.evaluate(() => { window.__recoMock.atalhoOcupado = true; });
  await clicar(page, 'atalho');
  await page.waitForTimeout(100);
  p.conferir('Opções: atalho ocupado → hotkey_taken à vista', /já está em uso/.test(await page.$eval('[data-ref=ajuda-atalho-texto]', (e) => e.textContent)));
  await clicar(page, 'autostart');
  await page.waitForTimeout(100);
  p.conferir('Opções: Iniciar com o Windows → definir_autostart', (await ultimo(page, 'definir_autostart'))?.args.ligar === true);
  await clicar(page, 'autostart');
  await page.evaluate(() => window.__recoMock.casco('reco-versao-nova', { tag: 'v9.9', url: 'https://github.com/dosxnjos/reco/releases/tag/v9.9' }));
  await page.waitForTimeout(100);
  const versao = await page.evaluate(() => ({ titulo: !document.querySelector('[data-ref=versao]').hasAttribute('data-escondido'), op: !document.querySelector('[data-ref=op-versao-btn]').hasAttribute('data-escondido') }));
  p.conferir('Opções: versão nova à vista na barra de título e em Opções', versao.titulo && versao.op);
  await clicar(page, 'versao');
  p.conferir('Opções: Baixar a versão → open_external com a URL', /v9\.9$/.test((await ultimo(page, 'open_external'))?.args.url));
  await page.click('.titulo [data-acao=minimizar]');
  await page.click('.titulo [data-acao=fechar]');
  p.conferir('barra de título: minimizar e fechar → window_minimize e window_hide', (await conta(page, 'window_minimize')) === 1 && (await conta(page, 'window_hide')) === 1);
}

async function bloqueio(page) {
  await aba(page, 'gravar');
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'gravando');
  p.conferir('gravando: aba Arquivo bloqueada com o motivo', await page.$eval('[data-tela="arquivo"]', (a) => a.getAttribute('aria-disabled') === 'true' && a.title.length > 0));
  await aba(page, 'arquivo');
  p.conferir('gravando: clicar em Arquivo não troca de tela', (await page.evaluate(() => window.vitrine.estado().tela)) === 'gravar');
  await aba(page, 'opcoes');
  const op = await page.evaluate(() => ({ e: window.vitrine.estado().estados.opcoes, sel: document.querySelector('[data-ref=sel-mic]').disabled,
    ajuda: document.querySelector('[data-ref=ajuda-dispositivo-texto]').textContent }));
  p.conferir('gravando: Opções navegável, dispositivos travados com "Bloqueado enquanto grava."', op.e === 'durante-gravacao' && op.sel && /Bloqueado enquanto grava/.test(op.ajuda), JSON.stringify(op));
  await aba(page, 'biblioteca');
  p.conferir('gravando: Biblioteca navegável', (await page.evaluate(() => window.vitrine.estado().tela)) === 'biblioteca');
  await aba(page, 'gravar');
  await clicar(page, 'principal');
  await esperarEstado(page, 'gravar', 'parado');
  await clicar(page, 'excluir');
  p.conferir('parou: Arquivo volta a abrir', await esperarEstado(page, 'gravar', 'pronto') && await page.$eval('[data-tela="arquivo"]', (a) => a.getAttribute('aria-disabled') === 'false'));
}

(async () => {
  const srv = await servir();
  const base = `http://127.0.0.1:${srv.address().port}/`;
  const browser = await playwright().chromium.launch();
  try {
    const { ctx, page, erros } = await abrir(browser, base);
    await esperarEstado(page, 'gravar', 'pronto');
    await biblioteca(page);
    await arquivo(page);
    await opcoes(page);
    await bloqueio(page);
    p.conferir('nenhum erro de página', !erros.length, erros.join(' | '));
    await ctx.close();
  } finally {
    await browser.close();
    srv.close();
  }
  console.log(`telas: falhas ${p.falhas()} em ${p.total()} verificações`);
  process.exit(p.falhas() ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });

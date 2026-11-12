// i18n-check.cjs: confere que todo texto da interface tem PT e EN (Fase 3, passo 11; o tools/check_i18n.py faz isso
// no app velho). Uso: npm --prefix app run i18n:check  →  última linha "i18n: <n> chaves, 0 faltando" (saída 0).
// Confere: (1) pt.ts e en.ts com as mesmas chaves; (2) todo código de erro do docs/PROTOCOL.md, os do casco
// (timeout, hotkey_taken) e os que o backend falso lança têm erro.<código>; (3) todo estado do motor tem
// estado.<nome>; (4) toda chave citada no código (t("…")) e no HTML (data-t*) existe; (5) nenhum hexadecimal de cor
// solto em app/ui/src (cor só nos tokens do design/tokens.css).
'use strict';
const fs = require('fs');
const path = require('path');

const APP = path.resolve(__dirname, '..');
const RAIZ = path.resolve(APP, '..');
const SRC = path.join(APP, 'ui', 'src');
const ler = (p) => fs.readFileSync(p, 'utf8');
const faltas = [];

const chaves = (arq) => new Set([...ler(path.join(SRC, 'i18n', arq)).matchAll(/^\s*"([^"]+)":\s/gm)].map((m) => m[1]));
const pt = chaves('pt.ts'), en = chaves('en.ts');
for (const k of pt) if (!en.has(k)) faltas.push(`EN sem a chave ${k}`);
for (const k of en) if (!pt.has(k)) faltas.push(`PT sem a chave ${k}`);
const tem = (k, onde) => { if (!pt.has(k) || !en.has(k)) faltas.push(`${onde}: falta ${k} em ${pt.has(k) ? 'EN' : 'PT'}`); };

// (2) códigos de erro do protocolo, do casco e do backend falso
const protocolo = ler(path.join(RAIZ, 'docs', 'PROTOCOL.md'));
const secao = protocolo.split('## Códigos de erro')[1];
if (!secao) faltas.push('docs/PROTOCOL.md sem a seção "## Códigos de erro"');
const codigos = new Set([...(secao || '').split('\n## ')[0].split('\n\n')[1].matchAll(/`([a-z_]+)`/g)].map((m) => m[1]));
if (codigos.size < 10) faltas.push(`PROTOCOL.md: só ${codigos.size} códigos lidos (esperado 12)`);
['timeout', 'hotkey_taken'].forEach((c) => codigos.add(c));
const arquivosTs = [];
const varrer = (dir) => fs.readdirSync(dir, { withFileTypes: true }).forEach((e) => {
  const p = path.join(dir, e.name);
  if (e.isDirectory()) varrer(p); else if (/\.(ts|css)$/.test(e.name)) arquivosTs.push(p);
});
varrer(SRC);
const mock = ler(path.join(SRC, 'mock.ts'));
[...mock.matchAll(/falha\("([a-z_]+)"/g)].forEach((m) => codigos.add(m[1]));
for (const c of codigos) tem('erro.' + c, 'código de erro');

// (3) estados do motor: o evento state e o `starting` do comando state
const linhaState = protocolo.match(/`state` — `\{state: ([a-z|]+),/);
const estados = new Set(linhaState ? linhaState[1].split('|') : []);
if (!estados.size) faltas.push('PROTOCOL.md: linha do evento state não encontrada');
estados.add('starting');
for (const s of estados) tem('estado.' + s, 'estado do motor');

// (4) chaves citadas no código e no HTML; as montadas por modelo (`g.tarefa-${…}`, `canal.${…}`) por lista
let citadas = 0;
for (const arq of arquivosTs.filter((p) => p.endsWith('.ts'))) {
  const txt = ler(arq).replace(/^\s*\/\/.*$/gm, ''), onde = path.relative(APP, arq).replace(/\\/g, '/');
  for (const m of txt.matchAll(/\bt\(\s*"([^"]+)"/g)) { citadas += 1; tem(m[1], onde); }
  for (const m of txt.matchAll(/\[[^\]\n]*?, "([a-z]+\.[a-z0-9.-]+)"\]/g)) if (/^(rec|g|b|a|o|st|av)\./.test(m[1])) { citadas += 1; tem(m[1], onde); }
}
['transcrever', 'passada', 'nota'].forEach((x) => tem('g.tarefa-' + x, 'modelo g.tarefa-'));
['mic', 'sys', 'save'].forEach((x) => tem('canal.' + x, 'modelo canal.'));
const html = ler(path.join(APP, 'ui', 'index.html'));
for (const m of html.matchAll(/data-t(?:-aria|-title|-ph)?="([^"]+)"/g)) { citadas += 1; tem(m[1], 'ui/index.html'); }

// (5) cor só nos tokens
for (const arq of arquivosTs) {
  const txt = ler(arq).replace(/href="#i-|"#i-"/g, '');
  for (const m of txt.matchAll(/#[0-9a-fA-F]{3,8}\b/g)) faltas.push(`${path.relative(APP, arq)}: hexadecimal ${m[0]} fora de design/tokens.css`);
}

faltas.forEach((f) => console.log('FALTA ' + f));
console.log(`i18n: ${pt.size} chaves PT, ${en.size} EN, ${codigos.size} códigos de erro, ${estados.size} estados, ${citadas} citações; ${faltas.length} faltando`);
process.exit(faltas.length ? 1 : 0);

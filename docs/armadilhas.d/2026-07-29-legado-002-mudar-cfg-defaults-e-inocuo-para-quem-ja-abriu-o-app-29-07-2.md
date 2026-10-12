---
titulo: Mudar `_CFG_DEFAULTS` é inócuo para quem já abriu o app (29/07/2026)
data: 2026-07-29
---
**Sintoma:** troca-se o default (por exemplo `"model"` de `small` para
`large-v3-turbo`), testa-se numa máquina limpa, funciona — e no computador do
usuário nada muda.

**Causa:** `load_config()` parte dos defaults e depois **deixa o arquivo salvo
sobrescrever** (`cfg.update(json…)`). Isso é o comportamento correto (a escolha
do usuário tem de ganhar), mas significa que qualquer default alterado só alcança
quem **nunca** salvou config. O `~/.reco_config.json` do Gabriel tinha
`"model": "small"` gravado, então a troca de modelo não teria chegado nele.

**O que fazer:** toda mudança de default que **precisa** alcançar usuários
existentes exige uma migração: subir `CFG_MIGRACAO` e tratar o caso em
`_migra_config()`. A migração roda uma vez (marcada em `_migracao` no próprio
JSON) e só promove valores que eram o **default antigo** — uma escolha deliberada
do usuário (ex.: `medium`) é preservada.

---

---
titulo: Migração de config persistida antes do exe novo re-arma o autosave do exe antigo (11/10/2026)
data: 2026-10-11
---
**Sintoma.** (Evitado antes de acontecer.) `~/.reco_config.json` com `_migracao: 2`
e `mic_device`/`sys_device` = `"auto:console"`, e o `Reco.exe` **antigo** aberto de
novo: o dispositivo padrão do dia volta a ser gravado como escolha, e o Reco novo
trata o id como manual para sempre (o bug do PDI de 29/09, sem migração que o conserte).

**Causa.** `load_config()` rodava a migração e **gravava** no disco a cada
`import reco` (o idioma é lido no import-time), então qualquer teste, ferramenta ou
sessão migrava o JSON real do Gabriel antes do exe novo existir. O exe antigo vê
`_migracao: 2 >= 1`, não migra, e o `trace_add` dele regrava o id pré-selecionado.

**O que fazer.** `load_config(persist=False)` é o padrão; só `App.__init__` passa
`persist=True`. O guard `tools/test_dispositivo_auto.py` falha se `import reco`
mudar o JSON. Quem mexer em config novo (migração 3 do QCY, passo 4.3): mesma regra,
e **só persista a migração a partir do exe que a entende**. Se o exe antigo abriu
depois do build, trocar `_migracao` para `1` no JSON antes de abrir o novo.

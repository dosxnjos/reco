# Texto repetido entre janelas (#31): guarda de eco no texto pronto

Data: 16/11/2026 · sessão c38e9592 · issue dosxnjos/reco#31 · cópia de trabalho
`C:\Dev\reco\.claude\worktrees\antiloop-31`, ramo `wt/antiloop-31`, criado de `origin/master` em `fb98efd`.

## Entendimento

Transcrições reais traziam a mesma frase curta de enchimento dezenas de vezes seguidas, e a defesa anti-loop
(`OVTranscriber._degenerado` / `_generate_sem_loop`) não reclamava. Diagnóstico medido em cópias de gravações (nada do
app instalado nem do config real foi tocado; o texto das gravações é privado e não entra aqui):

- **Causa (a), raiz:** a defesa olha uma janela do VAD (3 a 4 s) por vez. Janela de ruído, ou de voz do interlocutor
  vazando no mic, devolve uma frase curta e limpa; dezenas de janelas seguidas repetem a mesma. A junção (`_merge`)
  soma as repetições numa fala só.
- **Causa (c):** o `_degenerado` só roda acima de 40 caracteres; loop curto dentro de uma janela passa.
- **Amplificador (d):** o contexto (`initial_prompt`, últimas ~30 palavras) carrega a frase para a janela seguinte.
- **Hipótese (b), derrubada:** o fallback cego de 30 s não disparou em nenhuma das gravações.

## Decisões

- **D1. Filtrar o texto pronto, fala a fala, nunca o que o Whisper vê.** `antiloop.sem_eco` (módulo novo, o `reco.py`
  não pode crescer) tira só as cópias de um n-grama de 1 a 8 palavras além da 3ª seguida; a palavra que não é cópia
  fica. Quando o outro canal fala, a conta recomeça. Descartadas por medição: limpar o eco do contexto, desligar o
  contexto, tirar o piso de 40, refazer a janela sem prompt (todas mudam o texto das janelas seguintes e perderam fala
  real), contar no canal inteiro (apaga a mesma resposta em turnos diferentes) e tirar o trecho inteiro (há trecho que
  começa com o enchimento e segue com fala). Reversão: tirar as 3 chamadas no `reco.py`.
- **D2. Guarda mais rigorosa que a régua.** A guarda testa toda posição de início; a régua `tools/test_antiloop.pior`
  (em uso na Fase 4) fica como está.
- **D3. Número em dígitos é isento** (código e telefone ditados). Número por extenso e palavra repetida de verdade
  ficam como custo declarado (ARQUITETURA e armadilha de 16/11/2026).
- **D4. Nada instalado** (Fase 4 em uso real): o conserto chega no próximo instalador, junto com o polonês.
- **D5. Publicação por agente limpo** (a sessão leu conteúdo de terceiro), com este md como contrato.

## Passos

1. [x] Diagnóstico instrumentado nas cópias: o caminho do app reproduz o `.txt` do app byte a byte; causa (a) e (c)
   provadas, (b) derrubada.
2. [x] Conserto: `antiloop.py` (`sem_eco`, `texto_corrido`), chamado no `_merge` e nos caminhos sem diarização (OV e
   MLX); `antiloop` nos `hiddenimports` dos dois specs; `tools/test_antiloop.py` aplica o filtro como o app.
3. [x] Duas revisões independentes (refutar e prova): nenhum achado médio ou alto; os 5 baixos tratados no passo 4.
4. [x] Ajustes das revisões: guarda em toda posição (D2), dígitos isentos (D3), `texto_corrido` testado com remoção de
   verdade, custos declarados nas docs, frases e números de gravação fora dos docs versionados.
5. [x] Provas (todas na cópia `C:\Dev\reco\.claude\worktrees\antiloop-31`):
   - `python tools/test_eco_janelas.py` → `eco entre janelas: falhas 0` (13 checagens); contra o `reco.py` de antes
     falha 4; os 2 casos novos falham com a guarda antiga;
   - régua `tools/paridade.py --exigir-txt` nas 5 cópias: antes REPROVOU (pior 89, 4, 6), depois PASSOU (pior 3 em
     todas); duas gravações sem defeito saíram idênticas byte a byte;
   - a guarda final sobre os trechos crus das 5 gravações dá saída idêntica byte a byte à rodada revisada; o depois é
     subsequência do antes e cada palavra tirada é cópia além da 3ª seguida;
   - fuzz de 20 mil casos contra régua por força bruta: 0 com repetição > 3, 0 que não seja subsequência;
   - `test_paridade` falhas 0, `check_i18n` OK, `test_engine_protocol` OK, ruff limpo, `reco.py` com 5197 linhas;
   - motor congelado na cópia: passo 6.
6. [x] Motor congelado (`python engine/build.py`, 515 MB, apagado depois): `ready ok=True` nas 3 rodadas do smoke,
   shutdown com exit 0; o `antiloop` aparece nos `.toc` do PyInstaller.
7. [ ] GitHub (agente limpo, contrato abaixo).

O que não foi provado: ninguém ouviu o áudio (o provado é "só saíram cópias além da 3ª seguida"); o caminho MLX
(macOS) não rodou; o rascunho ao vivo (`LiveTranscriber`) não passa pelo filtro; o build do app velho (`reco.spec`)
não foi feito. Na gravação mais longa sobram trincas de enchimento espalhadas (o critério é "mais de 3").

### Passo 7: contrato do agente limpo

Conta: a pessoal, só no comando (`GH_TOKEN=$(gh auth token -u dosxnjos) gh ...`; nunca `gh auth switch`). Repo
`dosxnjos/reco`, ramo local `wt/antiloop-31` da cópia `C:\Dev\reco\.claude\worktrees\antiloop-31`.

0. Só leitura antes: `git -C <cópia> fetch origin`; se `origin/master` andou além de `fb98efd`, PARAR e relatar.
   Conferir que o ramo tem exatamente 1 commit à frente de `origin/master` e que `git status` está limpo.
1. `git push origin wt/antiloop-31:antiloop-31`.
2. PR `antiloop-31` → `master`, título «Transcrição: tira o eco entre janelas (texto repetido, #31)». Corpo em
   português, curto: causa (§ Entendimento, sem número de gravação), o que o conserto faz e não faz (D1 a D3), as
   provas do passo 5 e 6, a lista «O que não foi provado» inteira, que o `tools/test_antiloop.py` só passa porque passou
   a aplicar o filtro como o app, e que nada foi instalado. Linha `Closes #31`. Termina com a linha de atribuição do
   Claude Code. Nenhuma frase transcrita de gravação real (o teste usa texto inventado).
3. Esperar o CI (`gh pr checks`). Verde ou sem checks → `gh pr merge --merge` (merge commit). Vermelho → parar e
   relatar.
4. Conferir que o #31 fechou (`gh issue view 31 --json state`).
5. Abrir uma issue nova, título «Transcrição: enchimento que sobra em trincas (filtro de escrita para pt)», corpo:
   depois do #31, a gravação longa só de mic ainda tem frase de enchimento até 3 vezes seguidas, e tokens em escrita
   asiática numa transcrição em português; direção medida no diagnóstico do #31: descartar trecho em escrita asiática,
   cirílico ou só pontuação quando a língua é pt, **antes** da guarda de eco (depois dela, aproxima cópias e piora);
   sozinho não resolve o enchimento latino. Link para o PR do #31. Sem frase de gravação real.
6. Relatório: URL do PR, hash do merge, estado do #31, URL da issue nova.

## Fora de escopo

- Instalar ou recompilar o app que o Gabriel usa (D4).
- O filtro de escrita e o enchimento que sobra (issue nova do passo 7.5).
- Passar o rascunho ao vivo pelo filtro.

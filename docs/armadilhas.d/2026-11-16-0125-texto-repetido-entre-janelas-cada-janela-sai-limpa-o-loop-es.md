---
titulo: Texto repetido entre janelas: cada janela sai limpa, o loop está na sequência e no contexto
data: 2026-11-16
---
**Sintoma:** a transcrição tem a mesma frase curta de enchimento dezenas de vezes seguidas (#31), e o `_degenerado` não reclama de nenhuma janela. O `tools/test_antiloop.py` também não reproduz: ele
usa janelas cegas de 30 s, sem a cadeia de contexto.

**Causa:** a defesa olhava uma janela por vez, e só acima de 40 caracteres. Janela de ruído (3 a 4 s do VAD), ou de voz
do interlocutor vazando no mic, devolve uma frase de enchimento curta; o contexto (`initial_prompt`, últimas ~30
palavras) a carrega para a janela seguinte, que repete. Conserto: `antiloop.sem_eco`, no `_merge`, fala a fala; teste
`tools/test_eco_janelas.py`.

⚠️ **Não "limpar" o contexto, nem tirar o piso de 40 do `_degenerado`, nem refazer a janela sem prompt** (os três foram
medidos em cópias). Trocar o prompt ou o refazer de uma janela muda o texto de todas as seguintes:
- tirar do contexto só o eco apagou frases reais em janelas longe do loop, e desligar o contexto perde 26% do texto;
- sem o piso, o refazer com temperatura das janelas curtas mudou o resto de uma gravação longa (frases trocadas e
  perdidas, longe do loop);
- refazer sem prompt a janela de enchimento trouxe texto novo no canal do mic; nos dois casos conferidos, era a fala do
  interlocutor vazando (já transcrita no canal do sistema), atribuída a "Eu".

E contar a repetição no canal inteiro, sem recomeçar quando o outro fala, apagaria a mesma resposta curta dada em vários
turnos: a conta é por fala, como a régua do `tools/paridade.py`. Tirar o trecho inteiro também perde fala: há trecho
que começa com a cópia do enchimento e segue com fala de verdade; sai só a cópia.

**Custo declarado:** palavra repetida de verdade mais de 3 vezes seguidas na mesma fala perde as cópias além da 3ª
("muito muito muito muito bom"), inclusive número por extenso ("zero zero zero zero"). Número em dígitos fica
(n-grama só de dígitos é isento). Em gravação só de mic, ou sem diarização, a gravação inteira é uma fala só, e a conta
vale para o arquivo inteiro: uma 4ª resposta curta idêntica seguida sai mesmo com minutos de intervalo. Recomeçar a
conta por tempo foi medido e desfaz o conserto (o enchimento vinha com até 1 min entre as cópias). O rascunho ao vivo
não passa pelo filtro.

---
titulo: NLMS ingênuo diverge quando a referência silencia (29/07/2026)
data: 2026-07-29
---
**Sintoma:** um AEC adaptativo protótipo devolveu **ERLE de −38 dB** — ou seja,
amplificou o sinal em vez de limpá-lo.

**Causa:** o passo do NLMS é normalizado pela energia da referência
(`e / potência`). Quando o canal do sistema fica em silêncio, a potência tende a
zero, o passo explode e o filtro diverge.

**O que fazer:** usar mínimos quadrados com regularização de Tikhonov relativa à
energia **do próprio bloco** (solução fechada, estável por construção), como está
em `cancel_echo`. E manter a rede de segurança que devolve o áudio original se a
saída sair mais alta que a entrada — um AEC nunca deveria aumentar o sinal.

---

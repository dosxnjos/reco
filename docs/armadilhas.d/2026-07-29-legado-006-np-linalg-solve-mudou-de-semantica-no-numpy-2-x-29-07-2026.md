---
titulo: `np.linalg.solve` mudou de semântica no numpy 2.x (29/07/2026)
data: 2026-07-29
---
**Sintoma:** `ValueError: solve: Input operand 1 has a mismatch in its core
dimension 0, with gufunc signature (m,m),(m,n)->(m,n)`.

**Causa:** com `A` de forma `(lote, P, P)` e `b` de forma `(lote, P)`, o numpy 1.x
tratava `b` como pilha de vetores; o 2.x trata como matriz e o lote não bate.

**O que fazer:** passar `b[:, :, None]` e tirar a dimensão depois:
`np.linalg.solve(A, b[:, :, None])[:, :, 0]`.

---

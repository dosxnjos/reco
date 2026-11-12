---
titulo: cargo test do casco imprime ok 0 passed do binário e dos doctests além do resultado da lib
data: 2026-11-11
---
**Sintoma:** `cargo test --manifest-path app/src-tauri/Cargo.toml bandeja` imprime **três** linhas
`test result:`: a da lib (`ok. 3 passed`) e duas `ok. 0 passed; 0 filtered out` (o binário `main.rs` e
os doctests). Quem lê só a última linha conclui "0 passed" e reprova uma prova verde; quem filtra com
`grep "test result: ok"` aprova mesmo se o filtro não casar nada na lib.

**Causa:** o crate tem lib (`reco_lib`) e bin (`reco`); o `cargo test` roda os três alvos e o filtro
vale em cada um. No bin e nos doctests não há teste, então eles sempre dão `0 passed`.

**O que fazer:** as provas da Fase 3 exigem o número de testes passados **da lib**: conferir a linha
com `[1-9]` (`grep -E "test result: ok. [1-9]"`) e ler o nome dos testes (`grep "^test "`). Para os
ignorados que precisam de `python` (motor falso), `-- --ignored <filtro>` ou `-- --include-ignored`.

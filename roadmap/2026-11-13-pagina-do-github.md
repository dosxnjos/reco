# Página do Reco no GitHub refeita para o app novo (2026-11-13)

Pedido: Reco-pagina | Página do Reco no GitHub com screenshots | de: gabriel | desde: 2026-11-13 | origem: chat
Base: Reco `0ea91f0` (2026-11-13) · Risco: nenhum (texto e imagens públicos; nada de dado pessoal)

## Contexto

O Gabriel pediu (13/11): "Reconstrua a página do reco no GitHub. screenshots etc". A página pública
(`dosxnjos/reco`, README) ainda mostra o app Tkinter (`docs/screenshot.png`) e trata o app novo (Tauri + Rust,
`app/`, roadmap `2026-11-11-melhoria-reco-em-rust.md`) como seção "em teste". Desde 12/11 o app novo é o que ele usa.

## Decisões

- D1: o README apresenta o app novo como o Reco; o Tk vira nota de histórico. Motivo: é o que roda. Reverte se a
  Fase 4 for reprovada.
- D2: screenshots saem da interface real servida com o backend falso (`app/ui`, modo mock), por Playwright headless:
  sem abrir o app instalado, sem mouse, sem dado real (nomes de arquivo e falas de exemplo). PNG em `docs/screenshots/`.
- D3: sem release nova: publicar a 0.3.0 é decisão do Gabriel e depende da aprovação da Fase 4. O README explica
  instalar pelo build (`app/build.ps1`) e cita que o release v0.2.0 é do app antigo.
- D4: descrição e tópicos do repo atualizados pelo `gh repo edit` com o token da conta pessoal só no comando.

## Passos

1. [ ] Capturas: Gravar (gravando com ao vivo, parado), Biblioteca, Arquivo, Opções; as três skins; claro e escuro;
   uma imagem de abertura com as três lado a lado — **prova:** `ls docs/screenshots/*.png | wc -l` → ≥ 8, cada uma
   ≤ 400 KB e sem caminho pessoal visível
2. [ ] README EN e PT reescrito (o que é, telas, recursos, privacidade, instalar, como funciona, para quem
   desenvolve, histórico) — **prova:** `grep -c "docs/screenshots/" README.md` → ≥ 6 e nenhum link quebrado
   (`python` simples que confere os caminhos relativos)
3. [ ] Revisão adversarial: fato contra o código (nada prometido que o app não faz) e texto sem cara de IA
4. [ ] Descrição e tópicos do repo — **prova:** `gh repo view --json description,repositoryTopics`
5. [ ] Commit, push, hub e diário

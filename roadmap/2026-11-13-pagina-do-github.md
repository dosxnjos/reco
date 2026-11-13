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

1. [x] Capturas: Gravar (gravando com ao vivo, parado), Biblioteca, Arquivo, Opções; as três skins; claro e escuro;
   uma imagem de abertura com as três lado a lado — **prova:** `ls docs/screenshots/*.png | wc -l` → ≥ 8, cada uma
   ≤ 400 KB e sem caminho pessoal visível
   - 13/11: 9 PNGs, de 86 KB (`file.png`) a 332 KB (`hero.png`), todas ≤ 400 KB; as 9 conferidas no olho: só nomes
     de arquivo e falas de exemplo do backend falso, nenhum caminho nem nome de pessoa
2. [x] README EN e PT reescrito (o que é, telas, recursos, privacidade, instalar, como funciona, para quem
   desenvolve, histórico) — **prova:** `grep -c "docs/screenshots/" README.md` → ≥ 6 e nenhum link quebrado
   (`python` simples que confere os caminhos relativos)
   - 13/11: `grep -c` → 10; o checador (caminhos relativos e âncoras dos `.md`) leu 32 links, 0 quebrados. O README
     caiu de 364 para 203 linhas: estado e instalação logo abaixo da imagem, galeria de 4 telas (as skins viraram
     links), cada idioma enxuto, testes e medições levados para `docs/ARQUITETURA.md` § Casco
3. [x] Revisão adversarial: fato contra o código (nada prometido que o app não faz) e texto sem cara de IA
   - 13/11: 24 achados, todos aplicados (NPU experimental, transcrição no idioma do app, requisito de hardware Intel,
     tempo de build 6 a 11 min, Python 3.14 como versão testada, letras das skins, "Reco Novo" fora da página,
     tríade de slogan, "exits", jargão de testes). Nenhum achado falso. O `docs/screenshot.png` antigo fica: o passo 20
     da Fase 4 (`2026-11-11-melhoria-reco-em-rust-fase-4.md:393`) ainda o usa na prova
4. [x] Descrição e tópicos do repo — **prova:** `gh repo view --json description,repositoryTopics`
   - 13/11: descrição do app novo e 10 tópicos (windows, tauri, rust, transcription, whisper, openvino,
     audio-recorder, speech-to-text, diarization, local-first) conferidos no `gh repo view`
5. [x] Commit, push, hub e diário
   - 13/11: `9c3558a` no Reco (README, 9 PNGs, ARQUITETURA, este plano), push na `master`; hub `reco.md` (Estado
     agora) e fragmento `cerebro/pessoal/diario/2026-11-13/1304-4c65eb01-reco-pagina-github.md` no `C:\Dev`

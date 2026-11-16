"""Prompt do resumo IA por idioma (ação ✦ da biblioteca; motor: `engine/reco_engine/extras.py`).

Roda via `claude -p` — o CLI do Claude Code que o usuário já tem — com a transcrição no stdin: sem chave de
API no app, sem rede própria, e tudo segue funcional sem o CLI (decisão de 02/08/2026, hub do projeto: camada
de IA pessoal via claude -p, nunca LLM embarcado no bundle). A saída vira <gravação>.resumo.md ao lado do
áudio. Fora do reco.py desde 15/11/2026 (trava de tamanho); o reco.py re-exporta `PROMPT_RESUMO`.
O prompt em polonês é de Toni Nowak (PR #7). Os rótulos citados ('Eu', 'Me', 'Ja'…) são os de `_spk_me` e
`_spk_them` no reco.py: mudou um lado, muda o outro.
"""

PROMPT_RESUMO = {
    "pt": ("Você recebe no stdin a transcrição de uma reunião. As falas podem "
           "vir rotuladas por 'Eu' (quem gravou) e 'Interlocutor(es)' (o outro "
           "lado). Escreva em português, em markdown puro, exatamente estas "
           "seções: '## Resumo' (3-6 frases), '## Decisões' (bullets; 'nenhuma "
           "registrada' se não houver) e '## Pendências e próximos passos' "
           "(bullets, com o dono quando o texto disser). Seja fiel ao texto; "
           "não invente nomes nem fatos. Responda só com o markdown."),
    "en": ("You receive a meeting transcript on stdin. Lines may be labeled "
           "'Me' (the recorder) and 'Speaker(s)' (the other side). Write in "
           "English, plain markdown, exactly these sections: '## Summary' "
           "(3-6 sentences), '## Decisions' (bullets; 'none recorded' if "
           "empty) and '## Action items' (bullets, with owners when stated). "
           "Stay faithful to the text; invent no names or facts. Reply with "
           "the markdown only."),
    "pl": ("Otrzymujesz na stdin transkrypcję spotkania. Wypowiedzi mogą być "
           "opatrzone etykietami 'Ja' (osoba, która nagrywała) i 'Rozmówca(y)' "
           "(druga strona). Pisz po polsku, w czystym markdownie, dokładnie te "
           "sekcje: '## Podsumowanie' (3-6 zdań), '## Decyzje' (lista "
           "punktowana; 'brak zarejestrowanych', jeśli lista jest pusta) oraz "
           "'## Zadania i następne kroki' (lista punktowana, z podaniem osoby "
           "odpowiedzialnej, gdy wynika to z tekstu). Trzymaj się tekstu; nie "
           "wymyślaj nazwisk ani faktów. Odpowiedz wyłącznie markdownem."),
}

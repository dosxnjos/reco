"""Traduções PT->PL da janela Tk (app velho): chave = frase PT, valor = polonês.

Tabela de Toni Nowak (PR #7, 25/09/2026), fora do reco.py pela trava de tamanho
(tools/tamanho.json). O reco.py a importa como _TR_PL; o tools/check_i18n.py confere a cobertura.
"""

TR_PL: dict = {
    # header / meters
    "MIC": "MIKROFON",
    "SISTEMA": "SYSTEM",
    # buttons
    "Gravar": "Nagrywaj",
    "Parar": "Zatrzymaj",
    "Salvar": "Zapisz",
    "Transcrever": "Transkrybuj",
    "Excluir": "Usuń",
    "Transcrever + excluir": "Transkrybuj + usuń",
    "Reproduzir": "Odtwórz",
    "Salvar + Transcrever": "Zapisz + transkrybuj",
    "Tema:": "Motyw:",
    "Fundo": "Tło",
    "Destaque": "Akcent",
    "Padrão": "Domyślny",
    "Cor de fundo": "Kolor tła",
    "Cor de destaque": "Kolor akcentu",
    # links
    "Opções": "Opcje",
    "Ocultar opções": "Ukryj opcje",
    "Transcrever…": "Transkrybuj…",
    "← Gravar": "← Nagrywaj",
    # advanced labels
    "Entrada:": "Wejście:",
    "Saída:": "Wyjście:",
    "Pasta:": "Folder:",
    "Alterar…": "Zmień…",
    "Pasta de gravações": "Folder nagrań",
    "Atualizar dispositivos": "Odśwież urządzenia",
    "Processar em:": "Uruchom na:",
    "Idioma:": "Język:",
    "Criar atalho (Ctrl+Shift+R)": "Utwórz skrót (Ctrl+Shift+R)",
    "Remover atalho": "Usuń skrót",
    "Atalho criado — abra pelo Menu Iniciar ou com Ctrl+Shift+R.":
        "Skrót utworzony — otwórz go z Menu Start lub za pomocą "
        "Ctrl+Shift+R.",
    "Atalho removido.": "Skrót usunięty.",
    "Não foi possível criar o atalho: {e}":
        "Nie udało się utworzyć skrótu: {e}",
    "Preparando '{size}' no {dev} pela primeira vez — isso leva alguns minutos "
    "e só acontece uma vez.":
        "Przygotowywanie '{size}' na {dev} — pierwsza konfiguracja może "
        "potrwać kilka minut i dzieje się tylko raz.",
    # status — devices
    "Pronto para gravar.": "Gotowe do nagrywania.",
    "Buscando dispositivos…": "Wyszukiwanie urządzeń…",
    "Erro ao listar dispositivos: {m}":
        "Błąd podczas pobierania listy urządzeń: {m}",
    "Nenhum dispositivo de áudio encontrado.": "Nie znaleziono urządzeń audio.",
    "Atenção: nenhuma saída de áudio para loopback.":
        "Uwaga: brak wyjścia audio dla loopbacku.",
    "Não é possível atualizar dispositivos durante a gravação.":
        "Nie można odświeżyć urządzeń podczas nagrywania.",
    "Captura indisponível — instale soundcard, numpy e av.":
        "Przechwytywanie niedostępne — zainstaluj soundcard, numpy i av.",
    "Nenhuma fonte de áudio — abra Opções.":
        "Brak źródła dźwięku — otwórz Opcje.",
    # status — recording
    "microfone": "mikrofon",
    "áudio do sistema": "dźwięk systemowy",
    "Nenhuma fonte pôde ser capturada ({which}): {m}":
        "Nie udało się przechwycić żadnego źródła ({which}): {m}",
    "Falha ao capturar {which} (a outra fonte continua).":
        "Nie udało się przechwycić {which} (pozostałe źródło działa nadal).",
    "Salvando…": "Zapisywanie…",
    "Erro ao salvar: {m}": "Błąd podczas zapisywania: {m}",
    "Nenhum áudio capturado — verifique as fontes selecionadas.":
        "Nie przechwycono żadnego dźwięku — sprawdź wybrane źródła.",
    "Salvo: {n}  —  Escolha o que fazer:":
        "Zapisano: {n}  —  Wybierz, co dalej:",
    "Gravação salva: {n}": "Zapisano nagranie: {n}",
    "Gravação descartada.": "Nagranie odrzucone.",
    "Não foi possível excluir: {e}": "Nie udało się usunąć: {e}",
    "Não foi possível excluir.": "Nie udało się usunąć.",
    "Rascunho ao vivo desativado — transcrição em andamento.":
        "Wyłączono szkic na żywo — transkrypcja już trwa.",
    "Termine a gravação para trocar de tela.":
        "Zakończ nagrywanie, aby zmienić ekran.",
    "Termine a transcrição para trocar de tela.":
        "Zakończ transkrypcję, aby zmienić ekran.",
    "Termine a conversão para trocar de tela.":
        "Zakończ konwersję, aby zmienić ekran.",
    "Transcrição ao vivo (rascunho)": "Transkrypcja na żywo (szkic)",
    "Fechando rascunho ao vivo…": "Zamykanie szkicu na żywo…",
    "Salvo: {n}  —  refinando a transcrição…":
        "Zapisano: {n}  —  dopracowywanie transkrypcji…",
    "Rascunho mantido — passada final falhou: {e}":
        "Szkic zachowano — ostateczne dopracowanie nie powiodło się: {e}",
    "Transcrição final pronta: {n}": "Ostateczna transkrypcja gotowa: {n}",
    "Transcrição final pronta (falha ao salvar o .txt).":
        "Ostateczna transkrypcja gotowa (nie udało się zapisać pliku .txt).",
    "Transcrição ao vivo atrasada — descartando áudio antigo do rascunho.":
        "Transkrypcja na żywo nie nadąża — odrzucanie starszego audio "
        "ze szkicu.",
    "Transcrição ao vivo parou (a gravação continua).":
        "Transkrypcja na żywo się zatrzymała (nagrywanie trwa nadal).",
    # status — transcription
    "Nada para transcrever.": "Nic do transkrypcji.",
    "Nada para reproduzir.": "Nic do odtworzenia.",
    "Arquivo não encontrado.": "Nie znaleziono pliku.",
    "Já há uma transcrição em andamento.": "Transkrypcja już trwa.",
    "Transcrição indisponível — instale openvino-genai.":
        "Transkrypcja niedostępna — zainstaluj openvino-genai.",
    "Transcrevendo {n}…": "Transkrybowanie {n}…",
    "Transcrevendo… {p}%": "Transkrybowanie… {p}%",
    "Baixando modelo '{size}' (primeira vez)…":
        "Pobieranie modelu '{size}' (pierwszy raz)…",
    "Sem internet — usando o modelo '{size}' embutido.":
        "Brak internetu — używany jest wbudowany model '{size}'.",
    "Preparando modelo no {dev}…": "Przygotowywanie modelu na {dev}…",
    "Carregando áudio…": "Wczytywanie audio…",
    "Atualizando modelo…": "Aktualizowanie modelu…",
    "Modelo atualizado.": "Model zaktualizowany.",
    "Nova versão {tag}": "Nowa wersja {tag}",
    "Erro na transcrição: {e}": "Błąd transkrypcji: {e}",
    "Transcrito, mas falha ao salvar o .txt.":
        "Ztranskrybowano, ale nie udało się zapisać pliku .txt.",
    "Transcrição salva: {n}. Áudio excluído.":
        "Zapisano transkrypcję: {n}. Plik audio usunięty.",
    "Transcrição salva: {n}": "Zapisano transkrypcję: {n}",
    # transcribe section
    "TRANSCRIÇÃO": "TRANSKRYPCJA",
    "Escolher arquivo…": "Wybierz plik…",
    "Transcrição cancelada.": "Transkrypcja anulowana.",
    "Salvo: {n}": "Zapisano: {n}",
    # tray
    "Abrir": "Otwórz",
    "Sair": "Zakończ",
    "Reco — pronto": "Reco — gotowe",
    "Reco — gravando {d}": "Reco — nagrywanie {d}",
    "Reco — salvando gravação…": "Reco — zapisywanie nagrania…",
    "Salvando antes de sair…": "Zapisywanie przed zakończeniem…",
    "Reco — pausado {d}": "Reco — pauza {d}",
    # pause / resume
    "Pausar": "Wstrzymaj",
    "Continuar": "Wznów",
    "Pausado — {d} gravado.": "Wstrzymano — nagrano {d}.",
    # convert section (video/heavy audio → light MP3)
    "Converter…": "Konwertuj…",
    "CONVERSÃO": "KONWERSJA",
    "Escolher vídeo ou áudio…": "Wybierz wideo lub audio…",
    "Selecionar vídeo ou áudio": "Wybierz plik wideo lub audio",
    "Converter para MP3": "Konwertuj na MP3",
    "MP3 leve: {sr} kHz mono, {br} kbps.":
        "Lekki MP3: {sr} kHz mono, {br} kbps.",
    "Origem: {a}": "Źródło: {a}",
    "Convertendo… {p}%": "Konwertowanie… {p}%",
    "MP3 salvo: {n}  ({a} → {b})": "Zapisano MP3: {n}  ({a} → {b})",
    "O arquivo não tem faixa de áudio.": "Plik nie zawiera ścieżki dźwiękowej.",
    "Falha ao converter: {e}": "Błąd konwersji: {e}",
    "Já há uma conversão em andamento.": "Konwersja już trwa.",
    "Conversão indisponível — instale av.":
        "Konwersja niedostępna — zainstaluj av.",
    "Vídeo": "Wideo",
    "Abrir pasta": "Otwórz folder",
    "Abrir transcrição": "Otwórz transkrypcję",
    # recordings library (view "Gravações…")
    "Gravações…": "Nagrania…",
    "GRAVAÇÕES": "NAGRANIA",
    "Buscar:": "Szukaj:",
    "Arquivo": "Plik",
    "Data": "Data",
    "Duração": "Czas trwania",
    "Atualizar": "Odśwież",
    "Lendo gravações…": "Wczytywanie nagrań…",
    "Nenhuma gravação encontrada.": "Nie znaleziono nagrań.",
    "Selecione uma gravação.": "Zaznacz nagranie.",
    "Enviada para a Lixeira: {n}": "Przeniesiono do Kosza: {n}",
    # AI summary (library ✦ action, via the user's Claude Code CLI)
    "Resumo IA": "Podsumowanie AI",
    "Gerando resumo com o Claude…": "Generowanie podsumowania za pomocą Claude…",
    "Resumo salvo: {n}": "Zapisano podsumowanie: {n}",
    "Falha ao gerar o resumo: {e}":
        "Nie udało się wygenerować podsumowania: {e}",
    "Resumo indisponível — instale o Claude Code (comando 'claude').":
        "Podsumowanie niedostępne — zainstaluj Claude Code "
        "(polecenie 'claude').",
    "Já há um resumo em andamento.": "Generowanie podsumowania już trwa.",
    "Selecione um arquivo e clique em Transcrever.":
        "Wybierz plik i kliknij Transkrybuj.",
    "Selecione um arquivo válido.": "Wybierz prawidłowy plik.",
    "Erro: {e}": "Błąd: {e}",
    "Selecionar áudio": "Wybierz plik audio",
    "Áudio": "Audio", "Todos": "Wszystkie pliki",
    # dependency messagebox
    "Dependências ausentes": "Brakujące zależności",
    "Para gravar áudio, instale as dependências:\n\n  pip install {pkgs}\n\n"
    "Abra um terminal e rode o comando acima. Depois, reinicie o {app}.":
        "Aby nagrywać dźwięk, zainstaluj wymagane zależności:\n\n"
        "  pip install {pkgs}\n\n"
        "Otwórz terminal i wykonaj powyższe polecenie. "
        "Następnie uruchom ponownie {app}.",
    # chaves novas do master (15/11/2026): textos que nasceram depois do PR #7,
    # no glossário de Toni (nagranie, notatka, Opcje, mikrofon, system, Wejście/Wyjście)
    # modo nota
    "Nenhum microfone selecionado — abra Opções.":
        "Nie wybrano mikrofonu — otwórz Opcje.",
    "Gravando nota…  (só microfone)": "Nagrywanie notatki…  (tylko mikrofon)",
    "Salvo: {n}  —  transcrevendo…": "Zapisano: {n}  —  transkrybowanie…",
    "Nota preservada: {n}  —  {e}": "Notatka zachowana: {n}  —  {e}",
    "Nota preservada: {n}  —  falha ao salvar: {e}":
        "Notatka zachowana: {n}  —  błąd podczas zapisywania: {e}",
    "Nota pronta — caminho copiado": "Notatka gotowa — ścieżka skopiowana",
    # gravação
    "Gravando…  mic: {m} · sistema: {s}":
        "Nagrywanie…  mikrofon: {m} · system: {s}",
    "Salvar e copiar caminho": "Zapisz i skopiuj ścieżkę",
    "Salvo — caminho copiado: {n}": "Zapisano — skopiowano ścieżkę: {n}",
    "Gravação salva: {n} (falha ao copiar o caminho)":
        "Zapisano nagranie: {n} (nie udało się skopiować ścieżki)",
    # dispositivos "Auto" (roadmap 2026-09-30-melhoria-dispositivo-auto)
    # os três primeiros vão no combo de dispositivo (width=24): curtos de propósito
    "Auto: padrão do Windows ({nome})": "Auto: domyślne w Windows ({nome})",
    "Auto: padrão de comunicação ({nome})": "Auto: domyślne do komunikacji ({nome})",
    "Dispositivo salvo (ausente: usando o padrão do Windows)":
        "Zapisane urządzenie (niedostępne: domyślne w Windows)",
    "{canal} escolhida ausente: usando o padrão do Windows ({nome})":
        "{canal} — wybrane urządzenie niedostępne: używane jest domyślne urządzenie "
        "Windows ({nome})",
    "Entrada": "Wejście",
    "Saída": "Wyjście",
}

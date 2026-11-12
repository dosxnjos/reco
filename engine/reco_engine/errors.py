"""Códigos de erro do protocolo (docs/PROTOCOL.md § Códigos). A interface traduz; o motor só emite o código."""

CODES = frozenset({
    "bad_args",          # argumento ausente, de tipo errado ou chave de config desconhecida
    "busy",              # já há gravação/transcrição/resumo/conversão em andamento
    "cancelled",         # o pedido foi cancelado (transcribe.cancel)
    "claude_missing",    # `claude` fora do PATH (resumo IA)
    "internal",          # linha ilegível, cmd desconhecido, id repetido, exceção não prevista
    "no_audio",          # a gravação parou sem nenhuma amostra capturada
    "no_audio_stream",   # o arquivo não tem trilha de áudio (conversão)
    "no_device",         # nenhum dispositivo de captura resolvido
    "not_found",         # arquivo/gravação ausente
    "refused",           # pedido recusado por regra (ex.: excluir fora da biblioteca)
    "save_failed",       # o arquivo não pôde ser gravado (MP3, config, .txt)
    "unavailable",       # `reco` não importou a tempo, ou backend (soundcard/av/openvino) ausente
})


class EngineError(Exception):
    """Falha esperada de um comando: vira `{"ok":false,"error":{"code","detail"}}`."""

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in CODES:
            detail = f"{code}: {detail}"
            code = "internal"
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def short(e: BaseException, limit: int = 200) -> str:
    """Texto técnico curto de uma exceção, para o `detail`."""
    s = f"{type(e).__name__}: {e}"
    return s if len(s) <= limit else s[: limit - 1] + "…"

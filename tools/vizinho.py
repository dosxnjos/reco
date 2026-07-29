"""'Outro app aberto': processo separado, single-thread, que acorda a cada 50 ms,
faz um trabalho fixo e mede quanto tempo ele levou.

E o modelo de um app interativo real (UI que acorda, desenha, dorme) — nao de um
segundo job pesado. A metrica que importa e LATENCIA: se o trabalho que leva 5 ms
com a maquina ociosa passa a levar 40 ms durante a transcricao, o app engasga, e o
usuario ve isso. Throughput agregado nao captura esse efeito.

Imprime uma linha JSON por janela de 2 s. Nao usa numpy de proposito: BLAS e
multi-thread e ocuparia todos os nucleos, que e justamente o que nao queremos
simular aqui.
"""
import json, sys, time

TRABALHO = 60_000     # iteracoes por acorda-da — calibrado p/ ~2-5 ms ocioso
PERIODO = 0.05        # acorda a cada 50 ms
JANELA = 2.0          # reporta a cada 2 s


def tarefa():
    x = 0.0
    for i in range(TRABALHO):
        x += i * 0.5
    return x


def main():
    amostras, jitters = [], []
    t_janela = time.perf_counter()
    prox = time.perf_counter()
    while True:
        prox += PERIODO
        dorme = prox - time.perf_counter()
        if dorme > 0:
            time.sleep(dorme)
        jitters.append((time.perf_counter() - prox) * 1000)   # atraso p/ acordar
        t0 = time.perf_counter()
        tarefa()
        amostras.append((time.perf_counter() - t0) * 1000)    # duracao do trabalho

        agora = time.perf_counter()
        if agora - t_janela >= JANELA:
            a = sorted(amostras)
            j = sorted(jitters)
            p = lambda v, q: v[min(len(v) - 1, int(len(v) * q))] if v else 0.0
            print(json.dumps({
                "t": round(agora, 2),
                "trabalho_p50": round(p(a, 0.5), 1),
                "trabalho_p95": round(p(a, 0.95), 1),
                "acorda_p95": round(p(j, 0.95), 1),
                "n": len(a),
            }), flush=True)
            amostras, jitters, t_janela = [], [], agora


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

"""
Regras de negócio: cálculo da perda, classificação e recomendações.

A ideia central: o produtor informa quanto ESPERAVA colher no talhão
(área x produtividade estimada) e quanto REALMENTE colheu. A diferença
é a perda, que é classificada de acordo com o tipo de colheita, já que
a referência da SOCICANA é de até ~5% na manual e até ~15% na mecanizada.
"""

from validacoes import formatar_numero

# Tuplas: dados fixos que não devem ser alterados durante a execução
TIPOS_COLHEITA = ("MANUAL", "MECANIZADA")
CLASSIFICACOES = ("ACEITAVEL", "ATENCAO", "CRITICA")
ICONES_CLASSIFICACAO = {"ACEITAVEL": "🟢", "ATENCAO": "🟡", "CRITICA": "🔴"}


def calcular_producao_esperada(area_ha: float, prod_estimada_t_ha: float) -> float:
    """Toneladas que o talhão deveria render."""
    return round(area_ha * prod_estimada_t_ha, 2)


def calcular_perda(area_ha: float, prod_estimada_t_ha: float,
                   toneladas_colhidas: float, preco_tonelada: float) -> tuple:
    """
    Devolve uma tupla (perda_t, perda_perc, perda_rs).
    Se o colhido for maior que o esperado, a perda é zero (estimativa conservadora).
    """
    esperado = calcular_producao_esperada(area_ha, prod_estimada_t_ha)
    perda_t = max(esperado - toneladas_colhidas, 0.0)
    perda_perc = (perda_t / esperado) * 100 if esperado > 0 else 0.0
    perda_rs = perda_t * preco_tonelada
    return round(perda_t, 2), round(perda_perc, 2), round(perda_rs, 2)


def classificar_perda(perda_perc: float, tipo_colheita: str, limites: dict) -> str:
    """Classifica a perda conforme os limites do config.json para cada tipo."""
    faixa = limites[tipo_colheita]
    if perda_perc <= faixa["aceitavel"]:
        return CLASSIFICACOES[0]
    if perda_perc <= faixa["atencao"]:
        return CLASSIFICACOES[1]
    return CLASSIFICACOES[2]


def gerar_recomendacoes(colheita: dict, boas_praticas: dict) -> list:
    """
    Diferencial da solução: em vez de só mostrar o número, o sistema aponta
    a provável causa da perda e o que fazer na próxima colheita.
    """
    recomendacoes = []

    if colheita["tipo_colheita"] == "MECANIZADA":
        velocidade = colheita.get("velocidade_kmh")
        altura = colheita.get("altura_corte_cm")
        if velocidade is not None and velocidade > boas_praticas["velocidade_max_kmh"]:
            recomendacoes.append(
                f"Velocidade de {formatar_numero(velocidade)} km/h acima do ideal "
                f"({formatar_numero(boas_praticas['velocidade_max_kmh'])} km/h): reduza para diminuir "
                "pedaços de cana lançados pelo extrator."
            )
        if altura is not None and altura > boas_praticas["altura_corte_max_cm"]:
            recomendacoes.append(
                f"Altura de corte de {formatar_numero(altura)} cm acima do ideal "
                f"({formatar_numero(boas_praticas['altura_corte_max_cm'])} cm): tocos altos deixam "
                "a parte mais rica em sacarose no campo. Regule o corte de base."
            )

    if colheita["classificacao"] == "CRITICA":
        recomendacoes.append(
            "Perda crítica: revise o planejamento do talhão (sistematização do terreno, "
            "espaçamento entre linhas compatível com a colhedora) e o treinamento do operador."
        )
    elif colheita["classificacao"] == "ATENCAO":
        recomendacoes.append(
            "Perda em atenção: acompanhe as próximas colheitas deste talhão e "
            "verifique o estado das facas e do extrator da colhedora."
        )

    if not recomendacoes:
        recomendacoes.append("Colheita dentro do esperado. Mantenha os parâmetros atuais.")
    return recomendacoes


def resumo_geral(colheitas: list) -> dict:
    """Indicadores consolidados da tabela de memória."""
    if not colheitas:
        return {}
    total_esperado = sum(calcular_producao_esperada(c["area_ha"], c["prod_estimada_t_ha"])
                         for c in colheitas)
    total_perda_t = sum(c["perda_t"] for c in colheitas)
    resumo = {
        "qtd_colheitas": len(colheitas),
        "area_total_ha": round(sum(c["area_ha"] for c in colheitas), 2),
        "toneladas_colhidas": round(sum(c["toneladas_colhidas"] for c in colheitas), 2),
        "perda_total_t": round(total_perda_t, 2),
        "perda_total_rs": round(sum(c["perda_rs"] for c in colheitas), 2),
        "perda_media_perc": round(total_perda_t / total_esperado * 100, 2) if total_esperado else 0.0,
        "por_tipo": {},
        "por_classificacao": {classe: 0 for classe in CLASSIFICACOES},
    }
    for tipo in TIPOS_COLHEITA:
        do_tipo = [c for c in colheitas if c["tipo_colheita"] == tipo]
        if do_tipo:
            resumo["por_tipo"][tipo] = round(sum(c["perda_perc"] for c in do_tipo) / len(do_tipo), 2)
    for c in colheitas:
        resumo["por_classificacao"][c["classificacao"]] += 1
    return resumo


def ranking_colhedoras(colheitas: list) -> list:
    """
    Agrupa as colheitas mecanizadas por colhedora e ordena pela perda média.
    Devolve lista de tuplas: (colhedora, qtd_colheitas, perda_media_perc, perda_total_rs)
    """
    agrupado = {}
    for c in colheitas:
        if c["tipo_colheita"] != "MECANIZADA" or not c.get("colhedora"):
            continue
        dados = agrupado.setdefault(c["colhedora"], {"qtd": 0, "soma_perc": 0.0, "soma_rs": 0.0})
        dados["qtd"] += 1
        dados["soma_perc"] += c["perda_perc"]
        dados["soma_rs"] += c["perda_rs"]

    ranking = [(nome, d["qtd"], round(d["soma_perc"] / d["qtd"], 2), round(d["soma_rs"], 2))
               for nome, d in agrupado.items()]
    return sorted(ranking, key=lambda item: item[2])

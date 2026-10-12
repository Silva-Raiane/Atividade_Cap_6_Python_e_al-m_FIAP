"""
Manipulação de arquivos texto e JSON.

- config/config.json ............ parâmetros do sistema (leitura)
- data/colheitas_backup.json .... exportação/importação da tabela de memória
- data/colheitas_offline.json ... "banco" local usado quando o Oracle está indisponível
- data/relatorio_colheitas.txt .. relatório legível para o produtor
- data/log_operacoes.txt ........ histórico de tudo o que foi feito no sistema
"""

import json
import os
from datetime import date, datetime

from calculos import (ICONES_CLASSIFICACAO, calcular_producao_esperada,
                      ranking_colhedoras, resumo_geral)
from validacoes import formatar_moeda, formatar_numero

PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_CONFIG = os.path.join(PASTA_RAIZ, "config", "config.json")
PASTA_DADOS = os.path.join(PASTA_RAIZ, "data")
CAMINHO_BACKUP = os.path.join(PASTA_DADOS, "colheitas_backup.json")
CAMINHO_OFFLINE = os.path.join(PASTA_DADOS, "colheitas_offline.json")
CAMINHO_RELATORIO = os.path.join(PASTA_DADOS, "relatorio_colheitas.txt")
CAMINHO_LOG = os.path.join(PASTA_DADOS, "log_operacoes.txt")

CAMPOS_OBRIGATORIOS = ("talhao", "data_colheita", "tipo_colheita", "area_ha",
                       "prod_estimada_t_ha", "toneladas_colhidas", "perda_t",
                       "perda_perc", "perda_rs", "classificacao")


def carregar_config(caminho: str = CAMINHO_CONFIG) -> dict:
    """Lê o arquivo de configuração JSON."""
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def registrar_log(mensagem: str) -> None:
    """Procedimento: acrescenta uma linha com data/hora ao log em texto."""
    os.makedirs(PASTA_DADOS, exist_ok=True)
    carimbo = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(CAMINHO_LOG, "a", encoding="utf-8") as arquivo:
        arquivo.write(f"[{carimbo}] {mensagem}\n")


def _para_json(colheita: dict) -> dict:
    """Converte a data para texto, já que JSON não tem tipo data."""
    copia = dict(colheita)
    if isinstance(copia["data_colheita"], date):
        copia["data_colheita"] = copia["data_colheita"].isoformat()
    return copia


def _de_json(registro: dict) -> dict:
    copia = dict(registro)
    copia["data_colheita"] = date.fromisoformat(copia["data_colheita"])
    return copia


def exportar_json(colheitas: list, caminho: str = CAMINHO_BACKUP) -> str:
    """Grava a tabela de memória inteira em JSON e devolve o caminho."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    conteudo = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "total_registros": len(colheitas),
        "colheitas": [_para_json(c) for c in colheitas],
    }
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=4)
    return caminho


def importar_json(caminho: str = CAMINHO_BACKUP) -> list:
    """
    Lê um backup JSON e devolve só os registros completos e válidos.
    Registros com campos faltando são ignorados (e contados no log).
    """
    with open(caminho, "r", encoding="utf-8") as arquivo:
        conteudo = json.load(arquivo)

    validos, ignorados = [], 0
    for registro in conteudo.get("colheitas", []):
        if all(campo in registro for campo in CAMPOS_OBRIGATORIOS):
            try:
                validos.append(_de_json(registro))
                continue
            except (ValueError, TypeError):
                pass
        ignorados += 1
    if ignorados:
        registrar_log(f"Importação JSON: {ignorados} registro(s) inválido(s) ignorado(s).")
    return validos


def gerar_relatorio_txt(colheitas: list, preco_tonelada: float,
                        caminho: str = CAMINHO_RELATORIO) -> str:
    """Gera um relatório em texto puro, fácil de imprimir ou enviar ao produtor."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    resumo = resumo_geral(colheitas)
    linhas = [
        "=" * 78,
        "FARMTECH SOLUTIONS - RELATÓRIO DE PERDAS NA COLHEITA DE CANA-DE-AÇÚCAR",
        f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Preço de referência da tonelada: {formatar_moeda(preco_tonelada)}",
        "=" * 78,
        "",
        "1. RESUMO GERAL",
        "-" * 78,
        f"Colheitas registradas ....: {resumo['qtd_colheitas']}",
        f"Área total colhida .......: {formatar_numero(resumo['area_total_ha'])} ha",
        f"Toneladas colhidas .......: {formatar_numero(resumo['toneladas_colhidas'])} t",
        f"Perda total ..............: {formatar_numero(resumo['perda_total_t'])} t",
        f"Perda média ponderada ....: {formatar_numero(resumo['perda_media_perc'])} %",
        f"Prejuízo estimado ........: {formatar_moeda(resumo['perda_total_rs'])}",
        "",
        "Perda média por tipo de colheita:",
    ]
    for tipo, media in resumo["por_tipo"].items():
        linhas.append(f"   - {tipo:<11}: {formatar_numero(media)} %")
    linhas.append("")
    linhas.append("Colheitas por classificação:")
    for classe, qtd in resumo["por_classificacao"].items():
        linhas.append(f"   - {classe:<10}: {qtd}")

    linhas += ["", "2. DETALHAMENTO", "-" * 78,
               f"{'ID':>4} {'TALHÃO':<10} {'DATA':<10} {'TIPO':<10} "
               f"{'ESPERADO(t)':>11} {'PERDA %':>8} {'PREJUÍZO':>15}  CLASSE"]
    for c in colheitas:
        esperado = calcular_producao_esperada(c["area_ha"], c["prod_estimada_t_ha"])
        linhas.append(
            f"{c.get('id_colheita') or '-':>4} {c['talhao'][:10]:<10} "
            f"{c['data_colheita'].strftime('%d/%m/%Y'):<10} {c['tipo_colheita']:<10} "
            f"{formatar_numero(esperado):>11} {formatar_numero(c['perda_perc']):>8} "
            f"{formatar_moeda(c['perda_rs']):>15}  {c['classificacao']}"
        )

    ranking = ranking_colhedoras(colheitas)
    if ranking:
        linhas += ["", "3. RANKING DE COLHEDORAS (menor perda primeiro)", "-" * 78]
        for posicao, (nome, qtd, media, total_rs) in enumerate(ranking, start=1):
            linhas.append(f"{posicao}º {nome:<15} {qtd} colheita(s)  "
                          f"perda média {formatar_numero(media)} %  "
                          f"prejuízo {formatar_moeda(total_rs)}")

    linhas += ["", "=" * 78, "Fim do relatório."]
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")
    return caminho


def icone(classificacao: str) -> str:
    return ICONES_CLASSIFICACAO.get(classificacao, "")

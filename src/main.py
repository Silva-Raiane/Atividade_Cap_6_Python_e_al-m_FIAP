"""
FarmTech Solutions - Monitor de Perdas na Colheita de Cana-de-Açúcar
Programa principal (menu no prompt de comando).

Execução:  python src/main.py
"""

import sys

import arquivos
import banco
from calculos import (TIPOS_COLHEITA, calcular_perda, calcular_producao_esperada,
                      classificar_perda, gerar_recomendacoes, ranking_colhedoras,
                      resumo_geral)
from validacoes import (confirmar, formatar_moeda, formatar_numero, ler_data,
                        ler_float, ler_inteiro, ler_opcao, ler_texto)

# Tupla de opções do menu: (número, descrição)
OPCOES_MENU = (
    ("1", "Registrar nova colheita"),
    ("2", "Listar colheitas"),
    ("3", "Ver detalhes e recomendações de uma colheita"),
    ("4", "Alterar colheita"),
    ("5", "Excluir colheita"),
    ("6", "Painel de indicadores e ranking de colhedoras"),
    ("7", "Exportar backup em JSON"),
    ("8", "Importar backup em JSON"),
    ("9", "Gerar relatório em TXT"),
    ("0", "Sair"),
)

CAMPOS_EDITAVEIS = ("Talhão", "Data da colheita", "Tipo de colheita", "Área (ha)",
                    "Produtividade estimada (t/ha)", "Toneladas colhidas",
                    "Dados da colhedora (nome, velocidade, altura de corte)")

# Estado da aplicação
CONFIG = {}
CONEXAO = None          # conexão Oracle; None = modo offline
COLHEITAS = []          # tabela de memória: lista de dicionários


# ----------------------------------------------------------------------------
# Procedimentos de interface
# ----------------------------------------------------------------------------
def exibir_cabecalho(titulo: str) -> None:
    print("\n" + "=" * 70)
    print(f"  🌱 {titulo}")
    print("=" * 70)


def pausar() -> None:
    input("\nPressione ENTER para continuar...")


def exibir_menu() -> None:
    exibir_cabecalho(CONFIG["sistema"]["nome"])
    modo = "🟢 Conectado ao Oracle" if CONEXAO else "🟠 Modo offline (dados salvos em JSON)"
    print(f"  {modo}  |  {len(COLHEITAS)} colheita(s) carregada(s)\n")
    for numero, descricao in OPCOES_MENU:
        print(f"  [{numero}] {descricao}")
    print()


def exibir_tabela(colheitas: list) -> None:
    """Procedimento: imprime as colheitas em forma de tabela alinhada."""
    print(f"\n  {'ID':>4}  {'TALHÃO':<10} {'DATA':<10}  {'TIPO':<10} {'COLHEDORA':<10}"
          f" {'PERDA %':>8} {'PREJUÍZO':>15}   SITUAÇÃO")
    print("  " + "-" * 92)
    for c in colheitas:
        print(f"  {c['id_colheita']:>4}  {c['talhao'][:10]:<10} "
              f"{c['data_colheita'].strftime('%d/%m/%Y'):<10}  {c['tipo_colheita']:<10} "
              f"{(c.get('colhedora') or '-')[:10]:<10} {formatar_numero(c['perda_perc']):>8} "
              f"{formatar_moeda(c['perda_rs']):>15}   "
              f"{arquivos.icone(c['classificacao'])} {c['classificacao']}")
    print("  " + "-" * 92)


def exibir_detalhes(c: dict) -> None:
    """Procedimento: mostra uma colheita completa com as recomendações."""
    esperado = calcular_producao_esperada(c["area_ha"], c["prod_estimada_t_ha"])
    print(f"\n  Colheita #{c['id_colheita']} - Talhão {c['talhao']}")
    print("  " + "-" * 50)
    print(f"  Data ......................: {c['data_colheita'].strftime('%d/%m/%Y')}")
    print(f"  Tipo ......................: {c['tipo_colheita']}")
    if c["tipo_colheita"] == "MECANIZADA":
        print(f"  Colhedora .................: {c.get('colhedora') or '-'}")
        print(f"  Velocidade ................: {formatar_numero(c['velocidade_kmh'])} km/h")
        print(f"  Altura de corte ...........: {formatar_numero(c['altura_corte_cm'])} cm")
    print(f"  Área ......................: {formatar_numero(c['area_ha'])} ha")
    print(f"  Produtividade estimada ....: {formatar_numero(c['prod_estimada_t_ha'])} t/ha")
    print(f"  Produção esperada .........: {formatar_numero(esperado)} t")
    print(f"  Toneladas colhidas ........: {formatar_numero(c['toneladas_colhidas'])} t")
    print(f"  Perda .....................: {formatar_numero(c['perda_t'])} t "
          f"({formatar_numero(c['perda_perc'])} %)")
    print(f"  Prejuízo estimado .........: {formatar_moeda(c['perda_rs'])}")
    print(f"  Situação ..................: {arquivos.icone(c['classificacao'])} {c['classificacao']}")
    print("\n  💡 Recomendações:")
    for indice, texto in enumerate(gerar_recomendacoes(c, CONFIG["boas_praticas_mecanizada"]), 1):
        print(f"     {indice}. {texto}")


# ----------------------------------------------------------------------------
# Funções de apoio
# ----------------------------------------------------------------------------
def recalcular(colheita: dict) -> dict:
    """Recalcula perda, prejuízo e classificação a partir dos dados digitados."""
    perda_t, perda_perc, perda_rs = calcular_perda(
        colheita["area_ha"], colheita["prod_estimada_t_ha"], colheita["toneladas_colhidas"],
        CONFIG["parametros_economicos"]["preco_tonelada_cana_rs"])
    colheita["perda_t"] = perda_t
    colheita["perda_perc"] = perda_perc
    colheita["perda_rs"] = perda_rs
    colheita["classificacao"] = classificar_perda(
        perda_perc, colheita["tipo_colheita"], CONFIG["limites_perda_percentual"])
    return colheita


def ler_dados_colhedora(colheita: dict) -> None:
    """Procedimento: preenche (ou limpa) os campos que só existem na mecanizada."""
    if colheita["tipo_colheita"] == "MECANIZADA":
        colheita["colhedora"] = ler_texto("  Identificação da colhedora (ex.: CH-01): ", 30)
        colheita["velocidade_kmh"] = ler_float("  Velocidade média de colheita (km/h): ", 0.5, 15)
        colheita["altura_corte_cm"] = ler_float("  Altura média de corte (cm): ", 0, 30)
    else:
        colheita["colhedora"] = None
        colheita["velocidade_kmh"] = None
        colheita["altura_corte_cm"] = None


def ler_toneladas_colhidas(colheita: dict) -> float:
    """Limita o colhido a 150% do esperado, para pegar erro de digitação."""
    esperado = calcular_producao_esperada(colheita["area_ha"], colheita["prod_estimada_t_ha"])
    print(f"  (Produção esperada para este talhão: {formatar_numero(esperado)} t)")
    return ler_float("  Toneladas efetivamente colhidas: ", 0, round(esperado * 1.5, 2))


def buscar_por_id(id_colheita: int):
    """Procura a colheita na tabela de memória. Devolve (índice, dicionário) ou (None, None)."""
    for indice, c in enumerate(COLHEITAS):
        if c["id_colheita"] == id_colheita:
            return indice, c
    return None, None


def pedir_id_existente(acao: str):
    """Mostra a lista, pede um ID e garante que ele exista."""
    if not COLHEITAS:
        print("\n  Nenhuma colheita registrada ainda.")
        return None
    exibir_tabela(COLHEITAS)
    maior_id = max(c["id_colheita"] for c in COLHEITAS)
    id_escolhido = ler_inteiro(f"\n  Informe o ID da colheita que deseja {acao} (0 = voltar): ",
                               0, maior_id)
    if id_escolhido == 0:
        return None
    _, colheita = buscar_por_id(id_escolhido)
    if colheita is None:
        print(f"  ⚠ Não existe colheita com ID {id_escolhido}.")
    return colheita


def chave_colheita(colheita: dict) -> tuple:
    """Tupla que identifica uma colheita, usada para evitar duplicidade na importação."""
    return (colheita["talhao"], colheita["data_colheita"], colheita["tipo_colheita"],
            colheita["area_ha"], colheita["toneladas_colhidas"])


def proximo_id_offline() -> int:
    return max((c["id_colheita"] for c in COLHEITAS), default=0) + 1


def salvar_offline() -> None:
    """No modo offline, o JSON faz o papel do banco."""
    if CONEXAO is None:
        arquivos.exportar_json(COLHEITAS, arquivos.CAMINHO_OFFLINE)


# ----------------------------------------------------------------------------
# Opções do menu
# ----------------------------------------------------------------------------
def registrar_colheita() -> None:
    exibir_cabecalho("Registrar nova colheita")
    colheita = {}
    colheita["talhao"] = ler_texto("  Talhão (ex.: T-12): ", 30)
    colheita["data_colheita"] = ler_data("  Data da colheita DD/MM/AAAA (ENTER = hoje): ")
    print("  Tipo de colheita:")
    colheita["tipo_colheita"] = ler_opcao("  Escolha: ", TIPOS_COLHEITA)
    ler_dados_colhedora(colheita)
    colheita["area_ha"] = ler_float("  Área colhida (ha): ", 0.1, 10000)
    colheita["prod_estimada_t_ha"] = ler_float("  Produtividade estimada (t/ha): ", 1, 250)
    colheita["toneladas_colhidas"] = ler_toneladas_colhidas(colheita)
    recalcular(colheita)

    if CONEXAO:
        colheita["id_colheita"] = banco.inserir_colheita(CONEXAO, colheita)
    else:
        colheita["id_colheita"] = proximo_id_offline()
    COLHEITAS.append(colheita)
    salvar_offline()
    arquivos.registrar_log(f"Colheita #{colheita['id_colheita']} registrada "
                           f"(talhão {colheita['talhao']}, perda {colheita['perda_perc']}%).")
    print("\n  ✔ Colheita registrada com sucesso!")
    exibir_detalhes(colheita)


def listar_colheitas() -> None:
    exibir_cabecalho("Colheitas registradas")
    if not COLHEITAS:
        print("\n  Nenhuma colheita registrada ainda.")
        return
    print("  Filtrar por:")
    filtro = ler_opcao("  Escolha: ", ("TODAS",) + TIPOS_COLHEITA)
    selecionadas = COLHEITAS if filtro == "TODAS" else \
        [c for c in COLHEITAS if c["tipo_colheita"] == filtro]
    if not selecionadas:
        print(f"\n  Nenhuma colheita do tipo {filtro}.")
        return
    exibir_tabela(selecionadas)
    print(f"  {len(selecionadas)} registro(s).  🟢 aceitável  🟡 atenção  🔴 crítica")


def detalhar_colheita() -> None:
    exibir_cabecalho("Detalhes e recomendações")
    colheita = pedir_id_existente("consultar")
    if colheita:
        exibir_detalhes(colheita)


def alterar_colheita() -> None:
    exibir_cabecalho("Alterar colheita")
    original = pedir_id_existente("alterar")
    if not original:
        return
    colheita = dict(original)  # trabalha numa cópia; só grava se confirmar
    print("\n  Qual campo deseja alterar?")
    campo = ler_opcao("  Escolha: ", CAMPOS_EDITAVEIS)

    if campo == CAMPOS_EDITAVEIS[0]:
        colheita["talhao"] = ler_texto("  Novo talhão: ", 30)
    elif campo == CAMPOS_EDITAVEIS[1]:
        colheita["data_colheita"] = ler_data("  Nova data DD/MM/AAAA (ENTER = hoje): ")
    elif campo == CAMPOS_EDITAVEIS[2]:
        print("  Novo tipo:")
        colheita["tipo_colheita"] = ler_opcao("  Escolha: ", TIPOS_COLHEITA)
        ler_dados_colhedora(colheita)
    elif campo == CAMPOS_EDITAVEIS[3]:
        colheita["area_ha"] = ler_float("  Nova área (ha): ", 0.1, 10000)
        colheita["toneladas_colhidas"] = ler_toneladas_colhidas(colheita)
    elif campo == CAMPOS_EDITAVEIS[4]:
        colheita["prod_estimada_t_ha"] = ler_float("  Nova produtividade estimada (t/ha): ", 1, 250)
        colheita["toneladas_colhidas"] = ler_toneladas_colhidas(colheita)
    elif campo == CAMPOS_EDITAVEIS[5]:
        colheita["toneladas_colhidas"] = ler_toneladas_colhidas(colheita)
    else:
        if colheita["tipo_colheita"] != "MECANIZADA":
            print("  ⚠ Esta colheita é MANUAL e não tem dados de colhedora.")
            return
        ler_dados_colhedora(colheita)

    recalcular(colheita)
    if not confirmar("\n  Confirma a alteração?"):
        print("  Alteração cancelada.")
        return
    if CONEXAO:
        banco.atualizar_colheita(CONEXAO, colheita["id_colheita"], colheita)
    indice, _ = buscar_por_id(colheita["id_colheita"])
    COLHEITAS[indice] = colheita
    salvar_offline()
    arquivos.registrar_log(f"Colheita #{colheita['id_colheita']} alterada (campo: {campo}).")
    print("\n  ✔ Colheita atualizada.")
    exibir_detalhes(colheita)


def excluir_colheita() -> None:
    exibir_cabecalho("Excluir colheita")
    colheita = pedir_id_existente("excluir")
    if not colheita:
        return
    if not confirmar(f"\n  Excluir a colheita #{colheita['id_colheita']} "
                     f"(talhão {colheita['talhao']})? Essa ação não pode ser desfeita."):
        print("  Exclusão cancelada.")
        return
    if CONEXAO:
        banco.excluir_colheita(CONEXAO, colheita["id_colheita"])
    COLHEITAS.remove(colheita)
    salvar_offline()
    arquivos.registrar_log(f"Colheita #{colheita['id_colheita']} excluída.")
    print("  ✔ Colheita excluída.")


def exibir_painel() -> None:
    exibir_cabecalho("Painel de indicadores")
    if not COLHEITAS:
        print("\n  Nenhuma colheita registrada ainda.")
        return
    r = resumo_geral(COLHEITAS)
    print(f"\n  Colheitas registradas ....: {r['qtd_colheitas']}")
    print(f"  Área total colhida .......: {formatar_numero(r['area_total_ha'])} ha")
    print(f"  Toneladas colhidas .......: {formatar_numero(r['toneladas_colhidas'])} t")
    print(f"  Perda total ..............: {formatar_numero(r['perda_total_t'])} t")
    print(f"  Perda média ponderada ....: {formatar_numero(r['perda_media_perc'])} %")
    print(f"  💰 Prejuízo estimado .....: {formatar_moeda(r['perda_total_rs'])}")

    print("\n  Perda média por tipo de colheita:")
    for tipo, media in r["por_tipo"].items():
        barra = "█" * min(int(round(media)), 40)
        print(f"    {tipo:<11} {formatar_numero(media):>6} %  {barra}")

    print("\n  Situação das colheitas:")
    for classe, qtd in r["por_classificacao"].items():
        print(f"    {arquivos.icone(classe)} {classe:<10} {qtd}")

    ranking = ranking_colhedoras(COLHEITAS)
    if ranking:
        print("\n  🏆 Ranking de colhedoras (menor perda primeiro):")
        print(f"    {'POS':<4} {'COLHEDORA':<12} {'COLHEITAS':>9} {'PERDA MÉDIA':>12} {'PREJUÍZO':>15}")
        for pos, (nome, qtd, media, total) in enumerate(ranking, start=1):
            print(f"    {str(pos) + 'º':<4} {nome:<12} {qtd:>9} "
                  f"{formatar_numero(media) + ' %':>12} {formatar_moeda(total):>15}")
        pior = ranking[-1]
        if len(ranking) > 1 and pior[2] > ranking[0][2]:
            print(f"\n  💡 A colhedora {pior[0]} perde, em média, "
                  f"{formatar_numero(pior[2] - ranking[0][2])} pontos percentuais a mais que "
                  f"a {ranking[0][0]}. Vale revisar a regulagem e o operador dela.")


def exportar_backup() -> None:
    exibir_cabecalho("Exportar backup JSON")
    if not COLHEITAS:
        print("\n  Nada para exportar.")
        return
    caminho = arquivos.exportar_json(COLHEITAS)
    arquivos.registrar_log(f"Backup JSON exportado com {len(COLHEITAS)} registro(s).")
    print(f"\n  ✔ {len(COLHEITAS)} colheita(s) exportada(s) para:\n    {caminho}")


def importar_backup() -> None:
    exibir_cabecalho("Importar backup JSON")
    try:
        importadas = arquivos.importar_json()
    except FileNotFoundError:
        print(f"\n  ⚠ Arquivo não encontrado: {arquivos.CAMINHO_BACKUP}")
        return
    except ValueError:
        print("\n  ⚠ O arquivo de backup está corrompido (JSON inválido).")
        return
    if not importadas:
        print("\n  O backup não tem colheitas válidas.")
        return

    existentes = {chave_colheita(c) for c in COLHEITAS}
    novas = [c for c in importadas if chave_colheita(c) not in existentes]
    repetidas = len(importadas) - len(novas)
    print(f"\n  {len(importadas)} colheita(s) no backup: {len(novas)} nova(s), "
          f"{repetidas} já registrada(s) (serão ignoradas).")
    if not novas:
        print("  Nada novo para importar.")
        return
    importadas = novas
    if not confirmar("  Adicioná-las aos registros atuais?"):
        print("  Importação cancelada.")
        return
    for colheita in importadas:
        recalcular(colheita)  # garante consistência com os parâmetros atuais
        if CONEXAO:
            colheita["id_colheita"] = banco.inserir_colheita(CONEXAO, colheita)
        else:
            colheita["id_colheita"] = proximo_id_offline()
        COLHEITAS.append(colheita)
    salvar_offline()
    arquivos.registrar_log(f"{len(importadas)} colheita(s) importada(s) do backup JSON.")
    print(f"  ✔ {len(importadas)} colheita(s) importada(s).")


def gerar_relatorio() -> None:
    exibir_cabecalho("Gerar relatório TXT")
    if not COLHEITAS:
        print("\n  Nada para relatar.")
        return
    caminho = arquivos.gerar_relatorio_txt(
        COLHEITAS, CONFIG["parametros_economicos"]["preco_tonelada_cana_rs"])
    arquivos.registrar_log("Relatório TXT gerado.")
    print(f"\n  ✔ Relatório gerado em:\n    {caminho}")


# Dicionário que liga cada opção do menu à função correspondente
ACOES = {
    "1": registrar_colheita,
    "2": listar_colheitas,
    "3": detalhar_colheita,
    "4": alterar_colheita,
    "5": excluir_colheita,
    "6": exibir_painel,
    "7": exportar_backup,
    "8": importar_backup,
    "9": gerar_relatorio,
}


# ----------------------------------------------------------------------------
# Inicialização
# ----------------------------------------------------------------------------
def inicializar() -> None:
    global CONFIG, CONEXAO, COLHEITAS
    CONFIG = arquivos.carregar_config()
    exibir_cabecalho(CONFIG["sistema"]["nome"])
    print("  Conectando ao Oracle FIAP...")
    CONEXAO = banco.conectar(CONFIG["oracle"])

    if CONEXAO:
        banco.criar_tabela_se_nao_existir(CONEXAO)
        COLHEITAS = banco.listar_colheitas(CONEXAO)
        print(f"  ✔ Conectado. {len(COLHEITAS)} colheita(s) carregada(s) do banco.")
        arquivos.registrar_log("Sistema iniciado conectado ao Oracle.")
    else:
        if not confirmar("  Deseja continuar em modo offline (dados em JSON)?"):
            sys.exit(0)
        try:
            COLHEITAS = arquivos.importar_json(arquivos.CAMINHO_OFFLINE)
        except (FileNotFoundError, ValueError):
            COLHEITAS = []
        print(f"  Modo offline: {len(COLHEITAS)} colheita(s) carregada(s) do JSON.")
        arquivos.registrar_log("Sistema iniciado em modo offline.")


def main() -> None:
    inicializar()
    while True:
        exibir_menu()
        opcao = input("  Escolha uma opção: ").strip()
        if opcao == "0":
            break
        acao = ACOES.get(opcao)
        if acao is None:
            print("  ⚠ Opção inválida. Digite um número de 0 a 9.")
            continue
        try:
            acao()
        except Exception as erro:  # o programa não pode cair por um erro pontual
            print(f"\n  ✖ Ocorreu um erro: {erro}")
            arquivos.registrar_log(f"ERRO na opção {opcao}: {erro}")
        pausar()

    if CONEXAO:
        CONEXAO.close()
    arquivos.registrar_log("Sistema encerrado.")
    print("\n  Até a próxima colheita! 🌾\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Programa encerrado pelo usuário.")

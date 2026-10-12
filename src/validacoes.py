"""
Módulo de validação de entradas do usuário.

Todas as leituras do teclado passam por aqui, garantindo que nenhum dado de
tipo ou faixa inválida chegue aos cálculos ou ao banco de dados Oracle.
Cada função repete a pergunta até o usuário informar um valor válido.
"""

from datetime import date, datetime


def ler_texto(mensagem: str, tamanho_max: int = 30, obrigatorio: bool = True) -> str:
    """Lê um texto não vazio (se obrigatório) e com tamanho máximo controlado."""
    while True:
        valor = input(mensagem).strip()
        if not valor and not obrigatorio:
            return ""
        if not valor:
            print("  ⚠ Campo obrigatório. Digite um valor.")
        elif len(valor) > tamanho_max:
            print(f"  ⚠ Máximo de {tamanho_max} caracteres (você digitou {len(valor)}).")
        else:
            return valor.upper()


def ler_float(mensagem: str, minimo: float, maximo: float) -> float:
    """Lê um número decimal dentro da faixa [minimo, maximo]. Aceita vírgula ou ponto."""
    while True:
        bruto = input(mensagem).strip().replace(",", ".")
        try:
            valor = float(bruto)
        except ValueError:
            print("  ⚠ Valor inválido. Digite apenas números (ex.: 12,5).")
            continue
        if valor < minimo or valor > maximo:
            print(f"  ⚠ O valor deve estar entre {formatar_numero(minimo)} e {formatar_numero(maximo)}.")
            continue
        return round(valor, 2)


def ler_inteiro(mensagem: str, minimo: int, maximo: int) -> int:
    """Lê um número inteiro dentro da faixa [minimo, maximo]."""
    while True:
        bruto = input(mensagem).strip()
        if not bruto.lstrip("-").isdigit():
            print("  ⚠ Digite um número inteiro.")
            continue
        valor = int(bruto)
        if valor < minimo or valor > maximo:
            print(f"  ⚠ O valor deve estar entre {minimo} e {maximo}.")
            continue
        return valor


def ler_data(mensagem: str) -> date:
    """Lê uma data no formato DD/MM/AAAA, sem permitir datas futuras."""
    while True:
        bruto = input(mensagem).strip()
        if bruto == "":
            return date.today()
        try:
            valor = datetime.strptime(bruto, "%d/%m/%Y").date()
        except ValueError:
            print("  ⚠ Data inválida. Use o formato DD/MM/AAAA (ex.: 05/10/2026).")
            continue
        if valor > date.today():
            print("  ⚠ A data da colheita não pode estar no futuro.")
            continue
        return valor


def ler_opcao(mensagem: str, opcoes: tuple) -> str:
    """Mostra opções numeradas (vindas de uma tupla) e devolve a escolhida."""
    for indice, opcao in enumerate(opcoes, start=1):
        print(f"    {indice} - {opcao}")
    escolha = ler_inteiro(mensagem, 1, len(opcoes))
    return opcoes[escolha - 1]


def confirmar(mensagem: str) -> bool:
    """Pergunta S/N e só aceita essas respostas."""
    while True:
        resposta = input(f"{mensagem} (S/N): ").strip().upper()
        if resposta in ("S", "N"):
            return resposta == "S"
        print("  ⚠ Responda apenas S ou N.")


def formatar_numero(valor: float, casas: int = 2) -> str:
    """Formata número no padrão brasileiro: 1.234,56"""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda(valor: float) -> str:
    """Formata valor em reais: R$ 1.234,56"""
    return f"R$ {formatar_numero(valor)}"

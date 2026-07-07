"""
Eu organizei este módulo como a camada de apoio técnico da aplicação.

Aqui ficam concentradas as constantes, estruturas de dados e funções auxiliares usadas por outras partes do projeto.
Essa separação é importante porque evita repetição de regra em vários arquivos, facilita manutenção e deixa a aplicação
mais estável quando novos relatórios, modelos de planilha ou regras visuais precisam ser adicionados.

Na versão pública do projeto, este arquivo também ajuda a demonstrar a arquitetura da solução sem expor informações reais
do ambiente de trabalho. Os nomes, códigos e categorias usados como referência são genéricos, mas preservam a lógica
necessária para entender como a automação trata datas, variações, tabelas e classificações.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd


# Fui centralizando os caminhos principais do projeto para evitar referências espalhadas pela aplicação.
# Isso torna mais simples trocar templates, imagens e estrutura de pastas sem precisar alterar a lógica de geração.
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMPLATE_PATH = os.path.join(_BASE_DIR, "templates", "template_exemplo.docx")
_LOGO_PATH = os.path.join(_BASE_DIR, "img", "logo.png")


# Tive que manter os nomes dos meses em dicionários reutilizáveis porque os relatórios dependem de referências mensais.
# Essa padronização evita divergência entre textos, tabelas, gráficos e nomes de arquivos gerados automaticamente.
NOMES_MESES = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

NOMES_MESES_CAP = {k: v.capitalize() for k, v in NOMES_MESES.items()}

MESES_ABV = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


# Defini uma régua visual para classificar variações percentuais de forma consistente.
# Ajuda o relatório a destacar automaticamente mudanças relevantes, sem depender de avaliação manual a cada execução.
COR_VARIACOES = {
    "ate_5": "#FFFFFF",
    "5_a_10": "#B4C6E7",
    "10_a_20": "#F7CAAC",
    "acima_20": "#FF0000",
}


# Coloquei categorias representativas como massa de exemplo para demonstrar a geração de gráficos sem usar dados reais.
# Essa abordagem permite publicar o projeto preservando a lógica da aplicação e protegendo informações sensíveis.
CATEGORIAS_REPRESENTATIVAS = [
    ("CAT001", "Auxiliar de serviços gerais"),
    ("CAT002", "Técnico de manutenção"),
    ("CAT003", "Operador de equipamentos"),
    ("CAT004", "Engenheiro pleno"),
]

CORES_GRAFICOS = ["#D6A800", "#4F81BD", "#6AA84F", "#B07AA1"]


# Concentrei os padrões de validação e a estrutura esperada das tabelas para deixar o processamento mais previsível.
# Isso reduz erro de leitura em planilhas diferentes e facilita conferir se os dados chegaram no formato correto.
_PADRAO_CODIGO = re.compile(r"^[A-Z]{1,3}\d{3,6}$")

_COLUNAS_MDO = [
    "codigo",
    "categoria",
    "unidade",
    "salario",
    "pct_encargo_social",
    "rs_encargo_social",
    "pct_alimentacao",
    "rs_alimentacao",
    "pct_transporte",
    "rs_transporte",
    "pct_epi",
    "rs_epi",
    "pct_encargo_total",
    "rs_encargo_total",
    "valor_total",
]


# Eu usei dataclasses para representar os principais resultados intermediários da leitura das planilhas.
# Deixa claro quais dados cada etapa entrega e facilita a integração entre leitores, gráficos e gerador de relatório.
@dataclass
class ResultadoVariacoes:
    """Resultado estruturado da leitura do relatório de variações."""

    categorias: pd.DataFrame
    datas_referencia: list[pd.Timestamp]
    referencia_atual: pd.Timestamp
    referencia_anterior: pd.Timestamp


@dataclass
class ResultadoMDO:
    """Resultado estruturado da leitura das informações de mão de obra."""

    dados: pd.DataFrame
    tipo: str


# Criei funções auxiliares pequenas para isolar regras recorrentes de tratamento.
# Melhora a legibilidade e evita que cálculos de cor, data e valores nulos fiquem duplicados em outros módulos.
def _is_nan(valor: object) -> bool:
    if valor is None:
        return True

    try:
        return np.isnan(float(valor))
    except (TypeError, ValueError):
        return False


def _cor_variacao(valor: object) -> str:
    if _is_nan(valor):
        return COR_VARIACOES["ate_5"]

    variacao = abs(float(valor))

    if variacao > 20:
        return COR_VARIACOES["acima_20"]
    if variacao > 10:
        return COR_VARIACOES["10_a_20"]
    if variacao > 5:
        return COR_VARIACOES["5_a_10"]

    return COR_VARIACOES["ate_5"]


def label_referencia(data: pd.Timestamp) -> str:
    mes = NOMES_MESES.get(data.month, str(data.month))
    return f"{mes}/{data.year}"


def label_referencia_barra(data: pd.Timestamp) -> str:
    return f"{data.month:02d}/{data.year}"

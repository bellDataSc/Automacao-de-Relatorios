# Nesse módulo eu organizei como a camada para geração visual da aplicação.

# Coloquei aqui, os dados já tratados são transformados em gráficos de série histórica, prontos para serem inseridos no relatório Word. 
# Considerei importante porque reduz análise manual, padroniza a leitura visual das variações e permite que o
# relatório técnico seja gerado com gráficos consistentes a cada execução.

# Como essa é uma versão pública do meu projeto no tarbalho, os gráficos são produzidos a partir de categorias representativas e dados demonstrativos.
# Assim, a aplicação comunica a capacidade técnica da automação sem expor informações reais do projeto.

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from template.utils import (
    CATEGORIAS_REPRESENTATIVAS,
    CORES_GRAFICOS,
    ResultadoVariacoes,
    _is_nan,
)


def _extrair_serie_historica(
    linha: pd.Series,
    colunas_disponiveis: pd.Index,
    datas: list[pd.Timestamp],
) -> tuple[list[pd.Timestamp], list[float]]:
  
# Deixei apenas extração da série histórica para separar regra de dado e regra de visualização.
# Referências mensais disponíveis, ignora valores vazios e retorna apenas os pontos válidos.
# Para evitar que o gráfico seja gerado com ruído de planilha, datas ausentes ou registros incompletos.
  
    datas_validas = []
    valores = []

    for data in datas:
        if data not in colunas_disponiveis:
            continue

        valor = linha.get(data)

        if _is_nan(valor):
            continue

        datas_validas.append(data)
        valores.append(float(valor))

    return datas_validas, valores


def _formatar_eixo_temporal(ax: plt.Axes) -> None:
  
# Formatei o eixo temporal para manter os gráficos visualmente padronizados.
# Como os relatórios trabalham com referências mensais, o eixo de datas precisa ser legível, 
# compacto e adequado para inserção em documento Word.
 
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.tick_params(axis="both", labelsize=7)


def _aplicar_layout_tecnico(ax: plt.Axes) -> None:

# Eu preferi um layout visual mais limpo para relatórios técnicos.
# A remoção de bordas desnecessárias, o uso de grade leve e a padronização dos rótulos ajudam o gráfico a comunicar
# tendência histórica sem poluir o documento final.
  
    ax.set_ylabel("R$/unidade", fontsize=8)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _gerar_grafico_categoria(
    df: pd.DataFrame,
    codigo: str,
    nome: str,
    datas: list[pd.Timestamp],
    cor: str,
) -> io.BytesIO | None:

# Aqui a gente gera o gráfico individual de uma categoria representativa.
# A ideia para essa função foi localizar o código da categoria, extrai sua série histórica e monta um gráfico em memória. 
# Esse formato em BytesIO é útil porque permite inserir a imagem diretamente no documento Word sem salvar arquivos temporários.

    if df.empty or "codigo" not in df.columns:
        return None

    registro = df[df["codigo"] == codigo]

    if registro.empty:
        return None

    linha = registro.iloc[0]
    datas_validas, valores = _extrair_serie_historica(
        linha=linha,
        colunas_disponiveis=df.columns,
        datas=datas,
    )

    if len(valores) < 2:
        return None

    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)

    ax.plot(
        datas_validas,
        valores,
        color=cor,
        linewidth=2,
        marker="o",
        markersize=4,
    )

    ax.fill_between(
        datas_validas,
        valores,
        alpha=0.08,
        color=cor,
    )

    ax.set_title(
        f"{codigo} - {nome}",
        fontsize=10,
        fontweight="bold",
        pad=10,
    )

    _formatar_eixo_temporal(ax)
    _aplicar_layout_tecnico(ax)

    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)

    buffer.seek(0)

    return buffer


def gerar_graficos_representativas(
    resultado: ResultadoVariacoes,
) -> list[io.BytesIO]:

# Gráficos das categorias representativas do relatório.
# Aqui a gente tem uma função que percorre uma lista controlada de categorias públicas/demonstrativas, aplica a paleta visual definida
# no projeto e retorna apenas os gráficos que possuem dados suficientes. 
# Eu consigo manter o relatório enxuto e evita imagens vazias no documento final.

if resultado is None or resultado.categorias.empty:
        return []

    graficos = []
    datas = resultado.datas_referencia

    for indice, categoria in enumerate(CATEGORIAS_REPRESENTATIVAS):
        codigo, nome = categoria
        cor = CORES_GRAFICOS[indice % len(CORES_GRAFICOS)]

        grafico = _gerar_grafico_categoria(
            df=resultado.categorias,
            codigo=codigo,
            nome=nome,
            datas=datas,
            cor=cor,
        )

        if grafico is not None:
            graficos.append(grafico)

    return graficos

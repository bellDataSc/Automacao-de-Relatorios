# Organizei este módulo como a camada de leitura e normalização das planilhas da aplicação.

# A função deste arquivo é transformar arquivos Excel em estruturas padronizadas, prontas para alimentar gráficos,
# Tabelas e relatórios técnicos. Essa etapa é importante porque as planilhas de origem podem variar em nomes de colunas,
# Formatação e quantidade de referências mensais, mas a aplicação precisa receber os dados em um formato previsível.

# Na versão pública do projeto, este módulo demonstra a arquitetura de ingestão sem expor bases reais. 
# A lógica preserva o que é relevante tecnicamente: leitura de arquivos, detecção de datas, padronização 
# de campos e separação entre tipos de relatório.


from __future__ import annotations

import unicodedata
from datetime import datetime

import pandas as pd

from template.utils import ResultadoMDO, ResultadoVariacoes, _COLUNAS_MDO


def _texto_normalizado(valor: object) -> str:

# No futuro, para outros projetos, eu posso usar esta função para comparar nomes de colunas de forma mais segura.
# A normalização remove diferenças de acento, caixa e espaçamento. 
# Isso torna a leitura mais resistente a pequenas variações entre planilhas, como "Código", "codigo", "Descrição" ou "descricao".
  

    texto = str(valor).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))

    return texto


def _ler_primeira_aba(path: str, header: int = 1) -> pd.DataFrame:
# Centralizei a leitura da primeira aba para manter o comportamento dos leitores consistente.
# A aplicação trabalha com arquivos Excel estruturados, e esta função garante que os nomes das colunas sejam limpos 
# logo na entrada, sem alterar colunas que representam datas. Isso preserva a série histórica usada nos relatórios.


    df = pd.read_excel(path, sheet_name=0, header=header)
    df.columns = [coluna.strip() if isinstance(coluna, str) else coluna for coluna in df.columns]

    return df


def _detectar_colunas_data(df: pd.DataFrame) -> list[pd.Timestamp]:
# Isolei a detecção de datas porque as referências mensais são uma parte central do relatório.
# Essa função identifica colunas que representam períodos históricos e as ordena cronologicamente. Com isso,
# a aplicação consegue localizar automaticamente a referência atual e a referência anterior.

    colunas_data = []

    for coluna in df.columns:
        if isinstance(coluna, (datetime, pd.Timestamp)):
            colunas_data.append(pd.Timestamp(coluna))

    return sorted(colunas_data)


def _definir_referencias(colunas_data: list[pd.Timestamp]) -> tuple[pd.Timestamp, pd.Timestamp]:
# Defini uma regra de segurança para quando a planilha não traz série histórica suficiente.
# Quando existem ao menos duas datas, a aplicação usa as duas referências mais recentes. Quando isso não acontece,
# o sistema assume o mês corrente e o mês anterior para manter o fluxo de geração funcionando em bases de exemplo.

    if len(colunas_data) < 2:
        referencia_atual = pd.Timestamp(datetime.now().replace(day=1))
        referencia_anterior = referencia_atual - pd.DateOffset(months=1)

        return referencia_atual, referencia_anterior

    return colunas_data[-1], colunas_data[-2]


def _normalizar_colunas_variacoes(df: pd.DataFrame) -> pd.DataFrame:
# Aqui a regra de padronização das colunas do relatório de variações.
# Permite que o restante da aplicação trabalhe com nomes técnicos estáveis, mesmo quando o arquivo de entrada usa pequenas diferenças de nomenclatura.


    rename_map = {}

    for coluna in df.columns:
        coluna_normalizada = _texto_normalizado(coluna)

        if "codigo" in coluna_normalizada:
            rename_map[coluna] = "codigo"
        elif "descri" in coluna_normalizada:
            rename_map[coluna] = "descricao"
        elif "unidade" in coluna_normalizada:
            rename_map[coluna] = "unidade"
        elif "segmento" in coluna_normalizada:
            rename_map[coluna] = "segmento"
        elif "anterior" in coluna_normalizada and "preco" in coluna_normalizada:
            rename_map[coluna] = "preco_anterior"
        elif "atual" in coluna_normalizada and "preco" in coluna_normalizada:
            rename_map[coluna] = "preco_atual"
        elif "variacao" in coluna_normalizada:
            rename_map[coluna] = "variacao_decimal"

    return df.rename(columns=rename_map)


def _normalizar_colunas_mdo(df: pd.DataFrame) -> pd.DataFrame:
# Regra de padronização das colunas de mão de obra.
# A ideia é transformar diferentes nomenclaturas de planilhas em uma estrutura única. 
# Isso é importante porque os módulos seguintes não precisam conhecer a origem do arquivo, apenas consumir campos padronizados.


    rename_map = {}

    for coluna in df.columns:
        coluna_normalizada = _texto_normalizado(coluna)
        coluna_tecnica = coluna_normalizada.replace(" ", "_")

        if coluna_tecnica in _COLUNAS_MDO:
            rename_map[coluna] = coluna_tecnica
        elif "codigo" in coluna_normalizada:
            rename_map[coluna] = "codigo"
        elif "categoria" in coluna_normalizada or "descri" in coluna_normalizada:
            rename_map[coluna] = "categoria"
        elif "unidade" in coluna_normalizada:
            rename_map[coluna] = "unidade"
        elif "salario" in coluna_normalizada:
            rename_map[coluna] = "salario"
        elif "valor_total" in coluna_tecnica or "valor total" in coluna_normalizada:
            rename_map[coluna] = "valor_total"

    return df.rename(columns=rename_map)


def _filtrar_linhas_com_codigo(df: pd.DataFrame) -> pd.DataFrame:
# Eu uso esta função para manter apenas linhas efetivas de dados.
# Em relatórios técnicos extraídos de planilhas, é comum haver cabeçalhos intermediários, linhas vazias ou observações. 
  Filtrar pelo código ajuda a separar registros válidos de conteúdo meramente estrutural.


    if "codigo" not in df.columns:
        return df.copy()

    df = df[df["codigo"].notna()].copy()
    df["codigo"] = df["codigo"].astype(str).str.strip()

    return df


def _garantir_colunas_mdo(df: pd.DataFrame) -> pd.DataFrame:
# Garanto a estrutura mínima esperada para os dados de mão de obra.
# Etapa reduz risco de erro na geração do relatório, porque as colunas principais passam a existir mesmo quando
# uma planilha de demonstração não possui todos os campos usados em um cenário completo.
  
    for coluna in _COLUNAS_MDO:
        if coluna not in df.columns:
            df[coluna] = pd.NA

    colunas_extras = [coluna for coluna in df.columns if coluna not in _COLUNAS_MDO]

    return df[_COLUNAS_MDO + colunas_extras]


def ler_variacoes(path: str) -> ResultadoVariacoes:
# Leio o relatório de variações e preparo as informações necessárias para análise temporal.
# Função identifica as referências mensais, normaliza os campos principais e retorna um objeto estruturado.
# Com isso, a aplicação consegue usar o mesmo resultado para tabelas, gráficos e textos narrativos do relatório.

    df = _ler_primeira_aba(path)
    colunas_data = _detectar_colunas_data(df)
    referencia_atual, referencia_anterior = _definir_referencias(colunas_data)

    df = _normalizar_colunas_variacoes(df)
    df = _filtrar_linhas_com_codigo(df)

    return ResultadoVariacoes(
        categorias=df,
        datas_referencia=colunas_data,
        referencia_atual=referencia_atual,
        referencia_anterior=referencia_anterior,
    )


def _ler_mdo(path: str, tipo: str) -> ResultadoMDO:
# Usei aqui como leitor base para os diferentes tipos de mão de obra.
# A lógica de leitura é a mesma para arquivos onerados, desonerados e de consultoria. Por isso, mantive uma função
# interna reutilizável e deixei as funções públicas apenas com a responsabilidade de indicar o tipo de planilha.

    df = _ler_primeira_aba(path)
    df = _normalizar_colunas_mdo(df)
    df = _filtrar_linhas_com_codigo(df)
    df = _garantir_colunas_mdo(df)

    return ResultadoMDO(dados=df, tipo=tipo)


def ler_mdo_onerada(path: str) -> ResultadoMDO:
# Leio a planilha de mão de obra onerada.
# Esta entrada representa uma das variações de cálculo usadas pelo relatório e segue a mesma estrutura técnica
# padronizada pelo leitor base.

    return _ler_mdo(path, tipo="onerada")


def ler_mdo_desonerada(path: str) -> ResultadoMDO:
# Planilha de mão de obra desonerada.
# Separar esta função deixa explícito no código que a aplicação trata cenários distintos de composição de custos,
# mesmo quando a estrutura de leitura é reaproveitada.

    return _ler_mdo(path, tipo="desonerada")


def ler_mdo_consultoria(path: str) -> ResultadoMDO:
# Planilha de mão de obra de consultoria.
# Função mantém a mesma interface dos demais leitores e permite que o relatório combine diferentes naturezas
# de informação sem misturar regras de origem no restante da aplicação.


    return _ler_mdo(path, tipo="consultoria")

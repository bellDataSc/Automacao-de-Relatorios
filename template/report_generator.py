# Organizei esse módulo como um bloco central de orquestração da aplicação.
# Deixei que aqui fosse possivel conectar todas as etapas necessárias para transformar planilhas estruturadas em um relatório técnico consolidado:
# - recebimento dos arquivos, leitura e normalização dos dados, combinação das bases de mão de obra, cálculo de variações,
# - preparação do contexto, geração de textos por IA, criação de gráficos e renderização do documento Word.

# Também concentrei neste arquivo a interface construída em Streamlit. Essa organização permite manter a experiência do
# usuário conectada ao fluxo de processamento sem transferir regras específicas de leitura, visualização ou geração
# narrativa para a camada de interface.

# Como essa é uma versão pública do meu projeto do trabalho, os arquivos, categorias e documentos utilizados são demonstrativos. 
# A arquitetura preserva o funcionamento técnico da solução sem disponibilizar dados, modelos documentais ou informações reais que eu uso no dia a dia.


from __future__ import annotations

import os
import shutil
import tempfile
import traceback
from datetime import datetime

import pandas as pd
import streamlit as st

from template.charts import gerar_graficos_representativas
from template.data_readers import (
    ler_mdo_consultoria,
    ler_mdo_desonerada,
    ler_mdo_onerada,
    ler_variacoes,
)
from template.text_generator import gerar_texto_completo
from template.utils import (
    CATEGORIAS_REPRESENTATIVAS,
    MESES_ABV,
    NOMES_MESES,
    ResultadoMDO,
    ResultadoVariacoes,
    _LOGO_PATH,
    _TEMPLATE_PATH,
    _cor_variacao,
    _is_nan,
    label_referencia,
    label_referencia_barra,
)


def _salvar(
    uploaded_file,
    temp_dir: str,
    prefixo: str,
) -> str:
  
# Salvo temporariamente cada arquivo recebido pela interface para permitir seu processamento pelos módulos internos.
# Mantém os uploads isolados durante a execução e evita criar arquivos permanentes no ambiente da aplicação.
# O nome original não é reutilizado diretamente, o que ajuda a manter uma estrutura previsível para o processamento.

    extensao = os.path.splitext(uploaded_file.name)[1]
    path = os.path.join(temp_dir, f"{prefixo}{extensao}")

    with open(path, "wb") as arquivo:
        arquivo.write(uploaded_file.getbuffer())

    return path


def _detectar_referencia(
    uploaded_file,
) -> tuple[pd.Timestamp, pd.Timestamp] | None:
  
# Detecto automaticamente as referências temporais presentes no relatório de variações.
# A identificação antecipada permite preencher informações da interface sem exigir digitação manual. 
# Para preservar o arquivo recebido, a leitura é feita em um diretório temporário removido após o processamento.


    temp_dir = tempfile.mkdtemp(prefix="detect_ref_")

    try:
        temp_path = os.path.join(temp_dir, "variacoes.xlsx")

        with open(temp_path, "wb") as arquivo:
            arquivo.write(uploaded_file.getbuffer())

        uploaded_file.seek(0)

        resultado = ler_variacoes(temp_path)

        return (
            resultado.referencia_atual,
            resultado.referencia_anterior,
        )

    except Exception:
        return None

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


def combinar_mdo(
    res_onerada: ResultadoMDO,
    res_desonerada: ResultadoMDO,
    res_consultoria: ResultadoMDO,
) -> pd.DataFrame:
  
# Consolide as diferentes bases de mão de obra em uma única estrutura de análise.
# A aplicação recebe arquivos separados porque cada base representa uma natureza distinta de composição de custos.
# Aqui os registros são reunidos e códigos duplicados são tratados para formar uma visão consolidada.

    dados_combinados = pd.concat(
        [
            res_onerada.dados,
            res_desonerada.dados,
            res_consultoria.dados,
        ],
        ignore_index=True,
    )

    return (
        dados_combinados
        .drop_duplicates(
            subset="codigo",
            keep="first",
        )
        .reset_index(drop=True)
    )


def calcular_var_total(
    df_atual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    col_codigo: str = "codigo",
    col_valor: str = "valor_total",
) -> pd.Series:

# Calculei a variação percentual do valor total entre duas referências.
# Comparação é feita pelo código de cada categoria. Antes do cálculo, valido a existência dos valores e descarto
# divisões por zero, evitando resultados inconsistentes em registros novos ou incompletos.

    valores_anteriores = (
        df_anterior
        .set_index(col_codigo)[col_valor]
        .to_dict()
    )

    resultado = {}

    for _, registro in df_atual.iterrows():
        codigo = registro[col_codigo]
        valor_atual = registro[col_valor]
        valor_anterior = valores_anteriores.get(codigo)

        valores_validos = (
            valor_atual is not None
            and valor_anterior is not None
            and not pd.isna(valor_atual)
            and not pd.isna(valor_anterior)
            and valor_anterior != 0
        )

        if valores_validos:
            resultado[codigo] = round(
                (valor_atual / valor_anterior - 1) * 100,
                4,
            )
        else:
            resultado[codigo] = None

    return pd.Series(
        resultado,
        name="var_total_pct",
    )


def _fmt_pct(
    valor: object,
    casas: int = 2,
) -> str:

# Padronizei a apresentação dos percentuais antes de enviá-los ao documento.
# Valores ausentes recebem um marcador textual, enquanto resultados válidos seguem o padrão decimal usado no relatório.
# Essa função mantém consistência visual entre tabelas calculadas por diferentes etapas da aplicação.


    if _is_nan(valor):
        return "-"

    return f"{float(valor):.{casas}f}".replace(
        ".",
        ",",
    )


def montar_tabela_variacoes(
    resultado_var: ResultadoVariacoes,
    df_mdo_atual: pd.DataFrame,
    df_mdo_anterior: pd.DataFrame | None = None,
) -> list[dict]:

# Transformei os resultados processados em uma estrutura compatível com o template Word.
# Combinei informações cadastrais, variações salariais e variações do valor total. 
# Também atribuo regras visuais para que alterações relevantes sejam destacadas automaticamente durante a renderização do documento.

    variacao_valor_total = None

    if (
        df_mdo_anterior is not None
        and not df_mdo_anterior.empty
    ):
        variacao_valor_total = calcular_var_total(
            df_atual=df_mdo_atual,
            df_anterior=df_mdo_anterior,
        )

    tabela = []
    dados_variacoes = resultado_var.categorias

    if dados_variacoes.empty:
        return tabela

    for _, registro in dados_variacoes.iterrows():
        codigo = str(
            registro.get(
                "codigo",
                "",
            )
        )

        descricao = str(
            registro.get(
                "descricao",
                "",
            )
        )

        unidade = str(
            registro.get(
                "unidade",
                "",
            )
        )

        segmento = str(
            registro.get(
                "segmento",
                "",
            )
        )

        variacao_decimal = registro.get(
            "variacao_decimal"
        )

        variacao_salarial = (
            None
            if _is_nan(variacao_decimal)
            else float(variacao_decimal) * 100
        )

        if (
            variacao_valor_total is not None
            and codigo in variacao_valor_total.index
        ):
            valor_total = variacao_valor_total[codigo]

            variacao_total = (
                variacao_salarial
                if _is_nan(valor_total)
                else float(valor_total)
            )

        else:
            variacao_total = variacao_salarial

        tabela.append(
            {
                "cod": codigo,
                "desc": descricao,
                "un": unidade,
                "seg": segmento,
                "vs": _fmt_pct(
                    variacao_salarial
                ),
                "vt": _fmt_pct(
                    variacao_total
                ),
                "bg_vt": _cor_variacao(
                    variacao_total
                ),
                "bg": "FFFFFF",
            }
        )

    return tabela


def substituir_imagens_docx(
    docx_path: str,
    lista_imgs: list,
) -> None:

# Substitui as imagens de referência do template pelos gráficos gerados durante a execução.
# A substituição é feita diretamente nos relacionamentos internos do arquivo Word. Isso permite preservar posições,
# Dimensões e estrutura visual previamente definidas no documento, sem reconstruir o layout pelo código.

    from docx import Document

    documento = Document(docx_path)
    indice_imagem = 0

    for shape in documento.inline_shapes:
        if indice_imagem >= len(lista_imgs):
            break

        try:
            buffer = lista_imgs[indice_imagem]
            buffer.seek(0)

            blip = (
                shape
                ._inline
                .graphic
                .graphicData
                .pic
                .blipFill
                .blip
            )

            relationship_id = blip.embed

            imagem_documento = (
                documento
                .part
                .related_parts[relationship_id]
            )

            imagem_documento._blob = buffer.read()

            buffer.seek(0)

        except Exception as exc:
            print(
                f"[Erro] Imagem "
                f"{indice_imagem + 1}: "
                f"{exc}"
            )

        indice_imagem += 1

    documento.save(docx_path)


def gerar_relatorio(
    path_variacoes: str,
    path_mdo_onerada: str,
    path_mdo_desonerada: str,
    path_mdo_consultoria: str,
    output_path: str,
    path_mdo_anterior: str | None = None,
    num_relatorio: str = "01/2025",
    mes_emissao: int | None = None,
    ano_emissao: int | None = None,
    gerar_texto_llm: bool = False,
) -> tuple[str, list]:
  
# Fluxo completo de geração do relatório técnico.
# O processo começa pela leitura das planilhas, segue para consolidação e comparação dos dados, prepara o contexto
# utilizado pelo template, aciona opcionalmente a geração narrativa por IA, renderiza o documento e substitui as
# imagens de referência pelos gráficos produzidos durante a execução.

# Essa orquestração mantém cada responsabilidade em seu próprio módulo, enquanto oferece um único ponto de execução para a aplicação.

    from docxtpl import DocxTemplate

    if not os.path.exists(_TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Template não encontrado: {_TEMPLATE_PATH}\n"
            "Verifique o arquivo templates/template_exemplo.docx."
        )

    print(
        "Lendo relatório de variações..."
    )

    resultado_variacoes = ler_variacoes(
        path_variacoes
    )

    referencia_atual = (
        resultado_variacoes
        .referencia_atual
    )

    print(
        f"{len(resultado_variacoes.categorias)} "
        f"categorias | "
        f"referência="
        f"{label_referencia(referencia_atual)}"
    )

    print(
        "Lendo bases atuais de mão de obra..."
    )

    resultado_onerada = ler_mdo_onerada(
        path_mdo_onerada
    )

    resultado_desonerada = ler_mdo_desonerada(
        path_mdo_desonerada
    )

    resultado_consultoria = ler_mdo_consultoria(
        path_mdo_consultoria
    )

    df_mdo_atual = combinar_mdo(
        res_onerada=resultado_onerada,
        res_desonerada=resultado_desonerada,
        res_consultoria=resultado_consultoria,
    )

    print(
        f"MDO consolidada: "
        f"{len(df_mdo_atual)} registros"
    )

    df_mdo_anterior = None

    if (
        path_mdo_anterior
        and os.path.exists(path_mdo_anterior)
    ):
        print(
            "Lendo base anterior de mão de obra..."
        )

        resultado_anterior = ler_mdo_onerada(
            path_mdo_anterior
        )

        df_mdo_anterior = (
            resultado_anterior.dados
        )

        print(
            f"MDO anterior: "
            f"{len(df_mdo_anterior)} registros"
        )

    mes_referencia = referencia_atual.month
    ano_referencia = referencia_atual.year

    mes_documento = (
        mes_emissao
        or mes_referencia
    )

    ano_documento = (
        ano_emissao
        or ano_referencia
    )

    context = {
        "num_relatorio": num_relatorio,
        "referencia_upper": (
            label_referencia(
                referencia_atual
            )
            .upper()
        ),
        "referencia_lower": (
            label_referencia(
                referencia_atual
            )
        ),
        "referencia_barra": (
            label_referencia_barra(
                referencia_atual
            )
        ),
        "mes_emissao_upper": (
            NOMES_MESES[
                mes_documento
            ]
            .upper()
        ),
        "ano_emissao": str(
            ano_documento
        ),
        "tabela_variacoes": (
            montar_tabela_variacoes(
                resultado_var=resultado_variacoes,
                df_mdo_atual=df_mdo_atual,
                df_mdo_anterior=df_mdo_anterior,
            )
        ),
    }

    if gerar_texto_llm:
        print(
            "Gerando textos narrativos por IA..."
        )

        textos = gerar_texto_completo(
            context
        )

        context.update(
            textos
        )

        if textos.get(
            "texto_resumo_executivo"
        ):
            print(
                "Resumo executivo gerado."
            )

        if textos.get(
            "texto_analise_variacoes"
        ):
            print(
                "Análise de variações gerada."
            )

    else:
        context[
            "texto_resumo_executivo"
        ] = ""

        context[
            "texto_analise_variacoes"
        ] = ""

    os.makedirs(
        os.path.dirname(output_path)
        or ".",
        exist_ok=True,
    )

    documento = DocxTemplate(
        _TEMPLATE_PATH
    )

    documento.render(
        context
    )

    documento.save(
        output_path
    )

    print(
        f"Documento salvo: "
        f"{output_path}"
    )

    imagens = []

    try:
        print(
            "Gerando gráficos..."
        )

        imagens = (
            gerar_graficos_representativas(
                resultado_variacoes
            )
        )

        if imagens:
            substituir_imagens_docx(
                docx_path=output_path,
                lista_imgs=imagens,
            )

            print(
                f"{len(imagens)} "
                f"gráfico(s) inserido(s)."
            )

            for buffer in imagens:
                buffer.seek(0)

        else:
            print(
                "Nenhum gráfico foi gerado "
                "por insuficiência de dados."
            )

    except Exception as exc:
        print(
            f"[Aviso] Falha na geração "
            f"dos gráficos: {exc}"
        )

    print(
        "Processamento concluído."
    )

    return (
        output_path,
        imagens,
    )


def _aplicar_estilo_interface() -> None:

# Identidade visual da interface em um único bloco.
# Essa separação evita misturar configuração visual com regras de processamento e facilita futuras alterações no
# layout sem afetar o fluxo responsável pela geração dos relatórios.

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 3.8rem;
                max-width: 1120px;
            }

            h1 {
                color: #003A70;
                font-size: 1.65rem !important;
                font-weight: 600 !important;
            }

            h2,
            h3 {
                color: #003A70;
                font-weight: 600 !important;
            }

            .stButton > button {
                background-color: #003A70;
                color: white;
                border-radius: 6px;
                border: 1px solid #003A70;
                font-weight: 500;
            }

            .stButton > button:hover {
                background-color: #005A9C;
                border-color: #005A9C;
                color: white;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_report_page() -> None:

# Construí esta função como a interface operacional do gerador de relatórios.
# Usuário envia os arquivos necessários, acompanha o status de cada entrada, valida a referência detectada, informa
# os dados de identificação do documento e escolhe se deseja utilizar a geração narrativa por IA.

# Depois do processamento, a interface apresenta uma prévia dos gráficos e disponibiliza o relatório consolidado em formato Word. 
# Montei isso para reduzir operações manuais e tornar a geração do documento mais previsível.

    _aplicar_estilo_interface()

    if os.path.exists(
        _LOGO_PATH
    ):
        st.image(
            _LOGO_PATH,
            width=155,
        )

    st.title(
        "Gerador de Relatório Consolidado"
    )

    st.caption(
        "Automação de documentos técnicos — Mão de Obra"
    )

    with st.sidebar:
        st.markdown(
            "### Arquivos do release atual"
        )

        st.info(
            "Envie os quatro arquivos obrigatórios do release.\n\n"
            "O arquivo de MDO anterior é opcional e permite calcular "
            "a variação do valor total entre referências."
        )

        upload_variacoes = st.file_uploader(
            "Relatório de Variações (.xlsx) *",
            type=["xlsx"],
            key="up_var",
        )

        upload_onerada = st.file_uploader(
            "MDO Onerada (.xlsx) *",
            type=["xlsx"],
            key="up_onerada",
        )

        upload_desonerada = st.file_uploader(
            "MDO Desonerada (.xlsx) *",
            type=["xlsx"],
            key="up_desonerada",
        )

        upload_consultoria = st.file_uploader(
            "MDO Consultoria (.xlsx) *",
            type=["xlsx"],
            key="up_consultoria",
        )

        st.markdown(
            "---"
        )

        st.markdown(
            "### Release anterior"
        )

        upload_mdo_anterior = (
            st.file_uploader(
                "MDO anterior (.xlsx)",
                type=["xlsx"],
                key="up_mdo_ant",
            )
        )

    coluna_1, coluna_2, coluna_3 = (
        st.columns(3)
    )

    coluna_1.write(
        "Variações: OK"
        if upload_variacoes
        else "Variações: pendente"
    )

    coluna_2.write(
        "Onerada: OK"
        if upload_onerada
        else "Onerada: pendente"
    )

    coluna_3.write(
        "Desonerada: OK"
        if upload_desonerada
        else "Desonerada: pendente"
    )

    arquivos_obrigatorios = [
        upload_variacoes,
        upload_onerada,
        upload_desonerada,
        upload_consultoria,
    ]

    if not all(
        arquivos_obrigatorios
    ):
        st.markdown(
            "**Envie todos os arquivos obrigatórios "
            "para liberar a geração.**"
        )

        return

    st.write(
        "---"
    )

    referencia_detectada = (
        _detectar_referencia(
            upload_variacoes
        )
    )

    if referencia_detectada:
        (
            referencia_atual,
            referencia_anterior,
        ) = referencia_detectada

        st.success(
            f"Referência detectada: "
            f"**{label_referencia(referencia_atual).capitalize()}** "
            f"(anterior: "
            f"{label_referencia(referencia_anterior)})"
        )

        mes_referencia = (
            referencia_atual.month
        )

        ano_referencia = (
            referencia_atual.year
        )

    else:
        st.warning(
            "Não foi possível detectar "
            "a referência automaticamente."
        )

        mes_referencia = (
            datetime.now().month
        )

        ano_referencia = (
            datetime.now().year
        )

    with st.expander(
        "Identificação do relatório",
        expanded=True,
    ):
        coluna_a, coluna_b = (
            st.columns(2)
        )

        numero_relatorio = (
            coluna_a.text_input(
                "Número do Relatório",
                value=(
                    f"{mes_referencia:02d}/"
                    f"{ano_referencia}"
                ),
            )
        )

        mes_emissao_padrao = (
            mes_referencia + 1
            if mes_referencia < 12
            else 1
        )

        ano_emissao_padrao = (
            ano_referencia
            if mes_referencia < 12
            else ano_referencia + 1
        )

        meses = list(
            NOMES_MESES.keys()
        )

        coluna_c, coluna_d = (
            st.columns(2)
        )

        mes_emissao = (
            coluna_c.selectbox(
                "Mês de emissão",
                options=meses,
                index=meses.index(
                    mes_emissao_padrao
                ),
                format_func=lambda mes: (
                    NOMES_MESES[mes]
                    .capitalize()
                ),
            )
        )

        ano_emissao = int(
            coluna_d.number_input(
                "Ano de emissão",
                min_value=2020,
                max_value=2100,
                value=int(
                    ano_emissao_padrao
                ),
                step=1,
            )
        )

        st.markdown(
            "---"
        )

        gerar_texto_llm = (
            st.checkbox(
                "Gerar texto narrativo com IA",
                value=False,
                help=(
                    "Gera parágrafos técnicos "
                    "a partir dos dados processados. "
                    "Requer uma chave da OpenAI "
                    "configurada no ambiente."
                ),
            )
        )

    if st.button(
        "Gerar Relatório",
        type="primary",
    ):
        temp_dir = tempfile.mkdtemp(
            prefix="report_gen_"
        )

        try:
            with st.spinner(
                "Processando dados, gerando gráficos "
                "e montando o documento..."
            ):
                path_variacoes = _salvar(
                    uploaded_file=upload_variacoes,
                    temp_dir=temp_dir,
                    prefixo="variacoes",
                )

                path_onerada = _salvar(
                    uploaded_file=upload_onerada,
                    temp_dir=temp_dir,
                    prefixo="onerada",
                )

                path_desonerada = _salvar(
                    uploaded_file=upload_desonerada,
                    temp_dir=temp_dir,
                    prefixo="desonerada",
                )

                path_consultoria = _salvar(
                    uploaded_file=upload_consultoria,
                    temp_dir=temp_dir,
                    prefixo="consultoria",
                )

                path_mdo_anterior = (
                    _salvar(
                        uploaded_file=upload_mdo_anterior,
                        temp_dir=temp_dir,
                        prefixo="mdo_anterior",
                    )
                    if upload_mdo_anterior
                    else None
                )

                sufixo = (
                    f"{MESES_ABV[mes_referencia]}"
                    f"{str(ano_referencia)[-2:]}"
                )

                output_name = (
                    f"Relatorio_Consolidado_"
                    f"{sufixo}.docx"
                )

                output_path = os.path.join(
                    temp_dir,
                    output_name,
                )

                (
                    output_path,
                    imagens_geradas,
                ) = gerar_relatorio(
                    path_variacoes=path_variacoes,
                    path_mdo_onerada=path_onerada,
                    path_mdo_desonerada=path_desonerada,
                    path_mdo_consultoria=path_consultoria,
                    output_path=output_path,
                    path_mdo_anterior=path_mdo_anterior,
                    num_relatorio=numero_relatorio,
                    mes_emissao=mes_emissao,
                    ano_emissao=ano_emissao,
                    gerar_texto_llm=gerar_texto_llm,
                )

            st.success(
                "Relatório gerado com sucesso."
            )

            if imagens_geradas:
                st.markdown(
                    "### Prévia dos gráficos gerados"
                )

                colunas = st.columns(2)

                categorias_exibidas = zip(
                    imagens_geradas,
                    CATEGORIAS_REPRESENTATIVAS,
                )

                for indice, item in enumerate(
                    categorias_exibidas,
                    start=1,
                ):
                    buffer, categoria = item
                    _, nome = categoria

                    with colunas[
                        (indice - 1) % 2
                    ]:
                        st.caption(
                            f"Gráfico {indice} — {nome}"
                        )

                        try:
                            buffer.seek(0)

                            if (
                                buffer
                                .getbuffer()
                                .nbytes
                                > 0
                            ):
                                st.image(
                                    buffer,
                                    width=500,
                                )

                            else:
                                st.warning(
                                    f"Gráfico {indice}: "
                                    "imagem vazia."
                                )

                        except Exception as exc:
                            st.warning(
                                f"Gráfico {indice}: "
                                f"erro ao exibir: {exc}"
                            )

            st.divider()

            with open(
                output_path,
                "rb",
            ) as arquivo:
                st.download_button(
                    label=(
                        "Baixar relatório (.docx)"
                    ),
                    data=arquivo,
                    file_name=output_name,
                    mime=(
                        "application/vnd."
                        "openxmlformats-officedocument."
                        "wordprocessingml.document"
                    ),
                )

        except FileNotFoundError as exc:
            st.warning(
                str(exc)
            )

        except Exception:
            st.error(
                "Ocorreu um erro durante "
                "o processamento."
            )

            st.code(
                traceback.format_exc()
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )

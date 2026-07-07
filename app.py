"""
Eu estruturei esta aplicação como a porta de entrada de uma automação para relatórios técnicos.

Neste arquivo, concentrei apenas a configuração inicial da interface e o acionamento da página principal de geração.
Essa separação é importante porque mantém o app.py limpo, facilita a manutenção do projeto e deixa claro que a lógica
principal da aplicação está organizada em módulos específicos, sem misturar interface, processamento e geração de documento.

A aplicação foi pensada para transformar planilhas estruturadas em relatórios técnicos em Word, com apoio de gráficos,
tratamento de dados e texto narrativo gerado por IA. Para a versão pública, a arquitetura comunica o funcionamento do
sistema sem depender de bases reais, preservando dados sensíveis do ambiente de trabalho.
"""

from __future__ import annotations

import streamlit as st

from template.report_generator import run_report_page


def main() -> None:
    """
    Eu defini esta função como ponto central de execução da aplicação.

    A configuração da página fica isolada aqui para deixar o comportamento visual do Streamlit previsível.
    Isso ajuda a aplicação a abrir sempre com o mesmo layout, com navegação lateral expandida e uma área principal
    mais adequada para leitura de tabelas, gráficos e relatórios técnicos.
    """

    st.set_page_config(
        page_title="Automação de Relatórios Técnicos",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.markdown("# Automação de Relatórios")
    st.sidebar.markdown("---")

    run_report_page()


if __name__ == "__main__":
    main()

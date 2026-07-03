# Automação de Relatórios

Aplicação Streamlit que automatiza a geração de relatórios técnicos 
(.docx) a partir de planilhas Excel, com geração de texto narrativo 
via LLM.

## Funcionalidades

- Leitura automática de planilhas Excel com dados de custos/variações
- Geração de tabelas comparativas entre períodos
- Gráficos de séries históricas (Matplotlib/Plotly)
- Geração de texto narrativo com IA (opcional)
- Exportação em .docx com template customizável (docxtpl)

## Stack

- Python 3.12
- Streamlit 1.57
- OpenAI GPT-4o-mini (texto narrativo)
- docxtpl (templates Word)
- Pandas + OpenPyXL (processamento de dados)
- Matplotlib + Plotly (visualizações)

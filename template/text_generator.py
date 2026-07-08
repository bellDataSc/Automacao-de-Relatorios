# Geração narrativa da aplicação.
# Deixei os dados já calculados pelo sistema são transformados em texto técnico para compor o relatório Word.
# Todo esse processo me ajudou a reduz escrita manual, mantém padronização entre releases e permite que a análise textual
# acompanhe automaticamente as tabelas, variações e categorias processadas pela automação.
# A geração de texto não substitui o cálculo dos dados. O modelo recebe apenas informações já estruturadas pela aplicação
# e atua como apoio para redigir descrições formais, objetivas e consistentes. 
# Para uma versão aberta do projeto, trabalhei para demonstra a integração com IA sem expor dados reais :)

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """
Você é um analista técnico especializado em custos de mão de obra para o setor de infraestrutura.

Regras obrigatórias:
- Escreva em português formal, com tom técnico e imparcial.
- Não emita opiniões nem recomendações.
- Descreva apenas os dados fornecidos.
- Use valores exatos conforme recebidos.
- Não arredonde além do formato já informado.
- Estruture o texto em parágrafos curtos e objetivos.
- Não use bullet points nem listas.
- Mencione o período de referência quando relevante.
- Trate variações acima de 10% como variações expressivas.
- Trate categorias marcadas com asterisco (*) como novas inclusões do release.
""".strip()


def _get_client():
  
# Criação do cliente em uma função isolada para proteger a configuração da aplicação.
# A chave da API é lida exclusivamente por variável de ambiente, o que evita expor credenciais no código público.
# Essa separação também facilita trocar modelo, ambiente ou provedor futuramente sem alterar a lógica dos relatórios.

    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key or api_key.startswith("sk-COLE") or api_key == "sk-your-key-here":
        raise EnvironmentError(
            "OPENAI_API_KEY não configurada. Defina a variável no arquivo .env da raiz do projeto."
        )

    return OpenAI(api_key=api_key)


def _converter_variacao(valor: object) -> float | None:
  
# Eu uso esta função para converter percentuais de variação de forma controlada.
# Os dados podem chegar como texto, número ou marcador vazio. Essa função padroniza a conversão e impede que valores
# inválidos quebrem a geração narrativa do relatório.


    if valor in (None, "", "-"):
        return None

    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _extrair_variacoes_validas(tabela_variacoes: list[dict]) -> list[dict]:
  
# Separei aqui as categorias existentes que possuem variação numérica válida.
# Necessario porque categorias novas podem não ter base anterior de comparação. 
# Ao filtrar esses casos, o texto gerado passa a descrever apenas variações efetivamente comparáveis.


    variacoes_validas = []

    for registro in tabela_variacoes:
        codigo = str(registro.get("cod", "")).strip()

        if codigo.startswith("*"):
            continue

        variacao = _converter_variacao(registro.get("vs"))

        if variacao is None:
            continue

        variacoes_validas.append(
            {
                "codigo": codigo,
                "descricao": registro.get("desc", ""),
                "segmento": registro.get("seg", ""),
                "variacao": variacao,
            }
        )

    return variacoes_validas


def _calcular_media_variacao(variacoes_validas: list[dict]) -> float:
  
# Centralizei o cálculo da média para manter a narrativa alinhada aos dados computados.
# A função retorna zero quando não há variações válidas, evitando erro em relatórios demonstrativos ou incompletos.

    if not variacoes_validas:
        return 0.0

    valores = [registro["variacao"] for registro in variacoes_validas]

    return sum(valores) / len(valores)


def _formatar_destaques(variacoes_validas: list[dict], limite: int = 8) -> str:
  
# Fase que preparei os principais destaques antes de enviar o contexto para o modelo.
# A ordenação por valor absoluto ajuda a destacar as maiores movimentações, tanto positivas quanto negativas,
# mantendo a análise focada nas alterações mais relevantes do release.


    destaques = sorted(
        variacoes_validas,
        key=lambda registro: abs(registro["variacao"]),
        reverse=True,
    )[:limite]

    if not destaques:
        return "Sem variações válidas disponíveis."

    return "\n".join(
        f"{registro['descricao']} ({registro['segmento']}): {registro['variacao']:.2f}%"
        for registro in destaques
    )


def _resumo_segmento(registros: list[dict]) -> str:
  
# Resumi cada segmento com medidas simples para apoiar uma análise comparativa.
# O objetivo é oferecer ao modelo um contexto estatístico objetivo, sem permitir que ele invente conclusões fora dos
# dados fornecidos pela aplicação.

    if not registros:
        return "sem dados"

    valores = [registro["variacao"] for registro in registros]

    return (
        f"média {sum(valores) / len(valores):.2f}%, "
        f"mínima {min(valores):.2f}%, "
        f"máxima {max(valores):.2f}%"
    )


def _separar_variacoes_por_segmento(variacoes_validas: list[dict]) -> tuple[list[dict], list[dict]]:
  
# Separei variações por segmento para deixar a análise mais aderente à estrutura do relatório.
# Quando o segmento não está classificado explicitamente como consultoria, ele é tratado no grupo de construção.
# Essa regra preserva o comportamento esperado do relatório e evita perda de registros por nomenclaturas incompletas.

    construcao = []
    consultoria = []

    for registro in variacoes_validas:
        segmento = str(registro.get("segmento", ""))

        if "Consultoria" in segmento:
            consultoria.append(registro)
        else:
            construcao.append(registro)

    return construcao, consultoria


def _chamar_modelo(prompt: str, max_tokens: int) -> str:
  
# A chamada ao modelo para manter o controle da geração em um único ponto.
# Isso me ajudou deixar a aplicação mais simples de manter, porque temperatura, modelo e estrutura das mensagens ficam
# padronizados para todas as seções narrativas do relatório.

    client = _get_client()

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content.strip()


def gerar_texto_resumo_executivo(context: dict) -> str:
  
# Eu gero o resumo executivo a partir dos dados consolidados do relatório.
# Função calcula quantidade de categorias, identifica novas inclusões, mede a variação média e seleciona os maiores destaques. 
# O modelo recebe esse contexto pronto para redigir uma síntese técnica, curta e controlada.

    tabela_variacoes = context.get("tabela_variacoes", [])

    if not tabela_variacoes:
        return ""

    total_categorias = len(tabela_variacoes)
    novas = [
        registro
        for registro in tabela_variacoes
        if str(registro.get("cod", "")).strip().startswith("*")
    ]

    variacoes_validas = _extrair_variacoes_validas(tabela_variacoes)
    media_variacao = _calcular_media_variacao(variacoes_validas)
    principais_variacoes = _formatar_destaques(variacoes_validas)

    prompt = f"""
Escreva um resumo executivo para o relatório de custos de mão de obra.

Referência: {context.get("referencia_lower", "N/D")}

Dados do release:
Total de categorias profissionais analisadas: {total_categorias}
Categorias novas incluídas neste release: {len(novas)}
Variação salarial média: {media_variacao:.2f}%

Principais variações observadas:
{principais_variacoes}

O texto deve ter de 2 a 3 parágrafos e no máximo 200 palavras. Contextualize o release, mencione o número de categorias,
destaque as variações expressivas e mencione categorias novas quando existirem.
""".strip()

    return _chamar_modelo(prompt=prompt, max_tokens=500)


def gerar_texto_analise_variacoes(context: dict) -> str:
  
# Análise textual das variações por segmento.
# Criei a função que separa as categorias entre construção e consultoria, calcula medidas resumidas e envia ao modelo apenas os
# dados necessários para uma comparação técnica entre os segmentos.

    tabela_variacoes = context.get("tabela_variacoes", [])

    if not tabela_variacoes:
        return ""

    variacoes_validas = _extrair_variacoes_validas(tabela_variacoes)
    construcao, consultoria = _separar_variacoes_por_segmento(variacoes_validas)

    destaques_construcao = _formatar_destaques(construcao, limite=5)
    destaques_consultoria = _formatar_destaques(consultoria, limite=5)

    prompt = f"""
Escreva uma análise das variações salariais por segmento para o relatório.

Referência: {context.get("referencia_lower", "N/D")}

Segmento Construção:
Quantidade de categorias: {len(construcao)}
Resumo estatístico: {_resumo_segmento(construcao)}
Destaques:
{destaques_construcao}

Segmento Consultoria:
Quantidade de categorias: {len(consultoria)}
Resumo estatístico: {_resumo_segmento(consultoria)}
Destaques:
{destaques_consultoria}

O texto deve ter 2 parágrafos e no máximo 150 palavras. Compare os dois segmentos e destaque diferenças relevantes,
sem emitir recomendação ou opinião.
""".strip()

    return _chamar_modelo(prompt=prompt, max_tokens=400)


def gerar_texto_completo(context: dict) -> dict[str, str]:
# Concentrei aqui a geração de todas as seções narrativas do relatório.
# Essa função funciona como uma camada de orquestração: chama cada texto necessário e devolve um dicionário pronto para ser usado pelo gerador de documento. 
# Se a chave da API não estiver configurada, a aplicação continua gerando o relatório sem texto automático, o que mantém o fluxo funcional em ambientes públicos ou demonstrativos.

    resultado = {
        "texto_resumo_executivo": "",
        "texto_analise_variacoes": "",
    }

    try:
        resultado["texto_resumo_executivo"] = gerar_texto_resumo_executivo(context)
        resultado["texto_analise_variacoes"] = gerar_texto_analise_variacoes(context)
    except EnvironmentError:
        return resultado
    except Exception as exc:
        print(f"[Aviso] Geração de texto por IA falhou: {exc}")

    return resultado

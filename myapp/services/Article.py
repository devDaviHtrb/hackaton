
# Article.py
#
# Serviço de pontuação (scoring) e ranqueamento de artigos candidatos a
# referência. É o passo final do pipeline:
#
#   Gemini (contexto do artigo do usuário)
#     -> OpenAlex (candidatos a referência, via AlexService)
#       -> GenderizeNames (composição de gênero das autorias)
#         -> ESTE arquivo (similaridade + score geral + ordenação)
#
# Combina duas famílias de sinais:
#   1. Similaridade textual entre o artigo do usuário e cada candidato
#      (semântica via embeddings + léxica via TF-IDF).
#   2. Métricas do candidato: importância (Gemini), atualidade, relevância
#      por citações e participação feminina nas autorias.

import datetime

from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from myapp.services.GeminiService import article_importance
from typing import Dict, Any

from myapp.services.OpenAlex import AlexService


# Peso de cada campo textual dentro do cálculo de similaridade.
# O resumo (abstract) domina por ser o texto mais informativo do artigo.
WEIGHTS = {
    "title": 0.20,
    "abstract": 0.45,
    "keywords": 0.35
}

# Peso de cada métrica no score final (total) do candidato.
# Obs.: a soma não precisa ser 1; o "total" é uma soma ponderada bruta.
GERAL_WEIGHTS = {
    "similarity": 0.40,
    "importance": 0.55,
    "relevance": 0.25,
    "present": 0.05,
    "genre_compose": 0.05
}

# Peso de cada método de comparação textual dentro de compare_field.
# A comparação semântica (embeddings) pesa mais que a léxica (TF-IDF).
SEMANTIC_WEIGHT = 0.80
LEXICAL_WEIGHT = 0.20

# Modelo multilíngue de embeddings carregado uma única vez na importação
# (é caro de inicializar; reaproveitado em todas as comparações).
model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

# Instância única do serviço OpenAlex, compartilhada entre as chamadas
# (mantém o controle de rate limit interno da AlexService).
alexService =  AlexService()


def expand_score(score):
    """
    Makes medium/high similarities more distinguishable
    while keeping the result between 0 and 100.
    """
    # Normaliza para 0-1, aplica expoente < 1 (curva côncava que "estica"
    # a faixa média/alta) e volta para a escala 0-100.
    score = score / 100

    expanded_score = score ** 0.45

    return expanded_score * 100

def normalize_text(value):
    # Converte qualquer valor (None, lista ou escalar) em texto limpo,
    # para alimentar os comparadores sem quebrar.
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)

    return str(value).strip()


def semantic_similarity(text_a, text_b):
    # Similaridade por significado: dois embeddings normalizados cujo
    # produto escalar equivale ao cosseno entre eles.
    embeddings = model.encode(
        [text_a, text_b],
        normalize_embeddings=True
    )

    score = float(embeddings[0] @ embeddings[1])

    # Convert cosine similarity to a bounded 0-1 score.
    return max(0.0, min(1.0, score))


def lexical_similarity(text_a, text_b):
    # Similaridade por sobreposição de termos (palavras/bigramas em comum).
    if not text_a.strip() or not text_b.strip():
        return 0.0

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )

    try:
        vectors = vectorizer.fit_transform(
            [text_a, text_b]
        )
    except ValueError:
        # Ocorre quando os textos só têm stop words / ficam sem vocabulário.
        return 0.0

    return float(
        cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    )


def compare_field(text_a, text_b):
    # Combina os dois métodos num único score 0-1 para um campo.
    # Retorna None quando falta um dos lados (campo ignorado no total).
    if not text_a or not text_b:
        return None

    semantic_score = semantic_similarity(text_a, text_b)
    lexical_score = lexical_similarity(text_a, text_b)

    return (
        SEMANTIC_WEIGHT * semantic_score
        + LEXICAL_WEIGHT * lexical_score
    )


def calculate_article_similarity(article_a, article_b) -> float:
    # article_a: contexto do artigo do usuário no schema do Gemini (EN).
    # article_b: candidato vindo do OpenAlex.

    # Achata as key_words aninhadas em topics[].key_words numa lista única.
    kww = article_a.get("topics", [])
    kw = []
    for i in kww:
        for j in i["key_words"]:
            kw.append(j)
    # Mapeia o schema do Gemini para o formato interno {title, abstract, keywords}.
    article_a = {
        "title": article_a.get("title", ""),
        "abstract": (
            article_a.get("summary", "")
        ),
        "keywords": kw
    }

    # Mesmo formato interno para o candidato do OpenAlex.
    article_b = {
        "title": article_b.get("title", ""),
        "abstract": (
            article_b.get("abstract", "")
        ),
        "keywords": [i for i in article_b.get("keywords", [])]
    }

    #print(article_a,"\n\n" ,article_b, "\n\n\n\n")

    scores = {}
    weighted_total = 0.0
    total_weight = 0.0

    # Pontua campo a campo e acumula a média ponderada só dos campos válidos.
    for field, weight in WEIGHTS.items():
        text_a = normalize_text(article_a.get(field))
        text_b = normalize_text(article_b.get(field))

        score = compare_field(text_a, text_b)

        if score is None:
            continue

        scores[field] = round(score * 100, 2)
        weighted_total += score * weight
        total_weight += weight

    # Média ponderada apenas pelos pesos dos campos presentes (evita penalizar
    # candidatos sem keywords, por exemplo).
    final_score = (
    weighted_total / total_weight * 100
    if total_weight > 0
    else 0.0
)

    final_score = expand_score(final_score)

    return {
        "similarity": round(final_score, 2),
        "field_scores": scores,
    }


def convert_to_text(article) -> str:
    """
    Converte um artigo representado como dicionário em uma string de texto.
    """
    # Usado para enviar o candidato ao Gemini (cálculo de importância) como texto.
    title = article.get("title") or ""
    keywords = article.get("keywords") or []
    abstract = article.get("abstract") or ""

    text = f"Título: {title}\n"
    text += f"Palavras-chave: {' '.join(keywords)}\n"
    text += f"Resumo: {abstract}\n"

    return text


def calculate_article_importance(article_a:str, article_b:Dict[str, Any]) -> Dict[str, Any]:
    # Delega ao Gemini a avaliação de importância do candidato (article_b)
    # em relação ao texto do artigo do usuário (article_a).
    return article_importance(article_a, convert_to_text(article_b))
"""
{
  "score": 0,
  "h": meia-vida da área do artigo, em anos,
  "base": media de citações da area do artigo,
  "justification": "Justificativa da avaliação baseada nos textos fornecidos.",
  "evidence": [
    {
      "quote": "Trecho literal do resumo do artigo candidato.",
      "relevance": "Explicação de como o trecho sustenta a avaliação."
    }
  ],
  "uncertainty": "baixa",
  "using": [
    {
      "page": pagina do trecho recomendado, ou null se não disponível,
      "line": linha do trecho recomendado, ou null se não disponível,
      "word": palavra do trecho recomendado, ou null se não disponível,
      "paragraph_id": identificador do parágrafo do trecho recomendado, ou null se não disponível,
      "anchor_quote": "Trecho literal do texto original que identifica o local recomendado.",
      "citation_function": "fundamentação teórica",
      "reason": "Explicação da pertinência da citação neste local."
    }
  ]
}
"""

# 100 * 2**(age/h)
# h-> meia-vida da area artigo, em anos
def calculate_article_present(article_b, h:int):
    # (Primeira definição; é sobrescrita pela versão com h=10 mais abaixo.)
    current_year = datetime.now().year

    publication_year = article_b["ano"]
    age = max(0, current_year - publication_year)

    score = 100 * (2 ** (-age / h))

    return score


# base = med de citações da area do artigo
def calculate_article_relevance(article_b, base=5):
    # Relevância por impacto: citações do candidato normalizadas pela média
    # da área, limitada a 100.
    citations = article_b.get("cited_by_count") or 0  ## ATENTION

    if base <= 0:
        return 100
    
    score = (citations / base) * 100

    return min(score, 100)




# h -> meia-vida da área do artigo, em anos
def calculate_article_present(article_b, h: int =10):
    # Atualidade: decaimento exponencial pela idade do artigo. Quanto mais
    # antigo, menor o score (meia-vida = h anos). Esta versão (com default
    # h=10 e leitura de "year") substitui a definição anterior.
    current_year = datetime.date.today().year

    publication_year = article_b.get("year")
    if not publication_year:
        return 0.0

    age = max(0, current_year - publication_year)

    score = 100 * (2 ** (-age / h))

    return score




# % de mulheres entre os autores do artigo
def calculate_article_genre_compose(article_b):
    # Participação feminina estimada (vinda de GenderizeNames via OpenAlex).
    return (article_b.get("genero") or {}).get("female_percentage", 0) or 0


def calculate_score(article_a_text, article_a_data, article_b) -> Dict[str, Any]:
    # Reúne todas as métricas de um único candidato e calcula o total ponderado.
    similarity_result = calculate_article_similarity(
        article_a_data, article_b
    )
    # calculate_article_similarity devolve {"similarity", "field_scores"};
    # para o score geral usamos o valor escalar.
    if isinstance(similarity_result, dict):
        similarity_value = similarity_result.get("similarity", 0)
    else:
        similarity_value = similarity_result

    # Importância via Gemini é opcional (peso 0 no total). Se falhar
    # (503, JSON inválido, cota), não derruba o candidato: usa 0.
    from pydantic import BaseModel
    try:
        importance_result_data = calculate_article_importance(
            article_a_text, article_b
        )
        # Normaliza o retorno Pydantic para dict JSON-serializável.
        if isinstance(importance_result_data, BaseModel):
            importance_result_data = importance_result_data.model_dump(mode="json")
    except Exception as erro:
        # Guarda a mensagem de erro (truncada) em vez de interromper a análise.
        importance_result_data = {"erro": str(erro)[:200]}

    importance_result = (importance_result_data or {}).get("importance_score", 0) or 0

    # Demais métricas calculadas localmente (sem chamadas externas).
    present_result = calculate_article_present(
        article_b, h=5
    )
    relevance_result = calculate_article_relevance(
        article_b, base=10
    )
    genre_compose_result = calculate_article_genre_compose(
        article_b
    )

    return {
        "similarity": similarity_value,
        "importance": importance_result,
        "present": present_result,
        "relevance": relevance_result,
        "genre_compose": genre_compose_result,
        # Score final: soma ponderada de todas as métricas (ver GERAL_WEIGHTS).
        "total":
            similarity_value*GERAL_WEIGHTS["similarity"] +
            importance_result*GERAL_WEIGHTS["importance"] +
            present_result*GERAL_WEIGHTS["present"] +
            relevance_result*GERAL_WEIGHTS["relevance"] +
            genre_compose_result*GERAL_WEIGHTS["genre_compose"],
        # Payload completo do Gemini (justificativa, evidências, "using"...).
        "correction": importance_result_data
    }


## articlea[all_content, article_analysis]
def calculate_articles_scores(article_a, limit = 5, offset = 0):
    # Ponto de entrada chamado pela rota após Gemini + OpenAlex.
    # article_a["all_content"]: texto cru do artigo enviado pelo usuário.
    # article_a["article_analysis"]: contexto estruturado do Gemini.
    article_a_text = article_a.get("all_content", "")
    article_a_data = article_a.get("article_analysis", {})

    # Busca candidatos já filtrados por autoria feminina no OpenAlex.
    articles = alexService.buscar_artigos_para_comparacao(
        entrada=article_a_data,
        limite_percentual=25,
        country_id="BR",
        fallback_qtd=5,
    )

    ans = []
    cnt = 0
    # Garante que o contexto do Gemini seja dict (e não BaseModel) para o scoring.
    from pydantic import BaseModel
    if isinstance(article_a_data, BaseModel):
        article_a_data = article_a_data.model_dump()
    # Paginação simples: pula 'offset' candidatos e pontua no máximo 'limit'.
    for article_b in articles.get("candidatos", []):
        if(cnt < offset):
            cnt += 1
            continue
        if(cnt >= limit + offset):
            break
        data = calculate_score(article_a_text, article_a_data, article_b)
        ans.append({
            "article":{
                "article_data": article_b,
                "score_data": data
            }
        })
        cnt += 1

    # Lista de recomendações; a ordenação por "total" é feita a jusante.
    return ans
    """
    [
        "article":{
            "article_data": dados do artigo em alexService.buscar(),
            "score_data": {
                "similarity": similarity_score,
                "importance": importance_score,
                "present": present_score,
                "relevance": relevance_score,
                "genre_compose": genre_compose_score,
                "total": total_score,
                "correction":{
                    "H": meia-vida da área do artigo, em anos,
                    "base": med de citações da area do artigo
                    "score": 0,
                    "justification": "Justificativa da avaliação baseada nos textos fornecidos.",
                    "evidence": [
                        {
                        "quote": "Trecho literal do resumo do artigo candidato.",
                        "relevance": "Explicação de como o trecho sustenta a avaliação."
                        }
                    ],
                    "uncertainty": "baixa",
                    "using": [
                        {
                        "page": null,
                        "line": null,
                        "word": null,
                        "paragraph_id": null,
                        "anchor_quote": "Trecho literal do texto original que identifica o local recomendado.",
                        "citation_function": "fundamentação teórica",
                        "reason": "Explicação da pertinência da citação neste local."
                        }
                    ]
                }
            }
        }
    ]
    """

if __name__ == "__main__":
    # Smoke test manual da similaridade (não executa o pipeline completo).
    article_a = {
        "title": "Inteligência artificial na medicina",
        "abstract": (
            "Estudo sobre o uso de IA no diagnóstico de doenças."
        ),
        "keywords": [
            "inteligência artificial",
            "medicina",
            "diagnóstico",
        ],
    }

    article_b = {
        "title": "Aprendizado de máquina no diagnóstico médico",
        "abstract": (
            "Pesquisa sobre modelos de IA para detectar doenças."
        ),
        "keywords": [
            "IA",
            "medicina",
            "diagnóstico",
        ],
    }

    result = calculate_article_similarity(
        article_a, article_b
    )

    print(f"Similaridade: {result['similarity']}/100")

    for field, score in result["field_scores"].items():
        print(f"{field}: {score}/100")
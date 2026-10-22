
import datetime

from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from myapp.services.GeminiService import article_importance
from typing import Dict, Any

from myapp.services.OpenAlex import AlexService


WEIGHTS = {
    "title": 0.20,
    "abstract": 0.45,
    "keywords": 0.35,
    "similarity": 0.00,
    "importance": 0.00,
    "relevance": 0.00,
    "reliability": 0.00,
    "genre_compose": 0.00,
}

# Weight of each comparison method.
SEMANTIC_WEIGHT = 0.80
LEXICAL_WEIGHT = 0.20

model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

alexService =  AlexService()


def expand_score(score):
    """
    Makes medium/high similarities more distinguishable
    while keeping the result between 0 and 100.
    """
    score = score / 100

    expanded_score = score ** 0.45

    return expanded_score * 100

def normalize_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)

    return str(value).strip()


def semantic_similarity(text_a, text_b):
    embeddings = model.encode(
        [text_a, text_b],
        normalize_embeddings=True
    )

    score = float(embeddings[0] @ embeddings[1])

    # Convert cosine similarity to a bounded 0-1 score.
    return max(0.0, min(1.0, score))


def lexical_similarity(text_a, text_b):
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
        return 0.0

    return float(
        cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    )


def compare_field(text_a, text_b):
    if not text_a or not text_b:
        return None

    semantic_score = semantic_similarity(text_a, text_b)
    lexical_score = lexical_similarity(text_a, text_b)

    return (
        SEMANTIC_WEIGHT * semantic_score
        + LEXICAL_WEIGHT * lexical_score
    )


def calculate_article_similarity(article_a, article_b) -> float:
    article_a = {
        "title": article_a.get("title", ""),
        "abstract": (
            article_a.get("summary", "")
        ),
        "keywords": [keyword for topic in article_a.get("topics", []) if topic for keyword in topic.get("keywords", [])]
    }

    article_b = {
        "title": article_b.get("title", ""),
        "abstract": (
            article_b.get("summary", "")
        ),
        "keywords": [keyword for topic in article_b.get("topics", []) if topic for keyword in topic.get("keywords", [])]
    }
    scores = {}
    weighted_total = 0.0
    total_weight = 0.0

    for field, weight in WEIGHTS.items():
        text_a = normalize_text(article_a.get(field))
        text_b = normalize_text(article_b.get(field))

        score = compare_field(text_a, text_b)

        if score is None:
            continue

        scores[field] = round(score * 100, 2)
        weighted_total += score * weight
        total_weight += weight

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

# H e base
def calculate_article_importance(article_a, article_b) -> Dict[str, Any]:
    return article_importance(article_a.get("all_content", ""), article_b)
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
    current_year = datetime.now().year

    publication_year = article_b["ano"]
    age = max(0, current_year - publication_year)

    score = 100 * (2 ** (-age / h))

    return score

    pass

# base = med de citações da area do artigo
def calculate_article_relevance(article_b, base=5):
    citations = article_b["cited_by_count"] ## ATENTION

    if base <= 0:
        return 100
    
    score = (citations / base) * 100

    return min(score, 100)




# h -> meia-vida da área do artigo, em anos
def calculate_article_present(article_b, h: int =10):
    current_year = datetime.now().year

    publication_year = article_b["publication_year"]
    age = max(0, current_year - publication_year)

    score = 100 * (2 ** (-age / h))

    return score




# % de mulheres entre os autores do artigo
def calculate_article_genre_compose(article_b):
    return article_b.get("candidatos", {}).get("genero", {}).get("female_percentage", 0)


def calculate_score(article_a, article_b) -> Dict[str, Any]:
    similarity_result = calculate_article_similarity(
        article_a, article_b
    )
    importance_result_data = calculate_article_importance(
        article_a, article_b
    )

    importance_result = importance_result_data.get("importance_value", 0)

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
        "similarity": similarity_result,
        "importance": importance_result,
        "present": present_result,
        "relevance": relevance_result,
        "genre_compose": genre_compose_result,
        "total":
            similarity_result*WEIGHTS["similarity"] +
            importance_result*WEIGHTS["importance"] +
            present_result*WEIGHTS["present"] +
            relevance_result*WEIGHTS["relevance"] +
            genre_compose_result*WEIGHTS["genre_compose"],
        "correction": importance_result_data
    }


def calculate_articles_scores(article_a):
    results = []

    article_text = article_a.get("all_content", "")

    articles = alexService.filtrar_autoria_feminina(
        resultado = alexService.buscar(article_text, estimar_genero=True),
        limite_percentual=25,
        country_id="BR",
        fallback_qtd=5
    )

    ans = []
    for article_b in articles.get("candidatos", []):
        data = calculate_score(article_a, article_b)
        ans.append({
            "article":{
                "article_data": article_b,
                "score_data": data
            }
        })
        

    return results
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
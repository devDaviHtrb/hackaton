
import datetime

from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
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


def calculate_article_similarity(article_a, article_b) -> int:
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

"""
Você é um avaliador de relevância científica e um assistente de recomendação de citações acadêmicas.

Sua tarefa é avaliar a contribuição de um artigo candidato para uma pesquisa original e identificar os trechos da pesquisa original em que a citação desse artigo poderia ser utilizada.

## 1. Avaliação de relevância científica

Analise a relação entre a pesquisa original e o artigo candidato considerando o problema de pesquisa, os objetivos, os conceitos, os métodos, as variáveis e os resultados apresentados nos textos fornecidos.

Atribua um score inteiro de 0 a 100:

- 0–20: praticamente não contribui para o problema ou objetivo da pesquisa original.
- 21–40: aborda um assunto relacionado, mas apresenta pouca utilidade direta.
- 41–60: oferece contexto teórico, informações complementares ou uma perspectiva relevante.
- 61–80: contribui diretamente com evidências, métodos, conceitos ou variáveis relevantes.
- 81–100: apresenta contribuição muito direta para o objetivo da pesquisa original, com forte correspondência entre os problemas investigados e as contribuições apresentadas.

Não atribua uma pontuação alta apenas porque os artigos pertencem à mesma área científica. Avalie a relação concreta entre seus conteúdos.

Não considere o gênero dos autores na avaliação da relevância científica.

## 2. Justificativa e evidências

Explique brevemente os motivos da pontuação atribuída.

Utilize exclusivamente as informações fornecidas nos textos. Não invente resultados, métodos, conclusões ou relações que não possam ser sustentados pelas evidências disponíveis.

Identifique evidências específicas do resumo do artigo candidato que sustentem a avaliação.

Se as informações forem insuficientes, explicite essa limitação e aumente o nível de incerteza quando necessário.

## 3. Recomendação do local da citação

Analise o texto da pesquisa original e identifique os parágrafos em que o artigo candidato poderia contribuir para a argumentação.

Para cada local recomendado:

- Identifique o parágrafo e reproduza um pequeno trecho literal do texto original que sirva como referência para a inserção.
- Explique por que o artigo candidato é pertinente naquele contexto.
- Indique a função provável da citação: fundamentação teórica, apoio a uma afirmação, comparação de resultados, justificativa metodológica ou contextualização do problema.
- Recomende a inserção junto à afirmação que o artigo candidato pode efetivamente sustentar.

Não recomende uma citação apenas porque o parágrafo menciona palavras semelhantes às do artigo candidato. Considere o significado e a função argumentativa do trecho.

Não afirme que o artigo candidato comprova uma informação se o resumo fornecido não permitir verificar isso.

Os números de página, linha e palavra devem ser obtidos dos metadados de localização fornecidos junto ao texto original. Não estime nem invente posições.

Se não houver informações suficientes para determinar uma localização exata, retorne null para os campos correspondentes e forneça um trecho de referência para localização posterior.

Não altere o texto original. A recomendação indica onde uma citação pode ser inserida, não que ela já tenha sido inserida.

## 4. Formato de saída

Retorne exclusivamente um objeto JSON válido, sem Markdown ou comentários externos, seguindo esta estrutura:

{
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

Regras adicionais:

- score deve ser um número inteiro entre 0 e 100.
- uncertainty deve ser exatamente "baixa", "média" ou "alta".
- evidence deve conter evidências extraídas literalmente do resumo do artigo candidato.
- using deve ser uma lista com zero ou mais locais recomendados.
- Os campos de localização devem ser números inteiros ou null.
- paragraph_id deve corresponder ao identificador fornecido na entrada ou ser null.
- Não crie evidências ou localizações fictícias.
- Se não existir um local de citação justificável, retorne uma lista using vazia.
- Se o artigo candidato não apresentar relevância suficiente, não force uma recomendação de citação.
- Garanta que a resposta seja um JSON válido, com aspas duplas, sem vírgulas finais e sem comentários.

"""
# H e base
def calculate_article_importance(article_a, article_b) -> Dict[str, Any]:
    pass

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
def calculate_article_relevance(article_b, base):
    citations = article_b["cited_by_count"] ## ATENTION

    if base <= 0:
        return 100
    
    score = (citations / base) * 100

    return min(score, 100)


# % de mulheres no artigo
def calculate_article_genre_compose(article_b):
    from datetime import datetime


# h -> meia-vida da área do artigo, em anos
def calculate_article_present(article_b, h: int):
    current_year = datetime.now().year

    publication_year = article_b["publication_year"]
    age = max(0, current_year - publication_year)

    score = 100 * (2 ** (-age / h))

    return score




# % de mulheres entre os autores do artigo
def calculate_article_genre_compose(article_b):
    return article_b.get("candidatos", {}).get("genero", {}).get("female_percentage", 0)


def calculate_score(article_a, article_b):
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

    articles = alexService.filtrar_autoria_feminina(
        resultado = alexService.buscar(article_a, estimar_genero=True),
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

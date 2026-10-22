
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


WEIGHTS = {
    "title": 0.40,
    "abstract": 0.40,
    "keywords": 0.20,
}

# Weight of each comparison method.
SEMANTIC_WEIGHT = 0.80
LEXICAL_WEIGHT = 0.20

model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)


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


def calculate_article_similarity(article_a, article_b):
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

    return {
        "similarity": round(final_score, 2),
        "field_scores": scores,
    }


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
            "machine learning",
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

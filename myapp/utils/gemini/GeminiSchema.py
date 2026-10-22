# GeminiSchema.py
#
# Schemas Pydantic usados como response_schema nas chamadas ao Gemini
# (structured output). Cada classe define o formato JSON que o modelo é
# obrigado a devolver; as descrições dos Field orientam o modelo.
#
# IMPORTANTE: os nomes de campo aqui devem bater com os nomes citados nos
# prompts (GeminiPrompt.py). Um descompasso (ex.: prompt pedindo "score"
# enquanto o schema exige "importance_score") faz o valor vir zerado/errado.
#
# Restrição do Gemini: structured output NÃO aceita additionalProperties,
# então evite campos dict[str, ...] de chaves livres nestes schemas.

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from enum import Enum


#============================== Schema for Gemini =============================#

# Finalidade bibliográfica de um tópico. Enum fechado para o Gemini escolher
# exatamente uma das categorias (o OpenAlex também valida contra estes valores).
class TopicPurpose(str, Enum):
    METHOD = "method"
    RELATED_WORKS = "related_works"
    THEORETICAL_FRAMEWORK = "theoretical_framework"
    CONTEXT = "context"


# Um tópico = uma necessidade bibliográfica distinta do artigo. As key_words
# viram consultas de busca no OpenAlex.
class TopicSchema(BaseModel):
    theme: str = Field(description="O tema especifico que necessita outras referências específicas")
    description: str = Field("breve descrição do tema presente no artigo")
    key_words: list[str] = Field(
                            min_length=1,
                            description="Termos específicos para buscar artigos científicos relacionados ao tópico."
                            )
    purpose: TopicPurpose = Field(description="Finalidade bibliográfica do tópico.")

# Referência já citada no artigo do usuário. Serve para o OpenAlex EXCLUIR
# da busca o que o autor já referenciou (evita recomendar o que já existe).
class ExistingReference(BaseModel):
    doi: str | None = None
    title: str
    authors: list[str]
    # Ano limitado a 4 dígitos plausíveis; None quando não identificável.
    year: int | None = Field(default=None, ge=1000, le=2100)


# Schema principal da análise do artigo do usuário (1ª chamada ao Gemini).
# Cada atributo é uma "chave" do JSON de resposta. É a entrada do OpenAlex.
class ArticleContextSchema(BaseModel):
    title: str  = Field(description="O título, tema, principal do artigo do usuário")
    research_objective: str = Field(description="O objetivo principal da pesquisa/artigo")
    research_area: str = Field(description="A principal área científica relacionada com o artigo do usuario")
    summary: str = Field(description="Um breve resumo do artigo do usuário")
    topics: list[TopicSchema] = Field(
                    min_length=1,
                    description="Tópicos que representam necessidades bibliográficas distintas"
                    )
    existing_references: list[ExistingReference] = Field(
        description="Referências já presentes no artigo, quando identificáveis",
        default_factory=list
    )

#===========================================================================================#



from pydantic import BaseModel, Field


# Uma evidência textual extraída do resumo do candidato que sustenta a nota.
class EvidenceSchema(BaseModel):
    quote: str = Field(
        description="Trecho literal do resumo do artigo candidato que sustenta a avaliação."
    )

    relevance: str = Field(
        description="Explicação de como o trecho sustenta a relevância do artigo."
    )


# Um local sugerido no texto original onde a citação caberia ("onde citar").
# page/line/word/paragraph_id são opcionais: hoje o pipeline não envia os
# metadados de localização, então normalmente vêm null.
class CitationLocationSchema(BaseModel):
    page: int | None = Field(
        default=None,
        description="Número da página onde a citação pode ser inserida."
    )

    line: int | None = Field(
        default=None,
        description="Número da linha do texto onde a citação pode ser inserida."
    )

    word: int | None = Field(
        default=None,
        description="Posição da palavra onde a citação pode ser inserida."
    )

    paragraph_id: int | None = Field(
        default=None,
        description="Identificador do parágrafo onde a citação pode ser inserida."
    )

    anchor_quote: str = Field(
        description="Trecho literal do texto original que identifica o local recomendado."
    )

    citation_function: str = Field(
        description=(
            "Função da citação. Deve ser uma das seguintes: "
            "fundamentação teórica, apoio a uma afirmação, "
            "comparação de resultados, justificativa metodológica "
            "ou contextualização do problema."
        )
    )

    reason: str = Field(
        description="Explicação de por que o artigo é pertinente nesse local."
    )


# Schema da 2ª chamada ao Gemini (por candidato): nota de importância +
# justificativa + evidências + sugestões de onde citar.
# NÃO tem campo de chaves livres (dict) de propósito: structured output do
# Gemini rejeita additionalProperties.
class ImportanceAnalysisSchema(BaseModel):
    # Campo lido por Article.calculate_score; o prompt precisa citá-lo com
    # este mesmo nome (importance_score) para não vir zerado.
    importance_score: float = Field(
        description="Pontuação final de importância do artigo, de 0 a 100.",
        ge=0,
        le=100
    )

    h: float = Field(
        description="Meia-vida da área científica do artigo, em anos.",
        gt=0
    )

    base: float = Field(
        description="Média de citações de artigos da mesma área.",
        ge=0
    )

    justification: str = Field(
        description="Justificativa da avaliação de relevância."
    )

    evidence: list[EvidenceSchema] = Field(
        description="Evidências do artigo candidato que sustentam a avaliação.",
        default_factory=list
    )

    uncertainty: str = Field(
        description='Nível de incerteza: "baixa", "média" ou "alta".'
    )

    using: list[CitationLocationSchema] = Field(
        description=(
            "Locais da pesquisa original onde o artigo candidato pode ser "
            "utilizado como citação. Pode conter vários locais ou ser vazia "
            "quando não houver uma localização justificável."
        ),
        default_factory=list
    )
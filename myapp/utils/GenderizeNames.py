# GenderizeNames.py
#
# Estimativa de gênero das autorias a partir dos nomes, usando a lib
# demografix (Genderize.io). Alimenta a métrica de participação feminina
# usada no scoring (Article.calculate_article_genre_compose) e no filtro
# do OpenAlex (filtrar_autoria_feminina).
#
# Estratégia: isolar o PRIMEIRO nome de cada autor (descartando títulos
# acadêmicos) e consultar o serviço, preferindo chamadas em lote (batch).

from typing import List, Dict, Optional, Any

from demografix import Demografix
from demografix.errors import DemografixError

from myapp.config import Config
from myapp.utils.Async import make_async

# Só contamos como "feminino" quando a confiança do serviço é alta o
# suficiente, para reduzir falsos positivos em nomes ambíguos.
FEMALE_PROBABILITY_THRESHOLD = 0.8


def _get_client() -> Demografix:
    # Cliente SÍNCRONO (as versões assíncronas abaixo usam make_async, que
    # roda em thread pool — por isso não usamos o AsyncDemografix).
    api_key = getattr(Config, "DEMOGRAFIX_API_KEY", "") or ""
    if not api_key:
        raise DemografixError(
            "DEMOGRAFIX_API_KEY não configurada no ambiente (.env)."
        )
    return Demografix(api_key=api_key)


# Prefixos de títulos acadêmicos/trato que devem ser ignorados ao achar
# o primeiro nome (ex.: "Dra. Maria Silva" -> "Maria").
_TITLE_PREFIXES = {
    "dr", "dra", "drs", "dras", "prof", "profa", "profº", "profª",
    "me", "msc", "phd", "mestre", "mestra", "sr", "sra", "srta",
}


def _first_name(full_name: str) -> str:
    # Retorna o primeiro token que não seja um título acadêmico.
    if not full_name:
        return ""
    for token in full_name.strip().split():
        cleaned = token.strip(".,").lower()
        if not cleaned or cleaned in _TITLE_PREFIXES:
            continue
        return token.strip(".,")
    return ""


def genderize_name(name: str, country_id: Optional[str] = "BR") -> Dict[str, Any]:
    # Estima o gênero de um único autor. country_id melhora a precisão
    # ajustando a distribuição de nomes por país (padrão: Brasil).
    first = _first_name(name)
    if not first:
        # Sem primeiro nome utilizável: resultado "desconhecido".
        return {"name": name, "gender": None, "probability": 0.0,
                "count": 0, "is_female": False}

    client = _get_client()
    result = client.genderize(first, country_id=country_id)

    return {
        "name": name,
        "gender": result.gender,
        "probability": result.probability,
        "count": result.count,
        # is_female exige gênero feminino E confiança acima do limiar.
        "is_female": result.gender == "female"
        and result.probability >= FEMALE_PROBABILITY_THRESHOLD,
    }


def genderize_names(
    names: List[str], country_id: Optional[str] = "BR"
) -> List[Dict[str, Any]]:
    # Versão em lote: uma única chamada à API para todos os primeiros nomes.
    firsts = [_first_name(n) for n in names]
    valid = [(original, first) for original, first in zip(names, firsts) if first]
    if not valid:
        # Nenhum nome utilizável: devolve tudo como desconhecido.
        return [{"name": n, "gender": None, "probability": 0.0,
                 "count": 0, "is_female": False} for n in names]

    client = _get_client()
    batch = client.genderize_batch([first for _, first in valid], country_id=country_id)

    # Indexa a resposta por primeiro nome (minúsculo) para remapear na ordem
    # original — inclusive nomes repetidos reaproveitam o mesmo resultado.
    by_first: Dict[str, Any] = {r.name.lower(): r for r in batch.results}

    output: List[Dict[str, Any]] = []
    for original, first in zip(names, firsts):
        r = by_first.get(first.lower()) if first else None
        if r is None:
            output.append({"name": original, "gender": None, "probability": 0.0,
                           "count": 0, "is_female": False})
            continue
        output.append({
            "name": original,
            "gender": r.gender,
            "probability": r.probability,
            "count": r.count,
            "is_female": r.gender == "female"
            and r.probability >= FEMALE_PROBABILITY_THRESHOLD,
        })
    return output


def female_authorship_share(authors: List[str], country_id: Optional[str] = "BR") -> int:
    # Atalho: percentual (inteiro) de autoras femininas numa lista de nomes.
    if not authors:
        return 0
    predictions = genderize_names(authors, country_id=country_id)
    female = sum(1 for p in predictions if p["is_female"])
    return round(female / len(authors) * 100)


def analyze_authors(authors: List[str], country_id: Optional[str] = "BR") -> Dict[str, Any]:
    # Relatório completo da composição de gênero de um artigo: contagens e
    # percentuais por categoria + detalhamento por autor. É este dict que
    # vira a chave "genero" de cada candidato no OpenAlex.
    predictions = genderize_names(authors, country_id=country_id)
    total = len(predictions)

    if total == 0:
        # Sem autores: zera tudo para evitar divisão por zero a jusante.
        return {
            "authors": [],
            "total": 0,
            "female_count": 0,
            "male_count": 0,
            "unknown_count": 0,
            "female_percentage": 0.0,
            "male_percentage": 0.0,
            "unknown_percentage": 0.0,
        }

    female_count = sum(1 for p in predictions if p["is_female"])
    male_count = sum(1 for p in predictions if p["gender"] == "male")
    # Desconhecidos = tudo que não entrou com confiança em feminino/masculino.
    unknown_count = total - female_count - male_count

    return {
        "authors": predictions,
        "total": total,
        "female_count": female_count,
        "male_count": male_count,
        "unknown_count": unknown_count,
        "female_percentage": round(female_count / total * 100, 1),
        "male_percentage": round(male_count / total * 100, 1),
        "unknown_percentage": round(unknown_count / total * 100, 1),
    }


# Versões assíncronas (via make_async, executadas em thread pool) para uso
# em contexto não-bloqueante sem reescrever a lógica síncrona acima.
genderize_name_async = make_async(genderize_name)
genderize_names_async = make_async(genderize_names)
female_authorship_share_async = make_async(female_authorship_share)
analyze_authors_async = make_async(analyze_authors)
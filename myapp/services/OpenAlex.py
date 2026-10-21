# OpenAlex.py
#
# Serviço de busca de candidatos a referência no OpenAlex, com integração
# opcional à estimativa de gênero das autorias (util GenderizeNames).
#
# O que faz:
#   - Planeja e executa consultas por tópico (textual e semântica).
#   - Deduplica por OpenAlex ID / DOI e exclui referências já citadas.
#   - Reconstrói o resumo (abstract_inverted_index).
#   - Opcionalmente, estima a composição de gênero das autorias de cada
#     candidato reutilizando myapp.utils.GenderizeNames.analyze_authors.
#
# O que NÃO faz: similaridade entre abstracts, avaliação por IA, ranking final.

import json
import os
import re
import time
import unicodedata

from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen




class AlexService:
    BASE_URL = "https://api.openalex.org/works"

    # Campos escolhidos para alimentar GeminiService e ArticleScoring.
    # O abstract_inverted_index é lido somente dentro de _converter e
    # transformado no campo "abstract" (texto comum).
    CAMPOS_OPENALEX = (
        "id", "doi", "title", "publication_year", "publication_date",
        "authorships", "cited_by_count", "citation_normalized_percentile",
        "fwci", "counts_by_year", "relevance_score", "topics", "keywords",
        "primary_topic", "referenced_works", "related_works",
        "primary_location", "type", "is_retracted", "open_access",
        "best_oa_location",
    )

    def __init__(self, api_key=None, timeout=35):
        # Mantém compatibilidade: usa a key passada, senão a do ambiente.
        # Preferimos a Config do projeto quando disponível.
        if api_key is None:
            try:
                from myapp.config import Config
                api_key = getattr(Config, "OPENALEX_API_KEY", "") or None
            except Exception:
                api_key = None

        self.api_key = api_key or os.getenv("OPENALEX_API_KEY")
        self.timeout = timeout

        self._lock = Lock()
        self._ultima_chamada = 0.0

    def buscar(self, entrada, estimar_genero=False, country_id="BR", preferencias=None):
        """Consulta OpenAlex a partir de ArticleContextSchema (Gemini) ou dict.

        `entrada` possui title, research_objective, research_area, summary,
        topics: [{theme, description, key_words, purpose}] e
        existing_references: [{doi, title, authors, year}].

        `preferencias` é parâmetro opcional separado, pois NÃO existe no
        ArticleContextSchema; permite configurar a busca sem alterar o schema.
        Preserva o formato da saída: status, candidatos, consultas, estatisticas.
        """
        entrada = self._para_dict(entrada)
        if preferencias is None:
            preferencias = entrada.get("preferencias") or {}
        self._validar(entrada, preferencias)
        referencias = [self._para_dict(ref) for ref in entrada.get("existing_references", [])]

        candidatos = []
        consultas_realizadas = []
        indice_ids = {}
        indice_dois = {}
        recuperados = 0
        duplicados = 0
        referencias_excluidas = 0
        descartados_sem_identificacao = 0

        for topico_bruto in entrada["topics"]:
            topico = self._para_dict(topico_bruto)
            consultas = self._planejar_consultas(entrada, topico, preferencias)

            for consulta in consultas:
                registro = {
                    "topico": topico["theme"],
                    "purpose": self._valor_enum(topico.get("purpose")),
                    "modalidade": consulta["modalidade"],
                    "parametro": consulta["parametro"],
                    "texto": consulta["texto"],
                    "consultado_em": self._agora(),
                    "metadados_resposta": None,
                    "recuperados": 0,
                    "erro": None,
                }

                try:
                    resposta = self._consultar(
                        consulta["parametro"], consulta["texto"], preferencias,
                    )
                except (HTTPError, URLError, TimeoutError, OSError, ValueError) as erro:
                    registro["erro"] = self._mensagem_erro(erro)
                    consultas_realizadas.append(registro)
                    continue

                resultados = resposta["results"]
                registro["metadados_resposta"] = deepcopy({
                    chave: valor for chave, valor in resposta.items()
                    if chave != "results"
                })
                registro["recuperados"] = len(resultados)
                consultas_realizadas.append(registro)

                for posicao, item in enumerate(resultados, start=1):
                    recuperados += 1
                    artigo = self._converter(item, topico["theme"], registro["consultado_em"])

                    if self._ja_citado(artigo, referencias):
                        referencias_excluidas += 1
                        continue

                    openalex_id = self._normalizar_id(artigo.get("id"))
                    doi = self._normalizar_doi(artigo.get("doi"))
                    if not openalex_id and not doi:
                        descartados_sem_identificacao += 1
                        continue

                    existente = indice_ids.get(openalex_id) if openalex_id else None
                    if existente is None and doi:
                        existente = indice_dois.get(doi)

                    origem = {
                        "topico": topico["theme"],
                        "purpose": self._valor_enum(topico.get("purpose")),
                        "modalidade": consulta["modalidade"],
                        "consulta": consulta["texto"],
                        "posicao": posicao,
                        "relevance_score": item.get("relevance_score"),
                        "rerank_score": item.get("rerank_score"),
                    }

                    if existente is not None:
                        duplicados += 1
                        if topico["theme"] not in existente["topicos_origem"]:
                            existente["topicos_origem"].append(topico["theme"])
                        existente["origens_busca"].append(origem)
                        if openalex_id:
                            indice_ids[openalex_id] = existente
                        if doi:
                            indice_dois[doi] = existente
                        continue

                    artigo["origens_busca"].append(origem)
                    candidatos.append(artigo)
                    if openalex_id:
                        indice_ids[openalex_id] = artigo
                    if doi:
                        indice_dois[doi] = artigo

        if estimar_genero:
            self._anexar_genero(candidatos, country_id=country_id)

        falhas = sum(registro["erro"] is not None for registro in consultas_realizadas)
        status = (
            "concluido" if falhas == 0 else
            "falhou" if falhas == len(consultas_realizadas) else "parcial"
        )

        return {
            "status": status,
            "gerado_em": self._agora(),
            "candidatos": candidatos,
            "consultas": consultas_realizadas,
            "estatisticas": {
                "consultas_executadas": len(consultas_realizadas),
                "consultas_com_erro": falhas,
                "ocorrencias_recuperadas": recuperados,
                "duplicados_removidos": duplicados,
                "ocorrencias_de_referencias_excluidas": referencias_excluidas,
                "descartados_sem_identificacao": descartados_sem_identificacao,
                "artigos_unicos": len(candidatos),
                "artigos_sem_estimativa_genero": (
                    sum(
                        artigo.get("genero", {}).get("disponivel") is not True
                        for artigo in candidatos
                    ) if estimar_genero else None
                ),
            },
        }

    # ============================================================
    # INTEGRAÇÃO COM O UTIL DE GÊNERO (GenderizeNames)
    # ============================================================

    @staticmethod
    def extrair_autores(item):
        """Extrai os nomes das autorias de um objeto 'work' do OpenAlex.

        Aceita artigos selecionados e objetos brutos com 'authorships'.
        """
        dados = item.get("dados_openalex", item) if isinstance(item, dict) else {}
        autorias = dados.get("authorships") or []

        nomes = []
        for autoria in autorias:
            if not isinstance(autoria, dict):
                continue
            autor = autoria.get("author") or {}
            nome = autor.get("display_name") or autoria.get("raw_author_name")
            if nome and nome.strip():
                nomes.append(nome.strip())
        return nomes

    @staticmethod
    def filtrar_autoria_feminina(
        resultado,
        limite_percentual=50,
        country_id="BR",
        fallback_qtd=5,
        limite_qtd=None,
    ):
        """Filtra o retorno de buscar() priorizando artigos de autoria feminina.

        Recebe o dicionário devolvido por buscar() (com a lista "candidatos")
        e retorna um dicionário com a MESMA estrutura, porém com "candidatos"
        contendo apenas os artigos cuja participação feminina estimada é
        MAIOR que limite_percentual (padrão: > 50%).

        Fallback: se NENHUM artigo atingir o limite, em vez de devolver lista
        vazia, retorna os artigos com maior participação feminina disponível
        (ordenados do maior para o menor percentual), até fallback_qtd itens.
        Passe fallback_qtd=0 para desligar o fallback e permitir lista vazia.

        limite_qtd: número máximo de artigos a retornar. Quando definido, o
        resultado é ordenado pela maior participação feminina e cortado nesse
        total (vale tanto para o caso normal quanto para o fallback). Use None
        (padrão) para não limitar a quantidade.

        Cada candidato mantido conserva os campos selecionados do OpenAlex e
        a chave "genero" (o retorno de GenderizeNames.analyze_authors), que
        inclui a lista de dicionários por autor e as porcentagens.

        Se os candidatos ainda não tiverem a chave "genero" (buscar() chamado
        com estimar_genero=False), a estimativa é calculada aqui, uma vez por
        artigo, reutilizando analyze_authors.
        """
        from copy import deepcopy

        filtrado = deepcopy(resultado)
        candidatos = filtrado.get("candidatos") or []

        analyze_authors = None
        com_genero = []   # artigos com estimativa disponível (passando ou não)
        aprovados = []    # artigos acima do limite

        for artigo in candidatos:
            genero = artigo.get("genero")

            # Calcula a estimativa sob demanda se ela ainda não existe.
            if not isinstance(genero, dict) or not genero.get("disponivel"):
                if analyze_authors is None:
                    try:
                        from myapp.utils.GenderizeNames import analyze_authors
                    except Exception:
                        analyze_authors = False  # marca como indisponível

                if analyze_authors:
                    autores = AlexService.extrair_autores(artigo)
                    try:
                        genero = analyze_authors(autores, country_id=country_id)
                        genero["disponivel"] = True
                        artigo["genero"] = genero
                    except Exception:
                        continue  # sem estimativa confiável: ignora o artigo
                else:
                    continue

            com_genero.append(artigo)

            if genero.get("female_percentage", 0) > limite_percentual:
                aprovados.append(artigo)

        usou_fallback = False

        if aprovados:
            mantidos = aprovados
        elif fallback_qtd and com_genero:
            # Ninguém passou do limite: pega os de maior participação feminina.
            usou_fallback = True
            ordenados = sorted(
                com_genero,
                key=lambda a: a["genero"].get("female_percentage", 0),
                reverse=True,
            )
            mantidos = ordenados[:fallback_qtd]
        else:
            mantidos = []

        # Corte opcional por quantidade: mantém os de maior participação.
        if limite_qtd is not None and len(mantidos) > limite_qtd:
            mantidos = sorted(
                mantidos,
                key=lambda a: a["genero"].get("female_percentage", 0),
                reverse=True,
            )[:limite_qtd]

        filtrado["candidatos"] = mantidos

        estatisticas = filtrado.get("estatisticas")
        if isinstance(estatisticas, dict):
            estatisticas["artigos_unicos"] = len(mantidos)
            estatisticas["artigos_antes_do_filtro_genero"] = len(candidatos)
            estatisticas["artigos_filtrados_por_genero"] = (
                len(candidatos) - len(mantidos)
            )
            estatisticas["limite_percentual_feminino"] = limite_percentual
            estatisticas["aprovados_acima_do_limite"] = len(aprovados)
            estatisticas["usou_fallback_menor_participacao"] = usou_fallback
            estatisticas["limite_qtd_solicitado"] = limite_qtd

        return filtrado

    def _anexar_genero(self, candidatos, country_id="BR"):
        """Para cada candidato, estima a composição de gênero das autorias.

        Reutiliza myapp.utils.GenderizeNames.analyze_authors. Falhas na API de
        gênero NÃO derrubam a busca: o candidato recebe genero com "erro".
        """
        try:
            from myapp.utils.GenderizeNames import analyze_authors
        except Exception as erro:
            for artigo in candidatos:
                artigo["genero"] = {
                    "disponivel": False,
                    "erro": f"GenderizeNames indisponível: {erro}",
                }
            return

        for artigo in candidatos:
            autores = self.extrair_autores(artigo)
            try:
                analise = analyze_authors(autores, country_id=country_id)
                analise["disponivel"] = True
                artigo["genero"] = analise
            except Exception as erro:
                artigo["genero"] = {
                    "disponivel": False,
                    "erro": self._mensagem_erro(erro),
                    "autores": autores,
                }
    def _planejar_consultas(self, entrada, topico, preferencias):
        """Gera buscas a partir de theme, key_words e contexto Gemini.

        Mantém as mesmas modalidades da versão anterior:
        search.title_and_abstract e, opcionalmente, search.semantic.
        """
        tema = topico["theme"].strip()
        palavras = [p.strip() for p in topico.get("key_words", []) if p.strip()]
        expressoes = [tema]
        if palavras:
            alternativa = " ".join(palavras[:2])[:300]
            if alternativa.casefold() != tema.casefold():
                expressoes.append(alternativa)

        consultas = [
            {"modalidade": "textual", "parametro": "search.title_and_abstract", "texto": texto}
            for texto in dict.fromkeys(expressoes)
        ]

        if preferencias.get("busca_semantica", True):
            contexto = (
                f"Tema: {tema}. "
                f"Descrição: {topico.get('description', '')}. "
                f"Finalidade: {self._valor_enum(topico.get('purpose', ''))}. "
                f"Área: {entrada.get('research_area', '')}. "
                f"Objetivo: {entrada['research_objective']}. "
                f"Resumo: {entrada['summary']}"
            )[:900]
            consultas.append({
                "modalidade": "semantica",
                "parametro": "search.semantic",
                "texto": contexto,
            })

        return consultas

    def _consultar(
        self,
        parametro,
        texto,
        preferencias,
    ):
        parametros = {
            parametro: texto,
            "filter": self._montar_filtros(preferencias),
            "per_page": preferencias.get(
                "resultados_por_consulta",
                25,
            ),
        }

        # Intencionalmente sem "select":
        # preserva os campos da resposta padrão do OpenAlex.
        url = f"{self.BASE_URL}?{urlencode(parametros)}"

        if len(url.encode("utf-8")) > 4000:
            raise ValueError(
                "Consulta muito longa. "
                "Reduza a descrição ou expressão de busca."
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": "AlexService/1.0",
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        for tentativa in range(3):
            self._aguardar_limite()

            requisicao = Request(
                url,
                headers=headers,
                method="GET",
            )

            try:
                with urlopen(
                    requisicao,
                    timeout=self.timeout,
                ) as resposta:
                    dados = json.load(resposta)

                if (
                    not isinstance(dados, dict)
                    or not isinstance(dados.get("results"), list)
                    or any(
                        not isinstance(item, dict)
                        for item in dados["results"]
                    )
                ):
                    raise ValueError(
                        "Formato inesperado na resposta do OpenAlex."
                    )

                return dados

            except HTTPError as erro:
                status = erro.code
                retry_after = erro.headers.get(
                    "Retry-After", ""
                )
                erro.close()

                temporario = (
                    status == 429 or status >= 500
                )

                if not temporario or tentativa == 2:
                    raise

                espera = max(
                    2 ** tentativa,
                    self._interpretar_retry_after(retry_after),
                )

                if espera > 30:
                    raise ValueError(
                        "OpenAlex solicitou uma espera longa. "
                        "Reagende a consulta."
                    ) from erro

                time.sleep(espera)

            except (URLError, TimeoutError):
                if tentativa == 2:
                    raise

                time.sleep(2 ** tentativa)

        raise RuntimeError(
            "Não foi possível concluir a consulta."
        )

    @staticmethod
    def _montar_filtros(preferencias):
        filtros = [
            "is_retracted:false",
        ]

        # Padrão do projeto: exigir resumo para permitir
        # a comparação posterior entre abstracts.
        # Pode ser desligado para ampliar a recuperação.
        if preferencias.get("exigir_resumo", True):
            filtros.append("has_abstract:true")

        inicio = preferencias.get("ano_inicial")
        fim = preferencias.get("ano_final")

        if inicio is not None:
            filtros.append(
                f"from_publication_date:{inicio}-01-01"
            )

        if fim is not None:
            filtros.append(
                f"to_publication_date:{fim}-12-31"
            )

        idiomas = preferencias.get("idiomas") or []

        if idiomas:
            filtros.append(
                f"language:{'|'.join(idiomas)}"
            )

        if preferencias.get(
            "somente_acesso_aberto",
            False,
        ):
            filtros.append("open_access.is_oa:true")

        return ",".join(filtros)

    def _converter(self, item, tema, coletado_em):
        """Extrai só os campos selecionados para o serviço de scores.

        O OpenAlex é consultado com o retorno completo, mas os demais campos
        nunca são devolvidos a quem consome este serviço.
        """
        artigo = {campo: deepcopy(item.get(campo)) for campo in self.CAMPOS_OPENALEX}
        artigo["abstract"] = self._reconstruir_resumo(item.get("abstract_inverted_index"))
        artigo["topicos_origem"] = [tema]
        artigo["origens_busca"] = []
        artigo["coletado_em"] = coletado_em
        return artigo

    @staticmethod
    def _reconstruir_resumo(indice):
        if not indice:
            return None

        palavras = {
            posicao: palavra
            for palavra, posicoes in indice.items()
            for posicao in posicoes
        }

        return " ".join(
            palavras[posicao]
            for posicao in sorted(palavras)
        )

    def _ja_citado(self, artigo, referencias):
        """Exclui referências Gemini por DOI, ID ou título e ano.

        Referências de ExistingReference trazem doi, title, authors e year;
        a ausência de DOI não impede identificar títulos já utilizados.
        """
        for ref in referencias:
            referencia = self._para_dict(ref)
            mesmo_id = self._iguais(
                self._normalizar_id(artigo.get("id")),
                self._normalizar_id(referencia.get("id") or referencia.get("openalex_id")),
            )
            if mesmo_id:
                return True

            doi_artigo = self._normalizar_doi(artigo.get("doi"))
            doi_referencia = self._normalizar_doi(referencia.get("doi"))
            if self._iguais(doi_artigo, doi_referencia):
                return True
            if doi_artigo and doi_referencia:
                continue

            titulo_artigo = self._normalizar_titulo(artigo.get("title"))
            titulo_referencia = self._normalizar_titulo(
                referencia.get("title") or referencia.get("titulo")
            )
            anos_compativeis = (
                artigo.get("publication_year") is None
                or (referencia.get("year") or referencia.get("ano")) is None
                or artigo.get("publication_year") == (referencia.get("year") or referencia.get("ano"))
            )
            if self._iguais(titulo_artigo, titulo_referencia) and anos_compativeis:
                return True
        return False

    def _aguardar_limite(self):
        """
        Controle compartilhado pelas threads que usam
        esta instância. Vários processos precisam de
        um controle de taxa externo.
        """
        with self._lock:
            intervalo = (
                time.monotonic() - self._ultima_chamada
            )

            espera = max(0, 1.1 - intervalo)

            if espera:
                time.sleep(espera)

            self._ultima_chamada = time.monotonic()

    @staticmethod
    def _interpretar_retry_after(valor):
        if not valor:
            return 0

        try:
            return max(0, float(valor))
        except ValueError:
            pass

        try:
            data = parsedate_to_datetime(valor)

            if data.tzinfo is None:
                data = data.replace(
                    tzinfo=timezone.utc
                )

            return max(
                0,
                (
                    data - datetime.now(timezone.utc)
                ).total_seconds(),
            )

        except (TypeError, ValueError, OverflowError):
            return 0

    @staticmethod
    def _normalizar_doi(valor):
        return re.sub(
            r"^(https?://(dx\.)?doi\.org/|doi:\s*)",
            "",
            (valor or "").strip().lower(),
        )

    @staticmethod
    def _normalizar_id(valor):
        return re.sub(
            r"^https?://openalex\.org/",
            "",
            (valor or "").strip().lower(),
        )

    @staticmethod
    def _normalizar_titulo(valor):
        texto = unicodedata.normalize(
            "NFKD",
            valor or "",
        )

        texto = "".join(
            caractere
            for caractere in texto
            if not unicodedata.combining(caractere)
        )

        return re.sub(
            r"[\W_]+",
            " ",
            texto.lower(),
        ).strip()

    @staticmethod
    def _iguais(a, b):
        return bool(a and a == b)

    @staticmethod
    def _agora():
        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _mensagem_erro(erro):
        # Não expõe URLs autenticadas nem corpos de erro.
        if isinstance(erro, HTTPError):
            return f"OpenAlex retornou HTTP {erro.code}."

        if isinstance(erro, URLError):
            return "Falha de conexão com o OpenAlex."

        if isinstance(erro, TimeoutError):
            return "Tempo limite da consulta excedido."

        if isinstance(erro, OSError):
            return "Falha de comunicação com o OpenAlex."

        return str(erro)

    @staticmethod
    def _para_dict(valor):
        """Aceita dict ou Pydantic BaseModel sem importar o GeminiSchema."""
        if isinstance(valor, dict):
            return valor
        if hasattr(valor, "model_dump"):
            return valor.model_dump(mode="json")
        raise TypeError("Entrada deve ser ArticleContextSchema (Pydantic) ou dict.")

    @staticmethod
    def _valor_enum(valor):
        return valor.value if hasattr(valor, "value") else valor

    @classmethod
    def _validar(cls, entrada, preferencias=None):
        """Valida o contrato de ArticleContextSchema e opções do OpenAlex."""
        entrada = cls._para_dict(entrada)
        preferencias = preferencias or {}

        for campo in ("title", "summary", "research_objective", "research_area"):
            valor = entrada.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"Gemini: '{campo}' deve ser texto não vazio.")

        topicos = entrada.get("topics")
        if not isinstance(topicos, list) or not 1 <= len(topicos) <= 5:
            raise ValueError("Gemini: 'topics' deve ter entre 1 e 5 tópicos.")

        for topico_bruto in topicos:
            topico = cls._para_dict(topico_bruto)
            tema = topico.get("theme")
            if not isinstance(tema, str) or not 1 <= len(tema.strip()) <= 200:
                raise ValueError("Gemini: 'theme' deve ter de 1 a 200 caracteres.")
            descricao = topico.get("description")
            if descricao is not None and not isinstance(descricao, str):
                raise ValueError("Gemini: 'description' deve ser texto.")
            palavras = topico.get("key_words")
            if (not isinstance(palavras, list) or not palavras
                    or any(not isinstance(p, str) or not p.strip() for p in palavras)):
                raise ValueError("Gemini: 'key_words' deve conter textos não vazios.")
            finalidade = cls._valor_enum(topico.get("purpose"))
            if finalidade not in ("method", "related_works", "theoretical_framework", "context"):
                raise ValueError("Gemini: 'purpose' inválido.")

        referencias = entrada.get("existing_references", [])
        if not isinstance(referencias, list):
            raise ValueError("Gemini: 'existing_references' deve ser lista.")
        for referencia_bruta in referencias:
            ref = cls._para_dict(referencia_bruta)
            if not isinstance(ref.get("title"), str) or not ref["title"].strip():
                raise ValueError("Referência precisa de título.")
            if not isinstance(ref.get("authors"), list) or any(
                not isinstance(nome, str) for nome in ref["authors"]
            ):
                raise ValueError("Referência precisa de lista de autores.")
            if ref.get("doi") is not None and not isinstance(ref["doi"], str):
                raise ValueError("DOI da referência deve ser texto ou None.")
            if ref.get("year") is not None and type(ref["year"]) is not int:
                raise ValueError("Ano da referência precisa ser inteiro ou None.")

        if not isinstance(preferencias, dict):
            raise ValueError("preferencias deve ser um dicionário.")
        quantidade = preferencias.get("resultados_por_consulta", 25)
        if type(quantidade) is not int or not 1 <= quantidade <= 50:
            raise ValueError("resultados_por_consulta deve estar entre 1 e 50.")
        for campo in ("busca_semantica", "exigir_resumo", "somente_acesso_aberto"):
            if campo in preferencias and type(preferencias[campo]) is not bool:
                raise ValueError(f"{campo} deve ser true ou false.")
        idiomas = preferencias.get("idiomas")
        if idiomas is not None and (
            not isinstance(idiomas, list)
            or any(not isinstance(i, str) or not re.fullmatch(r"[a-z]{2}", i) for i in idiomas)
        ):
            raise ValueError("Use idiomas como pt, en ou es.")
        inicio = preferencias.get("ano_inicial")
        fim = preferencias.get("ano_final")
        for ano in (inicio, fim):
            if ano is not None and (type(ano) is not int or not 1000 <= ano <= 9999):
                raise ValueError("Ano de publicação inválido.")
        if inicio is not None and fim is not None and inicio > fim:
            raise ValueError("ano_inicial deve ser menor ou igual a ano_final.")

# ------------------------------------------------------------
# MOCK: simula o ArticleContextSchema retornado pelo Gemini
dados_mock = {
    "title": "Mapa do Brasil em Impressão 3D: Uma Nova Abordagem para o Ensino de Geografia",

    "research_objective": (
        "Investigar como a impressão 3D pode contribuir para "
        "o ensino de geografia e o engajamento dos alunos."
    ),

    "research_area": "Informática na Educação",

    "summary": (
        "Este estudo analisa o uso de mapas tridimensionais "
        "impressos em 3D como recurso pedagógico para alunos "
        "do Ensino Fundamental. A pesquisa utiliza Design Science "
        "Research e avalia o engajamento e a aprendizagem."
    ),

    "topics": [
        {
            "theme": "Impressão 3D na educação",
            "description": (
                "Uso de objetos impressos em 3D como "
                "recursos didáticos na educação básica."
            ),
            "key_words": [
                "3D printing education",
                "educational technology",
                "manufatura aditiva"
            ],
            "purpose": "related_works"
        },
        {
            "theme": "Ensino de cartografia",
            "description": (
                "Uso de mapas e materiais concretos "
                "no ensino de geografia."
            ),
            "key_words": [
                "cartography education",
                "geography teaching",
                "tangible learning"
            ],
            "purpose": "theoretical_framework"
        }
    ],

    "existing_references": [
        {
            "doi": None,
            "title": "Research Design: Qualitative, Quantitative, and Mixed Methods Approaches",
            "authors": ["John W. Creswell"],
            "year": 2014
        }
    ]
}


#========= EXEMPLO ==========

# 1. Simula o objeto Pydantic produzido pelo Gemini.

# MOCK: simula o ArticleContextSchema retornado pelo Gemini
dados_mock = {
    "title": "Mapa do Brasil em Impressão 3D: Uma Nova Abordagem para o Ensino de Geografia",

    "research_objective": (
        "Investigar como a impressão 3D pode contribuir para "
        "o ensino de geografia e o engajamento dos alunos."
    ),

    "research_area": "Informática na Educação",

    "summary": (
        "Este estudo analisa o uso de mapas tridimensionais "
        "impressos em 3D como recurso pedagógico para alunos "
        "do Ensino Fundamental. A pesquisa utiliza Design Science "
        "Research e avalia o engajamento e a aprendizagem."
    ),

    "topics": [
        {
            "theme": "Impressão 3D na educação",
            "description": (
                "Uso de objetos impressos em 3D como "
                "recursos didáticos na educação básica."
            ),
            "key_words": [
                "3D printing education",
                "educational technology",
                "manufatura aditiva"
            ],
            "purpose": "related_works"
        },
        {
            "theme": "Ensino de cartografia",
            "description": (
                "Uso de mapas e materiais concretos "
                "no ensino de geografia."
            ),
            "key_words": [
                "cartography education",
                "geography teaching",
                "tangible learning"
            ],
            "purpose": "theoretical_framework"
        }
    ],

    "existing_references": [
        {
            "doi": None,
            "title": "Research Design: Qualitative, Quantitative, and Mixed Methods Approaches",
            "authors": ["John W. Creswell"],
            "year": 2014
        }
    ]
}

# 2. Instancia o serviço real do OpenAlex.
service = AlexService()

# 3. Executa as buscas reais.
resultado = service.buscar(
    entrada=dados_mock,
    estimar_genero=True,
    country_id="BR",
    preferencias={
        "resultados_por_consulta": 5,
        "busca_semantica": False,
        "exigir_resumo": True,
        "somente_acesso_aberto": False
    }
)

# 4. Mostra estatísticas e consultas realizadas.
print("\n========== ESTATÍSTICAS ==========")
print(json.dumps(
    resultado["estatisticas"],
    indent=2,
    ensure_ascii=False
))

print("\n========== CONSULTAS ==========")
print(json.dumps(
    resultado["consultas"],
    indent=2,
    ensure_ascii=False
))

# 5. Mostra TODOS os campos devolvidos por candidato.
print("\n========== ARTIGOS ==========")

for i, artigo in enumerate(resultado["candidatos"], 1):
    print(f"\n========== ARTIGO {i} ==========")
    print(json.dumps(
        artigo,
        indent=2,
        ensure_ascii=False,
        default=str
    ))

# 6. Mostra um resumo dos principais campos.
print("\n========== RESUMO ==========")

for artigo in resultado["candidatos"]:
    print("\nTítulo:", artigo.get("title"))
    print("DOI:", artigo.get("doi"))
    print("Ano:", artigo.get("publication_year"))
    print("Abstract:", artigo.get("abstract"))
    print("Citações:", artigo.get("cited_by_count"))
    print("Autores:", AlexService.extrair_autores(artigo))
    print("Gênero:", artigo.get("genero"))
    print("-" * 60)
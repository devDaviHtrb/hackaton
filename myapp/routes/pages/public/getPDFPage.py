# getPDFPage.py
#
# Rota POST /pdf/page: ponto de entrada do pipeline acionado pelo frontend
# (CitaDelasRecommend.js) ao enviar o artigo. Orquestra as etapas:
#   upload -> extração de texto -> Gemini -> scoring/OpenAlex/Genderize
# e devolve { source, recommendations } no formato que o front espera.

from flask import render_template, Blueprint, Response, request, jsonify
from myapp.services.Article import calculate_articles_scores
from myapp.services.ExtractTextService import extract_file_text
import myapp.services.GeminiService as geminiService

get_pdf_page_bp = Blueprint("getPdfPage", __name__)


@get_pdf_page_bp.route("/pdf/page", methods=["POST"])
def GetPdfPage() -> Response:
    # O front envia o arquivo no campo multipart "pdf_file".
    pdf_file = request.files.get("pdf_file")

    # Sem arquivo (ou nome vazio): 400 antes de gastar chamadas de API.
    if pdf_file is None or pdf_file.filename == "":
        return jsonify({"error": "Nenhum arquivo foi enviado."}), 400

    """
    ArticleContextSchema
    "all_content": tudo escrito
    """

    # 1) Extrai o texto cru do PDF/TXT.
    all_content = extract_file_text(pdf_file.read(), pdf_file.filename)
    # 2) Gemini estrutura o contexto do artigo (título, tópicos, referências...).
    article_analysis = geminiService.analyze_article(all_content)

    # Empacota texto cru + análise estruturada para o scoring.
    pdf_data = {
        "all_content": all_content,
        "article_analysis": article_analysis,
    }

    # 3) OpenAlex + Genderize + scoring: gera as recomendações ranqueadas.
    recommendations = calculate_articles_scores(pdf_data)

    # Contexto do manuscrito do usuário (para o cabeçalho da página de resultados)
    # Normaliza o schema do Gemini para dict antes de ler os campos.
    analysis = article_analysis
    if hasattr(analysis, "model_dump"):
        analysis = analysis.model_dump(mode="json")
    # Monta o "source" com defaults seguros caso algum campo falte.
    source = {
        "title": analysis.get("title", "") if isinstance(analysis, dict) else "",
        "research_area": analysis.get("research_area", "") if isinstance(analysis, dict) else "",
        "research_objective": analysis.get("research_objective", "") if isinstance(analysis, dict) else "",
        "summary": analysis.get("summary", "") if isinstance(analysis, dict) else "",
    }

    # O front espera { source, recommendations }.
    return jsonify({"source": source, "recommendations": recommendations})
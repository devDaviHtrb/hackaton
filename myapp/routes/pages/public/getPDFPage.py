from flask import render_template, Blueprint, Response, request, jsonify
from myapp.services.Article import calculate_articles_scores
from myapp.services.ExtractTextService import extract_file_text
import myapp.services.GeminiService as geminiService

getPDFPage = Blueprint("getPDFPage", __name__)


@getPDFPage.route("/pdf/page", methods=["GET", "POST"])
def getPDFPage() -> Response:
    pdf_file  = request.args.get("pdf_file")
    """
    ArticleContextSchema
    "all_content": tudo escrito
    """

    pdf_data = {}
    pdf_data["all_context"] = extract_file_text(pdf_file)
    pdf_data = geminiService.analyze_article(pdf_data["all_context"])



    articles_recomendation = calculate_articles_scores(pdf_file)

    return jsonify(articles_recomendation)

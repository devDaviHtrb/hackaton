# CitaDelasPage.py
#
# Rota da página inicial do CitaDelas. Serve "/" renderizando o template de
# envio do artigo. O processamento de verdade acontece na rota POST /pdf/page
# (getPDFPage.py), chamada via fetch a partir desta página.

from flask import render_template, Blueprint, Response

cita_delas_page_bp = Blueprint("citaDelasPage", __name__)


@cita_delas_page_bp.route("/")
def CitaDelasPage() -> Response:
    """Página inicial do CitaDelas: envio do artigo e recomendações."""
    return render_template("CitaDelas.html")
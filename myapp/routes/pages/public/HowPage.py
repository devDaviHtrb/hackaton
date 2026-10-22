from flask import render_template, Blueprint, Response

how_page_bp = Blueprint("howPage", __name__)

@how_page_bp.route("/howPage")
def How():
    return render_template("HowPage.html")
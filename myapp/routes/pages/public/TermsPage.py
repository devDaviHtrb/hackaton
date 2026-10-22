from flask import render_template, Blueprint, Response

terms_page_bp = Blueprint("termsPage", __name__)

@terms_page_bp.route("/termsPage")
def Terms():
    return render_template("TermsPage.html")
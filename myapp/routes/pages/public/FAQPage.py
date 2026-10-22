from flask import render_template, Blueprint, Response

faq_page_bp = Blueprint("faqPage", __name__)

@faq_page_bp.route("/faqPage")
def Faq():
    return render_template("FaqPage.html")
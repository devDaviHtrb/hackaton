from flask import render_template, Blueprint, Response

contact_page_bp = Blueprint("contactPage", __name__)

@contact_page_bp.route("/contactPage")
def Contact():
    return render_template("ContactPage.html")
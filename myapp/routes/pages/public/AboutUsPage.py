from flask import render_template, Blueprint, Response

about_us_page_bp = Blueprint("aboutUsPage", __name__)

@about_us_page_bp.route("/aboutUsPage")
def AboutUs():
    return render_template("AboutUsPage.html")
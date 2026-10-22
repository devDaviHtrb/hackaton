from flask import render_template, Blueprint, Response

services_page_bp = Blueprint("servicesPage", __name__)

@services_page_bp.route("/servicesPage")
def Services():
    return render_template("ServicesPage.html")
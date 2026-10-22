from flask import render_template, Blueprint, Response

loginPage = Blueprint("loginPage", __name__)


@loginPage.route("/loginPage", methods=["GET"])
@loginPage.route("/loginPage/<msg>", methods=["GET"])

def LoginPage(msg: str="") -> Response:
    return render_template("Login.html", message = msg)

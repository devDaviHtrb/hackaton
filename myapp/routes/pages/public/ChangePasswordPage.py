from flask import render_template, Blueprint, Response

change_pass = Blueprint("changePasswordPage", __name__)

@change_pass.route("/change/now")
@change_pass.route("/change/now/<string:token>")
def ChangePasswordPage(token:str = None) -> Response:
    return render_template("ChangePasswordPage.html", token = token)

from flask import render_template, Blueprint, Response, session

signUpPage = Blueprint("signUpPage", __name__)

@signUpPage.route("/signUpPage")
def SignUpPage(msg:str = "") -> Response:
    if("user_id" in session):
        return render_template("Index.html")
    return render_template("SignUp.html", message = msg)

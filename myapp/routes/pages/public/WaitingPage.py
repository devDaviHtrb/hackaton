from flask import Blueprint, render_template, Response

waitingPage = Blueprint("waitingPage", __name__)

@waitingPage.route("/waitingPage")
@waitingPage.route("/waitingPage/<string:link>")
@waitingPage.route("/waitingPage/<string:link>/<string:email>")
def WaitingPage(link: str = "signUpPage.SignUpPage", email: str = None) -> Response:
    return render_template("Waiting.html", link=link, email=email)

from flask import render_template, Blueprint, Response, session, redirect, url_for
import myapp.repositories.UserRepository as user_repository
from myapp.models.Addresses import addresses
from myapp.utils.LinksUrl import LOGIN_PAGE

profile = Blueprint("profilePage", __name__)

@profile.route("/profile")
@profile.route("/profile/<string:username>")
def ProfilePage(username: str = None) -> Response:
    user = None
    if not username:
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for(LOGIN_PAGE))
        user = user_repository.get_by_id(user_id)
    else:
        user = user_repository.get_by_username(username)

    if not user:
        return redirect(url_for(LOGIN_PAGE))

    user_params = {
        "user_id":  user.user_id,
        "username": user.username,
        "name":     user.name,
        "email":    user.email,
        "photo":    user.photo if user.photo else "https://res.cloudinary.com/dnet6nodm/image/upload/v1762029407/Users_photos/xlch6finabqgecvcac6r.png",
        "wallet":   float(user.wallet) if user.wallet is not None else 0.0,
        "admin":    user.admin_user
    }

    user_addresses = addresses.query.filter_by(user_id=user.user_id).all()

    return render_template(
        "Profile.html",
        user_param=user_params,
        addresses=user_addresses
    )

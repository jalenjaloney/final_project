import os
import random

from flask import (
    Flask,
    jsonify,
    send_from_directory,
    request,
    render_template,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object("project.config.Config")
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    active = db.Column(db.Boolean(), default=True, nullable=False)

    def __init__(self, email):
        self.email = email


@app.route("/")
def home():

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    sql = text("""
        SELECT tweets.id_tweets, tweets.text, tweets.created_at,
               tweets.media_filename,
               users.screen_name, users.name
        FROM tweets
        JOIN users ON tweets.id_users = users.id_users
        ORDER BY tweets.created_at DESC
    """)

    result = db.session.execute(sql, {'limit': per_page, 'offset': offset})
    tweets = result.fetchall()

    return render_template("home.html", tweets=tweets, page=page)


@app.route("/static/<path:filename>")
def staticfiles(filename):
    return send_from_directory(app.config["STATIC_FOLDER"], filename)


@app.route("/media/<path:filename>")
def mediafiles(filename):
    return send_from_directory(app.config["MEDIA_FOLDER"], filename)


ALLOWED_EXTENSIONS = {"gif"}


def allowed_file(filename):
    return (
        "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files["file"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["MEDIA_FOLDER"], filename))

    return render_template("upload.html")

import os
import random

from flask import (
    Flask,
    jsonify,
    send_from_directory,
    request,
    render_template,
    session,
    redirect,
    url_for,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object("project.config.Config")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
db = SQLAlchemy(app)


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
        LIMIT :limit OFFSET :offset
    """)

    result = db.session.execute(sql, {'limit': per_page, 'offset': offset})
    tweets = result.fetchall()

    return render_template("home.html", tweets=tweets, page=page)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required")
            return render_template("login.html")

        # Check credentials
        sql = text("""
            SELECT credentials.id_credentials, credentials.id_users,
                   credentials.password, users.screen_name
            FROM credentials
            JOIN users ON credentials.id_users = users.id_users
            WHERE credentials.username = :username
        """)

        result = db.session.execute(sql, {'username': username})
        user = result.fetchone()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id_users
            session['screen_name'] = user.screen_name
            flash(f"Welcome back, @{user.screen_name}!")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out")
    return redirect(url_for('home'))


@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        screen_name = request.form.get("screen_name")
        name = request.form.get("name")

        if not username or not password or not screen_name:
            flash("Username, password, and screen name are required")
            return render_template("create_account.html")

        # Check if username exists
        sql = text("SELECT id_credentials FROM credentials WHERE username = :username")
        result = db.session.execute(sql, {'username': username})
        if result.fetchone():
            flash("Username already exists")
            return render_template("create_account.html")

        # Create user
        try:
            # Insert into users table
            sql = text("""
                INSERT INTO users (screen_name, name, created_at)
                VALUES (:screen_name, :name, NOW())
                RETURNING id_users
            """)
            result = db.session.execute(sql, {
                'screen_name': screen_name,
                'name': name or screen_name
            })
            user_id = result.fetchone()[0]

            # Insert into credentials table
            hashed_password = generate_password_hash(password)
            sql = text("""
                INSERT INTO credentials (id_users, username, password, created_at)
                VALUES (:id_users, :username, :password, NOW())
            """)
            db.session.execute(sql, {
                'id_users': user_id,
                'username': username,
                'password': hashed_password
            })

            db.session.commit()

            # Auto-login
            session['user_id'] = user_id
            session['screen_name'] = screen_name
            flash(f"Account created! Welcome, @{screen_name}!")
            return redirect(url_for('home'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating account: {str(e)}")
            return render_template("create_account.html")

    return render_template("create_account.html")


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

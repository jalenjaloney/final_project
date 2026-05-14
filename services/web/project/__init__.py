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
    make_response,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object("project.config.Config")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
db = SQLAlchemy(app)

# Ensure media folder exists
os.makedirs(app.config["MEDIA_FOLDER"], exist_ok=True)


@app.route("/")
def home():

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    sql = text("""
        SELECT tweets.id_tweets, tweets.text, tweets.created_at,
               tweets.media_filename,
               users.username, users.name
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
                   credentials.password, users.username, users.name
            FROM credentials
            JOIN users ON credentials.id_users = users.id_users
            WHERE credentials.username = :username
        """)

        result = db.session.execute(sql, {'username': username})
        user = result.fetchone()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id_users
            session['username'] = user.username
            session['name'] = user.name
            flash(f"Welcome back, @{user.username}!")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('session', '', expires=0)  # Delete session cookie per stackoverflow
    session.clear()
    flash("You have been logged out")
    return resp


@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")
        name = request.form.get("name")

        if not username or not password or not name:
            flash("Username, password, and display name are required")
            return render_template("create_account.html")

        # Check if passwords match
        if password != password_confirm:
            flash("Passwords do not match")
            return render_template("create_account.html")

        # Check if username exists
        sql = text("SELECT id_users FROM users WHERE username = :username")
        result = db.session.execute(sql, {'username': username})
        if result.fetchone():
            flash("Username already exists")
            return render_template("create_account.html")

        # Create user
        try:
            # Insert into users table
            sql = text("""
                INSERT INTO users (username, name, created_at)
                VALUES (:username, :name, NOW())
                RETURNING id_users
            """)
            result = db.session.execute(sql, {
                'username': username,
                'name': name
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
            session['username'] = username
            session['name'] = name
            flash(f"Account created! Welcome, @{username}!")
            return redirect(url_for('home'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating account: {str(e)}")
            return render_template("create_account.html")

    return render_template("create_account.html")


@app.route("/create_message", methods=["GET", "POST"])
def create_message():
    # Must be logged in
    if not session.get('user_id'):
        flash("You must be logged in to post a message")
        return redirect(url_for('login'))
    
    if request.method == "POST":
        message_text = request.form.get("text")
        
        if not message_text:
            flash("Message cannot be empty")
            return render_template("create_message.html")
        
        # Handle image upload
        media_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to avoid filename collisions
                import time
                timestamp = int(time.time())
                media_filename = f"{timestamp}_{filename}"
                file.save(os.path.join(app.config["MEDIA_FOLDER"], media_filename))
        
        try:
            sql = text("""
                INSERT INTO tweets (id_tweets, id_users, created_at, text, media_filename, text_tokens)
                VALUES (nextval('tweets_id_seq'), :id_users, NOW(), :text, :media_filename, to_tsvector('english', :text))
            """)
            db.session.execute(sql, {
                'id_users': session['user_id'],
                'text': message_text,
                'media_filename': media_filename
            })
            db.session.commit()
            
            flash("Message posted!")
            return redirect(url_for('home'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error posting message: {str(e)}")
            return render_template("create_message.html")
    
    return render_template("create_message.html")


@app.route("/search")
def search():
    query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    tweets = []
    suggestions = []
    
    if query:
        # Full-text search with RUM index using <=> operator for ranking
        sql = text("""
            SELECT tweets.id_tweets, 
                   ts_headline('english', tweets.text, websearch_to_tsquery('english', :query),
                              'StartSel=<mark>, StopSel=</mark>') as highlighted_text,
                   tweets.created_at,
                   tweets.media_filename,
                   users.username, 
                   users.name,
                   tweets.text_tokens <=> websearch_to_tsquery('english', :query) as rank
            FROM tweets
            JOIN users ON tweets.id_users = users.id_users
            WHERE tweets.text_tokens @@ websearch_to_tsquery('english', :query)
            ORDER BY rank ASC, tweets.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = db.session.execute(sql, {
            'query': query,
            'limit': per_page,
            'offset': offset
        })
        tweets = result.fetchall()
        
        # Get spelling suggestions if no results found (EXTRA CREDIT)
        if not tweets:
            # Split query into words and check each for spelling suggestions
            query_words = query.lower().split()
            for word in query_words:
                try:
                    # Use pg_trgm similarity to find close matches
                    suggest_sql = text("""
                        SELECT word, SIMILARITY(word, :word) as sml
                        FROM tweet_words
                        WHERE SIMILARITY(word, :word) > 0.3
                        ORDER BY sml DESC
                        LIMIT 5
                    """)
                    
                    result = db.session.execute(suggest_sql, {'word': word})
                    word_suggestions = result.fetchall()
                    
                    # Only suggest if word isn't an exact match
                    if word_suggestions and word_suggestions[0].sml < 1.0:
                        suggestions.append({
                            'original': word,
                            'suggestions': [s.word for s in word_suggestions]
                        })
                except Exception as e:
                    # tweet_words table or pg_trgm extension might not exist
                    print(f"Spelling suggestion error: {e}")
    
    return render_template("search.html", tweets=tweets, query=query, page=page, suggestions=suggestions)


@app.route("/static/<path:filename>")
def staticfiles(filename):
    return send_from_directory(app.config["STATIC_FOLDER"], filename)


@app.route("/media/<path:filename>")
def mediafiles(filename):
    return send_from_directory(app.config["MEDIA_FOLDER"], filename)


ALLOWED_EXTENSIONS = {"gif", "jpg", "jpeg", "png", "webp"}


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

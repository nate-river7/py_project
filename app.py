from flask import Flask, render_template, request, redirect, url_for, session
import db
from recommender import Recommender, PRESETS

app = Flask(__name__)
app.secret_key = "its_a_secret_shush"

print("Building recommender...")
recommender = Recommender(db.load_movies_df())



def current_pref():
    return session.get("preference", "balanced")


def search_movies(q, limit=20):
    like = f"%{q}%"
    return db.query(
        """SELECT id, title, year, genres FROM movies
           WHERE title LIKE %s OR actors LIKE %s OR genres LIKE %s OR director LIKE %s
           ORDER BY (title LIKE %s) DESC, popularity DESC
           LIMIT %s""",
        (like, like, like, like, like, limit),
    )


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["username"].strip()
        if name:
            db.execute("INSERT IGNORE INTO users (username) VALUES (%s)", (name,))
            user = db.query("SELECT id, preference FROM users WHERE username = %s", (name,))[0]
            session["user_id"] = user["id"]
            session["username"] = name
            session["preference"] = user["preference"]
            return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/preferences", methods=["POST"])
def preferences():
    pref = request.form.get("preference", "balanced")
    if pref in PRESETS and session.get("user_id"):
        db.execute("UPDATE users SET preference = %s WHERE id = %s", (pref, session["user_id"]))
        session["preference"] = pref
    return redirect(url_for("home"))


@app.route("/home")
def home():
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))

    history = db.query(
        """SELECT m.id, m.title, m.year, w.rating
           FROM watch_history w JOIN movies m ON m.id = w.movie_id
           WHERE w.user_id = %s
           ORDER BY w.watched_at DESC""", (uid,))

    recent = db.query(
        "SELECT query FROM search_history WHERE user_id = %s ORDER BY searched_at DESC LIMIT 3",
        (uid,))
    searched_ids = []
    for s in recent:
        searched_ids += [m["id"] for m in search_movies(s["query"], limit=1)]

    recs = recommender.for_user(
        [{"movie_id": h["id"], "rating": h["rating"]} for h in history],
        searched_ids,
        preference=current_pref(),
    )
    return render_template("home.html", watched=history, recs=recs,
                           presets=PRESETS, pref=current_pref())


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = search_movies(q) if q else []
    if q and session.get("user_id"):
        db.execute("INSERT INTO search_history (user_id, query) VALUES (%s, %s)",
                   (session["user_id"], q))
    recs = recommender.similar_to(results[0]["id"], current_pref()) if results else []
    return render_template("search.html", q=q, results=results, recs=recs)


@app.route("/movie/<int:movie_id>")
def movie(movie_id):
    rows = db.query("SELECT * FROM movies WHERE id = %s", (movie_id,))
    if not rows:
        return "Movie not found", 404

    watched, my_rating = False, None
    if session.get("user_id"):
        r = db.query("SELECT rating FROM watch_history WHERE user_id = %s AND movie_id = %s",
                     (session["user_id"], movie_id))
        if r:
            watched, my_rating = True, r[0]["rating"]

    return render_template("movie.html", movie=rows[0], watched=watched, my_rating=my_rating,
                           recs=recommender.similar_to(movie_id, current_pref()))


@app.route("/watch/<int:movie_id>", methods=["POST"])
def watch(movie_id):
    if session.get("user_id"):
        rating = request.form.get("rating", type=int)
        if rating not in (1, 2, 3, 4, 5):
            rating = None
            
        db.execute(
            """INSERT INTO watch_history (user_id, movie_id, rating) VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE rating = COALESCE(VALUES(rating), rating),
                                       watched_at = CURRENT_TIMESTAMP""",
            (session["user_id"], movie_id, rating))
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)

import json
import pandas as pd
import db

MOVIES_CSV = "tmdb_5000_movies.csv"
CREDITS_CSV = "tmdb_5000_credits.csv"
TOP_ACTORS = 5        # how many billed actors to keep per movie
LIMIT = None          # e.g. 1000 to import only the 1000 most popular movies
BATCH_SIZE = 500


def load_json(text):
    
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return []


def names(text, limit=None):
    
    items = load_json(text)[:limit]
    return "|".join(i["name"].replace("|", "/") for i in items)


def top_cast(text, n):
    cast = sorted(load_json(text), key=lambda p: p.get("order", 999))
    return "|".join(p["name"] for p in cast[:n])


def director(text):
    for person in load_json(text):
        if person.get("job") == "Director":
            return person["name"]
    return ""


def main():
    
    movies = pd.read_csv(MOVIES_CSV)
    credits = pd.read_csv(CREDITS_CSV)

    # Join the two files on the movie id
    df = movies.merge(credits[["movie_id", "cast", "crew"]],
                      left_on="id", right_on="movie_id")
    df = df.sort_values("popularity", ascending=False)
    if LIMIT:
        df = df.head(LIMIT)

    rows = []
    for _, r in df.iterrows():
        release = pd.to_datetime(r["release_date"], errors="coerce")
        rows.append((
            int(r["id"]),
            str(r["title"])[:200],
            None if pd.isna(release) else int(release.year),
            names(r["genres"])[:255],
            top_cast(r["cast"], TOP_ACTORS)[:500],
            director(r["crew"])[:200],
            "" if pd.isna(r["overview"]) else str(r["overview"]),
            names(r["keywords"]),
            float(r["popularity"]),
        ))

    print("Clearing old movies and watch history...")
    db.execute("DELETE FROM watch_history")
    db.execute("DELETE FROM movies")

    sql = """INSERT INTO movies
             (id, title, year, genres, actors, director, plot, keywords, popularity)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    for start in range(0, len(rows), BATCH_SIZE):
        db.execute_many(sql, rows[start:start + BATCH_SIZE])
        print(f"  inserted {min(start + BATCH_SIZE, len(rows))}/{len(rows)}")

    print("Done!")


if __name__ == "__main__":
    main()
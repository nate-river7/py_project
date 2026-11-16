import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import normalize


PRESETS = {
    "balanced": {"genres": 0.35, "actors": 0.30, "plot": 0.25, "director": 0.10},
    "actors":   {"genres": 0.20, "actors": 0.55, "plot": 0.15, "director": 0.10},
    "genres":   {"genres": 0.60, "actors": 0.15, "plot": 0.15, "director": 0.10},
    "plot":     {"genres": 0.20, "actors": 0.10, "plot": 0.60, "director": 0.10},
    "director": {"genres": 0.20, "actors": 0.15, "plot": 0.15, "director": 0.50},
}

RATING_WEIGHT = {5: 1.0, 4: 0.85, 3: 0.6}   # 1-2 stars = disliked
UNRATED_WEIGHT = 0.8                         # watched but not rated
SEARCH_WEIGHT = 0.7                          # searched but not watched
DISLIKE_PENALTY = 0.3                        # how hard to push away disliked stuff
POPULARITY_BOOST = 0.2                       # most popular movie gets up to +20%

TEXT_COLS = ["title", "genres", "actors", "director", "plot", "keywords"]


def split_pipe(text):
    
    return [t.strip().lower() for t in text.split("|") if t.strip()]


def clean_year(y):
    return int(y) if pd.notna(y) and y != "" else ""


class Recommender:
    def __init__(self, movies: pd.DataFrame):
        self.df = movies.reset_index(drop=True)
        for col in TEXT_COLS:
            if col not in self.df:
                self.df[col] = ""
            self.df[col] = self.df[col].fillna("")

        self.idx = {int(mid): i for i, mid in enumerate(self.df["id"])}

        
        self.features = {}
        for col in ("genres", "actors", "director"):
            vec = CountVectorizer(tokenizer=split_pipe, token_pattern=None, binary=True)
            self.features[col] = normalize(vec.fit_transform(self.df[col]))

        plot_text = self.df["plot"] + " " + self.df["keywords"].str.replace("|", " ")
        tfidf = TfidfVectorizer(stop_words="english", max_features=20000)
        self.features["plot"] = tfidf.fit_transform(plot_text) 

        self.tags = {col: [{t.strip().lower(): t.strip() for t in v.split("|") if t.strip()}
                           for v in self.df[col]]
                     for col in ("genres", "actors")}

        pop = np.log1p(self.df["popularity"].astype(float).fillna(0).to_numpy())
        self.pop = pop / pop.max() if pop.max() > 0 else pop


    def _sim_rows(self, rows, weights):
        """Similarity of EVERY movie to each movie in `rows`.
        Returns an array of shape (number_of_movies, len(rows))."""
        total = 0
        for col, w in weights.items():
            M = self.features[col]
            total = total + w * (M @ M[rows].T).toarray()
        return total


    def _shared(self, col, a, b):
        """Names that movies a and b have in common, in their original spelling."""
        common = self.tags[col][a].keys() & self.tags[col][b].keys()
        return sorted(self.tags[col][b][k] for k in common)

    def _reasons(self, a, b):
        reasons = []
        genres = self._shared("genres", a, b)
        if genres:
            reasons.append("Genre: " + ", ".join(genres))
        actors = self._shared("actors", a, b)
        if actors:
            reasons.append("Actors: " + ", ".join(actors))
        d = self.df.at[a, "director"]
        if d and d == self.df.at[b, "director"]:
            reasons.append("Director: " + d)
        P = self.features["plot"]
        if P[a].multiply(P[b]).sum() > 0.1:
            reasons.append("Similar plot")
        return reasons


    def _package(self, scores, exclude, sources, source_sims, n, show_because):
        scores = scores.astype(float) * (1 + POPULARITY_BOOST * self.pop)
        if exclude:
            scores[list(exclude)] = -1
        top = np.argsort(-scores)[:n]

        results = []
        for i in top:
            if scores[i] <= 0:
                break
            src = sources[int(np.argmax(source_sims[i]))]
            row = self.df.iloc[i]
            results.append({
                "id": int(row["id"]),
                "title": row["title"],
                "year": clean_year(row["year"]),
                "match": min(100, round(float(scores[i]) * 100)),
                "because": self.df.at[src, "title"] if show_because else None,
                "reasons": self._reasons(src, i),
            })
        return results


    def similar_to(self, movie_id, preference="balanced", n=5):
        if movie_id not in self.idx:
            return []
        i = self.idx[movie_id]
        weights = PRESETS.get(preference, PRESETS["balanced"])
        sims = self._sim_rows([i], weights)
        return self._package(sims[:, 0], {i}, [i], sims, n, show_because=False)

    def for_user(self, history, searched_ids=(), preference="balanced", n=10):
        """history = [{"movie_id": 27205, "rating": 5}, {"movie_id": 155, "rating": None}, ...]"""
        weights = PRESETS.get(preference, PRESETS["balanced"])

        liked, liked_w, disliked = [], [], []
        for h in history:
            i = self.idx.get(h["movie_id"])
            if i is None:
                continue
            r = h["rating"]
            if r is not None and r <= 2:
                disliked.append(i)
            else:
                liked.append(i)
                liked_w.append(RATING_WEIGHT.get(r, UNRATED_WEIGHT))

        for mid in searched_ids:
            i = self.idx.get(mid)
            if i is not None and i not in liked and i not in disliked:
                liked.append(i)
                liked_w.append(SEARCH_WEIGHT)

        if not liked:
            return []


        sims = self._sim_rows(liked, weights) * np.array(liked_w)
        profile = sims.max(axis=1)

        if disliked:
            bad = self._sim_rows(disliked, weights).max(axis=1)
            profile = profile - DISLIKE_PENALTY * bad

        exclude = set(liked) | set(disliked)
        return self._package(profile, exclude, liked, sims, n, show_because=True)
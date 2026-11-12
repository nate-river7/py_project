import mysql.connector
import pandas as pd

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "movie_recs",
}


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=()):
    """Run a SELECT and return a list of dicts."""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE and commit."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    cur.close()
    conn.close()


def execute_many(sql, rows):
    """Insert many rows at once (much faster than a loop of execute)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(sql, rows)
    conn.commit()
    cur.close()
    conn.close()


def load_movies_df():
    """Load the whole movies table into a pandas DataFrame."""
    return pd.DataFrame(query("SELECT * FROM movies"))
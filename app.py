from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
DB_NAME = "database.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            best_dogs INTEGER DEFAULT 0,
            best_time REAL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))

        cursor.execute("INSERT INTO scores (username, best_dogs, best_time) VALUES (?, ?, ?)", (username, 0, 0))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Signup successful"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists"}), 409


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password"], password):
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid username or password"}), 401


@app.route("/highscore/<username>", methods=["GET"])
def get_highscore(username):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT best_dogs, best_time FROM scores WHERE username = ?", (username,))
    score = cursor.fetchone()
    conn.close()

    if score:
        return jsonify({
            "success": True,
            "username": username,
            "best_dogs": score["best_dogs"],
            "best_time": score["best_time"]
        })
    else:
        return jsonify({"success": False, "message": "User not found"}), 404


@app.route("/highscore", methods=["POST"])
def save_highscore():
    data = request.get_json()
    username = data.get("username")
    best_dogs = data.get("best_dogs")
    best_time = data.get("best_time")

    if username is None or best_dogs is None or best_time is None:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT best_dogs, best_time FROM scores WHERE username = ?", (username,))
    existing = cursor.fetchone()

    if not existing:
        conn.close()
        return jsonify({"success": False, "message": "User not found"}), 404

    current_best_dogs = existing["best_dogs"]
    current_best_time = existing["best_time"]

    new_best_dogs = current_best_dogs
    new_best_time = current_best_time

    if best_dogs > current_best_dogs:
        new_best_dogs = best_dogs

    if current_best_time == 0 or (best_time > 0 and best_time < current_best_time):
        new_best_time = best_time

    cursor.execute(
        "UPDATE scores SET best_dogs = ?, best_time = ? WHERE username = ?",
        (new_best_dogs, new_best_time, username)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Highscore saved",
        "best_dogs": new_best_dogs,
        "best_time": new_best_time
    })

@app.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, best_dogs, best_time
        FROM scores
        ORDER BY best_dogs DESC, best_time ASC
        LIMIT 5
    """)

    rows = cursor.fetchall()
    conn.close()

    leaderboard = []
    for row in rows:
        leaderboard.append({
            "username": row["username"],
            "best_dogs": row["best_dogs"],
            "best_time": row["best_time"]
        })

    return jsonify({
        "success": True,
        "leaderboard": leaderboard
    })

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)
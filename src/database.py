"""
Database module for SQLite backend with user authentication and decision storage.
"""

import hashlib
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

# Database file path
DB_FILE = "decisions.db"


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def init_database():
    """Initialize database with tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Decisions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            datetime TEXT NOT NULL,
            winner TEXT NOT NULL,
            winner_score REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )

    # Options table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            option_name TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decisions(id)
        )
    """
    )

    # Criteria table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            criterion TEXT NOT NULL,
            weight REAL NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decisions(id)
        )
    """
    )

    # Scores table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            option_id INTEGER NOT NULL,
            criterion_id INTEGER NOT NULL,
            score REAL NOT NULL,
            FOREIGN KEY (option_id) REFERENCES options(id),
            FOREIGN KEY (criterion_id) REFERENCES criteria(id)
        )
    """
    )

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str) -> Optional[int]:
    """Create a new user. Returns user_id if successful, None otherwise."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        # Username already exists
        return None
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[int]:
    """Authenticate user. Returns user_id if successful, None otherwise."""
    conn = get_db_connection()
    cursor = conn.cursor()

    password_hash = hash_password(password)
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash),
    )
    result = cursor.fetchone()
    user_id = result["id"] if result else None
    conn.close()

    return user_id


def save_decision(
    user_id: int,
    decision: str,
    options: List[str],
    criteria: List[str],
    weights: List[float],
    scores: Dict[str, Dict[str, float]],
    winner: str,
    winner_score: float,
) -> int:
    """Save a decision to the database. Returns decision_id."""
    conn = get_db_connection()
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%b %d, %Y")
    datetime_str = datetime.now().isoformat()

    # Insert decision
    cursor.execute(
        """
        INSERT INTO decisions (user_id, decision, timestamp, datetime, winner, winner_score)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (user_id, decision, timestamp, datetime_str, winner, winner_score),
    )
    decision_id = cursor.lastrowid

    # Insert options
    option_ids = {}
    for option in options:
        cursor.execute(
            "INSERT INTO options (decision_id, option_name) VALUES (?, ?)",
            (decision_id, option),
        )
        option_ids[option] = cursor.lastrowid

    # Insert criteria
    criterion_ids = {}
    for criterion, weight in zip(criteria, weights):
        cursor.execute(
            "INSERT INTO criteria (decision_id, criterion, weight) VALUES (?, ?, ?)",
            (decision_id, criterion, weight),
        )
        criterion_ids[criterion] = cursor.lastrowid

    # Insert scores
    for option, criterion_scores in scores.items():
        option_id = option_ids[option]
        for criterion, score in criterion_scores.items():
            criterion_id = criterion_ids[criterion]
            cursor.execute(
                "INSERT INTO scores (option_id, criterion_id, score) VALUES (?, ?, ?)",
                (option_id, criterion_id, score),
            )

    conn.commit()
    conn.close()
    return decision_id


def get_user_decisions(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Get user's decisions. Returns list of decision dictionaries."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, decision, timestamp, datetime, winner, winner_score
        FROM decisions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """,
        (user_id, limit),
    )

    decisions = []
    for row in cursor.fetchall():
        decision_id = row["id"]
        decision_data = {
            "id": decision_id,
            "decision": row["decision"],
            "timestamp": row["timestamp"],
            "datetime": row["datetime"],
            "winner": row["winner"],
            "winner_score": row["winner_score"],
        }

        # Get options
        cursor.execute(
            "SELECT option_name FROM options WHERE decision_id = ?", (decision_id,)
        )
        decision_data["options"] = [
            opt_row["option_name"] for opt_row in cursor.fetchall()
        ]

        # Get criteria and weights
        cursor.execute(
            "SELECT criterion, weight FROM criteria WHERE decision_id = ?",
            (decision_id,),
        )
        criteria_data = cursor.fetchall()
        decision_data["criteria"] = [
            crit_row["criterion"] for crit_row in criteria_data
        ]
        decision_data["weights"] = [crit_row["weight"] for crit_row in criteria_data]

        # Get scores
        cursor.execute(
            """
            SELECT o.option_name, c.criterion, s.score
            FROM scores s
            JOIN options o ON s.option_id = o.id
            JOIN criteria c ON s.criterion_id = c.id
            WHERE o.decision_id = ?
        """,
            (decision_id,),
        )
        scores = {}
        for score_row in cursor.fetchall():
            option = score_row["option_name"]
            criterion = score_row["criterion"]
            score = score_row["score"]
            if option not in scores:
                scores[option] = {}
            scores[option][criterion] = score
        decision_data["scores"] = scores

        # Reconstruct full_results for compatibility
        decision_data["full_results"] = _reconstruct_full_results(decision_data)

        decisions.append(decision_data)

    conn.close()
    return decisions


def _reconstruct_full_results(decision_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reconstruct full_results DataFrame-like structure from database data."""
    results = []
    for option in decision_data["options"]:
        result = {"Option": option}
        for criterion in decision_data["criteria"]:
            score = decision_data["scores"].get(option, {}).get(criterion, 5.0)
            result[f"{criterion} (1-10)"] = score
        results.append(result)
    return results


def get_decision_by_id(decision_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific decision by ID. Returns None if not found or not owned by user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, decision, timestamp, datetime, winner, winner_score
        FROM decisions
        WHERE id = ? AND user_id = ?
    """,
        (decision_id, user_id),
    )

    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    decision_data = {
        "id": row["id"],
        "decision": row["decision"],
        "timestamp": row["timestamp"],
        "datetime": row["datetime"],
        "winner": row["winner"],
        "winner_score": row["winner_score"],
    }

    # Get options
    cursor.execute(
        "SELECT option_name FROM options WHERE decision_id = ?", (decision_id,)
    )
    decision_data["options"] = [opt_row["option_name"] for opt_row in cursor.fetchall()]

    # Get criteria and weights
    cursor.execute(
        "SELECT criterion, weight FROM criteria WHERE decision_id = ?", (decision_id,)
    )
    criteria_data = cursor.fetchall()
    decision_data["criteria"] = [crit_row["criterion"] for crit_row in criteria_data]
    decision_data["weights"] = [crit_row["weight"] for crit_row in criteria_data]

    # Get scores
    cursor.execute(
        """
        SELECT o.option_name, c.criterion, s.score
        FROM scores s
        JOIN options o ON s.option_id = o.id
        JOIN criteria c ON s.criterion_id = c.id
        WHERE o.decision_id = ?
    """,
        (decision_id,),
    )
    scores = {}
    for score_row in cursor.fetchall():
        option = score_row["option_name"]
        criterion = score_row["criterion"]
        score = score_row["score"]
        if option not in scores:
            scores[option] = {}
        scores[option][criterion] = score
    decision_data["scores"] = scores

    # Reconstruct full_results
    decision_data["full_results"] = _reconstruct_full_results(decision_data)

    conn.close()
    return decision_data


def delete_decision(decision_id: int, user_id: int) -> bool:
    """Delete a decision. Returns True if successful, False otherwise."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if decision exists and belongs to user
    cursor.execute(
        "SELECT id FROM decisions WHERE id = ? AND user_id = ?", (decision_id, user_id)
    )
    if not cursor.fetchone():
        conn.close()
        return False

    # Delete scores (cascade)
    cursor.execute(
        """
        DELETE FROM scores
        WHERE option_id IN (SELECT id FROM options WHERE decision_id = ?)
    """,
        (decision_id,),
    )

    # Delete options
    cursor.execute("DELETE FROM options WHERE decision_id = ?", (decision_id,))

    # Delete criteria
    cursor.execute("DELETE FROM criteria WHERE decision_id = ?", (decision_id,))

    # Delete decision
    cursor.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))

    conn.commit()
    conn.close()
    return True

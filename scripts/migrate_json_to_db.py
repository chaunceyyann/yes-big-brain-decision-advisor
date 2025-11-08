"""
Migration script to migrate decisions from JSON file to SQLite database.
This script creates a default user and migrates all decisions to that user.
"""

import json
import os
import sys
from pathlib import Path

# Add src directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import (create_user, get_db_connection, init_database,
                      save_decision)

# Database and JSON file paths
DB_FILE = "decisions.db"
JSON_FILE = "decisions.json"


def migrate_json_to_db():
    """Migrate decisions from JSON file to SQLite database."""
    # Initialize database
    init_database()

    # Check if JSON file exists
    if not os.path.exists(JSON_FILE):
        print(f"❌ {JSON_FILE} not found. Nothing to migrate.")
        return

    # Load JSON data
    try:
        with open(JSON_FILE, "r") as f:
            decisions_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Error reading {JSON_FILE}: {e}")
        return

    if not decisions_data:
        print(f"ℹ️  {JSON_FILE} is empty. Nothing to migrate.")
        return

    # Create default user for migration
    default_username = "migrated_user"
    default_password = "migrated_password_change_me"

    # Check if user already exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (default_username,))
    existing_user = cursor.fetchone()
    conn.close()

    if existing_user:
        user_id = existing_user["id"]
        print(f"ℹ️  Using existing user: {default_username} (ID: {user_id})")
    else:
        user_id = create_user(default_username, default_password)
        if user_id:
            print(f"✅ Created default user: {default_username} (ID: {user_id})")
            print(f"⚠️  Default password: {default_password}")
            print(f"⚠️  Please change the password after migration!")
        else:
            print(f"❌ Failed to create default user")
            return

    # Migrate each decision
    migrated_count = 0
    skipped_count = 0

    for decision_data in decisions_data:
        try:
            # Extract data from JSON format
            decision = decision_data.get("decision", "")
            options = decision_data.get("options", [])
            criteria = decision_data.get("criteria", [])
            weights = decision_data.get("weights", [])
            winner = decision_data.get("winner", "")
            winner_score = decision_data.get("winner_score", 0.0)

            # Reconstruct scores from full_results
            full_results = decision_data.get("full_results", [])
            scores_dict = {}
            for result in full_results:
                option = result.get("Option", "")
                if not option:
                    continue
                scores_dict[option] = {}
                for criterion in criteria:
                    score_key = f"{criterion} (1-10)"
                    score = result.get(score_key, 5.0)
                    scores_dict[option][criterion] = float(score)

            # Save to database
            decision_id = save_decision(
                user_id=user_id,
                decision=decision,
                options=options,
                criteria=criteria,
                weights=weights,
                scores=scores_dict,
                winner=winner,
                winner_score=winner_score,
            )

            migrated_count += 1
            print(f"✅ Migrated: {decision} (ID: {decision_id})")

        except Exception as e:
            skipped_count += 1
            print(f"⚠️  Skipped decision: {e}")

    print(f"\n📊 Migration Summary:")
    print(f"   ✅ Migrated: {migrated_count} decisions")
    print(f"   ⚠️  Skipped: {skipped_count} decisions")
    print(f"   👤 User: {default_username} (ID: {user_id})")
    print(f"\n💡 Next steps:")
    print(f"   1. Log in with username: {default_username}")
    print(f"   2. Password: {default_password}")
    print(f"   3. Change your password after logging in")
    print(f"   4. Consider backing up {JSON_FILE} before deleting it")


if __name__ == "__main__":
    migrate_json_to_db()

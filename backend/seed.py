"""Reset the database to the business data in data/: uv run -m backend.seed"""

from backend import db

if __name__ == "__main__":
    db.reset()
    print(f"Seeded {db.path()}")

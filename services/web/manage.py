from flask.cli import FlaskGroup
from sqlalchemy import text

from project import app, db


cli = FlaskGroup(app)


@cli.command("populate_words")
def populate_words():
    """Populate tweet_words table for spelling suggestions (extra credit)"""
    try:
        print("Populating tweet_words table for spelling suggestions...")

        # Extract unique words from all tweets using ts_stat
        sql = text("""
            INSERT INTO tweet_words (word)
            SELECT DISTINCT word
            FROM ts_stat('SELECT text_tokens FROM tweets')
            ON CONFLICT (word) DO NOTHING
        """)

        db.session.execute(sql)
        db.session.commit()

        # Count words added
        count_sql = text("SELECT COUNT(*) FROM tweet_words")
        result = db.session.execute(count_sql)
        count = result.scalar()

        print(f"✓ Successfully populated tweet_words table with {count} unique words")
        print("✓ Spelling suggestions are now enabled for search!")

    except Exception as e:
        db.session.rollback()
        print(f"✗ Error populating tweet_words: {e}")
        print("Make sure:")
        print("  1. pg_trgm extension is installed")
        print("  2. tweet_words table exists in schema")
        print("  3. Tweets have been loaded")


if __name__ == "__main__":
    cli()

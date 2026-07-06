"""Show the live database structure — tables, columns, rows, indexes."""
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

import sqlalchemy as sa  # noqa: E402

engine = sa.create_engine(os.getenv("DATABASE_URL_SYNC"))

with engine.connect() as conn:
    print("\n=== TABLES ===")
    tables = conn.execute(sa.text("""
        SELECT table_name,
               (SELECT count(*) FROM information_schema.columns c
                WHERE c.table_name = t.table_name AND c.table_schema='public') as col_count
        FROM information_schema.tables t
        WHERE table_schema='public' AND table_type='BASE TABLE'
        ORDER BY table_name
    """)).fetchall()
    for t, c in tables:
        try:
            n = conn.execute(sa.text(f'SELECT count(*) FROM "{t}"')).scalar()
        except Exception:
            n = "?"
        print(f"  {t:30}  {c:3} cols   {n:>6} rows")

    print("\n=== EXTENSIONS ===")
    exts = conn.execute(sa.text("SELECT extname, extversion FROM pg_extension ORDER BY extname")).fetchall()
    for e, v in exts:
        print(f"  {e:20} v{v}")

    print("\n=== INDEXES (geo/perf) ===")
    idx = conn.execute(sa.text("""
        SELECT tablename, indexname FROM pg_indexes
        WHERE schemaname='public'
          AND (indexname LIKE '%gist%' OR indexname LIKE '%location%' OR indexname LIKE '%idx%')
        ORDER BY tablename, indexname
    """)).fetchall()
    for t, i in idx:
        print(f"  {t:25} {i}")

    print("\n=== ALEMBIC VERSION ===")
    v = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    print(f"  Current: {v}")

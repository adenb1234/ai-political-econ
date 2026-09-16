# Schema

- `events.sql` — discrete events spine
- `panel.sql` — place × month panel

Python mirrors: `src/schema/types.py`.

Apply with any SQL engine that accepts the dialect (SQLite-friendly CHECKs; swap `TIMESTAMPTZ` for `TEXT` if needed on strict SQLite).

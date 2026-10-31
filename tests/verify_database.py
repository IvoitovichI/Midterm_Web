"""Run via Get-Content -Raw tests/verify_database.py | docker compose exec -T backend python -.

Uses the real database; invalid writes are rolled back to savepoints.
"""
from app import connect, initialize_database
from pathlib import Path
import psycopg


def snapshot():
    with connect() as db:
        return {table: db.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
                for table in ('wanted_criminals', 'hunt_logs')}


before = snapshot()
assert len(before['wanted_criminals']) >= 5
assert len(before['hunt_logs']) >= 10
initialize_database()
assert snapshot() == before, 'Migration changed existing data on second startup'
print('PASS: >=5 criminals, >=10 logs; initialization is idempotent')

# Import into an isolated, empty schema, then roll everything back.
with connect() as db:
    db.execute('CREATE SCHEMA midterm_import_verification')
    db.execute('SET LOCAL search_path TO midterm_import_verification')
    for filename in ('schema.sql', 'seed.sql'):
        db.execute((Path('/app/database') / filename).read_text(encoding='utf-8'))
    assert db.execute('SELECT COUNT(*) AS count FROM wanted_criminals').fetchone()['count'] == 5
    assert db.execute('SELECT COUNT(*) AS count FROM hunt_logs').fetchone()['count'] == 10
    db.execute(Path('/app/database/seed.sql').read_text(encoding='utf-8'))
    assert db.execute('SELECT COUNT(*) AS count FROM hunt_logs').fetchone()['count'] == 10
    db.rollback()
print('PASS: clean SQL import creates 5 criminals and 10 logs; repeated seed does not duplicate data')

checks = [
    ('foreign key', "INSERT INTO hunt_logs(criminal_id,success,notes) VALUES (9223372036854775807,false,'test')", psycopg.errors.ForeignKeyViolation),
    ('difficulty range', 'UPDATE wanted_criminals SET difficulty=11 WHERE id=%s', psycopg.errors.CheckViolation),
    ('nonnegative reward', 'UPDATE wanted_criminals SET reward=-1 WHERE id=%s', psycopg.errors.CheckViolation),
    ('finite reward', "UPDATE wanted_criminals SET reward='NaN' WHERE id=%s", psycopg.errors.CheckViolation),
    ('coordinate range', 'UPDATE wanted_criminals SET latitude=91 WHERE id=%s', psycopg.errors.CheckViolation),
    ('location required', 'UPDATE wanted_criminals SET latitude=NULL,longitude=NULL,location_note=NULL WHERE id=%s', psycopg.errors.CheckViolation),
    ('coordinate pair required', 'UPDATE wanted_criminals SET latitude=1,longitude=NULL,location_note=NULL WHERE id=%s', psycopg.errors.CheckViolation),
    ('location note nonblank', "UPDATE wanted_criminals SET latitude=NULL,longitude=NULL,location_note=' ' WHERE id=%s", psycopg.errors.CheckViolation),
    ('restrict criminal deletion', 'DELETE FROM wanted_criminals WHERE id=%s', psycopg.errors.ForeignKeyViolation),
]
with connect() as db:
    criminal_id = before['wanted_criminals'][0]['id']
    for label, sql, expected in checks:
        db.execute('SAVEPOINT validation_check')
        try:
            db.execute(sql, (criminal_id,) if '%s' in sql else None)
        except expected:
            print(f'PASS: database enforces {label}')
        else:
            raise AssertionError(f'Database did not enforce {label}')
        finally:
            db.execute('ROLLBACK TO SAVEPOINT validation_check')
    # A server generated timestamp falls inside the transaction's clock interval.
    start = db.execute('SELECT CURRENT_TIMESTAMP AS now').fetchone()['now']
    row = db.execute("INSERT INTO hunt_logs(criminal_id,success,notes) VALUES (%s,false,'timestamp check') RETURNING *", (criminal_id,)).fetchone()
    assert row['created_at'] == start
    db.rollback()
assert snapshot() == before
print('PASS: database generates timestamp; all verification writes rolled back')

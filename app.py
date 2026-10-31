"""Space bounty REST API: Flask + psycopg + PostgreSQL."""
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=32768)
app.url_map.strict_slashes = False
MAX_ID = 9223372036854775807


def connect():
    return psycopg.connect(
        host=os.getenv('DB_HOST', 'localhost'), port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'space_bounty'), user=os.getenv('DB_USER', 'bounty'),
        password=os.getenv('DB_PASSWORD', 'bounty_local_dev'), connect_timeout=3,
        options='-c statement_timeout=5000 -c timezone=UTC', row_factory=dict_row,
    )


def initialize_database():
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(73103101)')
        for name in ('schema.sql', 'seed.sql'):
            db.execute((Path(__file__).parent / 'database' / name).read_text(encoding='utf-8'))


def serialize(value):
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    return value


def respond(value, status=200):
    return jsonify(serialize(value)), status


class ValidationError(ValueError):
    pass


@app.errorhandler(ValidationError)
def invalid_data(error):
    return respond({'error': str(error)}, 400)


@app.errorhandler(HTTPException)
def http_error(error):
    return respond({'error': error.description}, error.code)


@app.errorhandler(psycopg.errors.ForeignKeyViolation)
def invalid_foreign_key(error):
    return respond({'error': 'criminal_id must reference an existing criminal'}, 400)


@app.errorhandler(psycopg.Error)
def database_error(error):
    app.logger.exception('Database operation failed')
    return respond({'error': 'Database temporarily unavailable'}, 503)


def positive_id(value, field='id'):
    if isinstance(value, str):
        if not re.fullmatch(r'[0-9]{1,19}', value):
            raise ValidationError(f'{field} must be a positive 64-bit integer')
        value = int(value)
    if type(value) is not int or not 1 <= value <= MAX_ID:
        raise ValidationError(f'{field} must be a positive 64-bit integer')
    return value


def query_parameters(allowed):
    for key in request.args:
        if key not in allowed:
            raise ValidationError(f'Unknown query parameter: {key}')
        if len(request.args.getlist(key)) != 1:
            raise ValidationError(f'Duplicate query parameter: {key}')


def reward_parameter(name):
    raw = request.args[name]
    if len(raw) > 32:
        raise ValidationError(f'{name} must be a non-negative amount with at most 2 decimal places')
    try:
        value = Decimal(raw)
        valid = value.is_finite() and 0 <= value <= Decimal('999999999999.99') and value == value.quantize(Decimal('0.01'))
    except InvalidOperation:
        valid = False
    if not valid:
        raise ValidationError(f'{name} must be a non-negative amount with at most 2 decimal places')
    return value


def json_body(allowed, required=()):
    body = request.get_json()  # Flask returns 400 for malformed JSON and 415 for wrong media type.
    if not isinstance(body, dict):
        raise ValidationError('JSON body must be an object')
    unknown = body.keys() - set(allowed)
    if unknown:
        raise ValidationError('Unknown or read-only fields: ' + ', '.join(sorted(unknown)))
    missing = set(required) - body.keys()
    if missing:
        raise ValidationError('Missing fields: ' + ', '.join(sorted(missing)))
    if not body:
        raise ValidationError('At least one field is required')
    if 'success' in body and type(body['success']) is not bool:
        raise ValidationError('success must be a boolean')
    if 'notes' in body:
        if not isinstance(body['notes'], str) or not 1 <= len(body['notes'].strip()) <= 10000:
            raise ValidationError('notes must contain 1 to 10000 non-blank characters')
        body['notes'] = body['notes'].strip()
    if 'criminal_id' in body:
        if type(body['criminal_id']) is not int:
            raise ValidationError('criminal_id must be a JSON integer')
        body['criminal_id'] = positive_id(body['criminal_id'], 'criminal_id')
    return body


@app.get('/health')
def health():
    with connect() as db:
        db.execute('SELECT 1')
    return respond({'status': 'healthy', 'database': 'connected'})


@app.get('/api/criminals/')
def list_criminals():
    query_parameters({'min_reward', 'max_reward', 'armed', 'has_crew', 'escape_master', 'sort'})
    clauses, values = [], []
    minimum = reward_parameter('min_reward') if 'min_reward' in request.args else None
    maximum = reward_parameter('max_reward') if 'max_reward' in request.args else None
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValidationError('min_reward must not exceed max_reward')
    for value, operator in ((minimum, '>='), (maximum, '<=')):
        if value is not None:
            clauses.append(sql.SQL('reward {} %s').format(sql.SQL(operator)))
            values.append(value)
    for name in ('armed', 'has_crew', 'escape_master'):
        if name in request.args:
            raw = request.args[name].lower()
            if raw not in ('true', 'false'):
                raise ValidationError(f'{name} must be true or false')
            clauses.append(sql.SQL('{} = %s').format(sql.Identifier(name)))
            values.append(raw == 'true')
    sort = request.args.get('sort')
    ordering = {None: 'id ASC', 'reward': 'reward ASC, id ASC', '-reward': 'reward DESC, id ASC'}
    if sort not in ordering:
        raise ValidationError('sort must be reward or -reward')
    statement = sql.SQL('SELECT * FROM wanted_criminals')
    if clauses:
        statement += sql.SQL(' WHERE ') + sql.SQL(' AND ').join(clauses)
    statement += sql.SQL(' ORDER BY ') + sql.SQL(ordering[sort])
    with connect() as db:
        rows = db.execute(statement, values).fetchall()
    return respond(rows)


@app.get('/api/criminals/<criminal_id>/')
def criminal_details(criminal_id):
    criminal_id = positive_id(criminal_id)
    with connect() as db:
        row = db.execute('SELECT * FROM wanted_criminals WHERE id = %s', (criminal_id,)).fetchone()
    return respond(row) if row else respond({'error': 'Criminal not found'}, 404)


@app.get('/api/hunts/')
def list_hunts():
    query_parameters({'criminal_id'})
    statement = 'SELECT * FROM hunt_logs'
    values = ()
    if 'criminal_id' in request.args:
        statement += ' WHERE criminal_id = %s'
        values = (positive_id(request.args['criminal_id'], 'criminal_id'),)
    with connect() as db:
        rows = db.execute(statement + ' ORDER BY created_at DESC, id DESC', values).fetchall()
    return respond(rows)


@app.get('/api/hunts/<hunt_id>/')
def hunt_details(hunt_id):
    hunt_id = positive_id(hunt_id)
    with connect() as db:
        row = db.execute('SELECT * FROM hunt_logs WHERE id = %s', (hunt_id,)).fetchone()
    return respond(row) if row else respond({'error': 'Hunt log not found'}, 404)


@app.post('/api/hunts/')
def create_hunt():
    fields = ('criminal_id', 'success', 'notes')
    body = json_body(fields, required=fields)
    with connect() as db:
        row = db.execute(
            'INSERT INTO hunt_logs (criminal_id, success, notes) VALUES (%s, %s, %s) RETURNING *',
            tuple(body[key] for key in fields),
        ).fetchone()
    response, status = respond(row, 201)
    response.headers['Location'] = f"/api/hunts/{row['id']}/"
    return response, status


@app.patch('/api/hunts/<hunt_id>/')
def update_hunt(hunt_id):
    hunt_id = positive_id(hunt_id)
    body = json_body(('success', 'notes'))
    assignments = sql.SQL(', ').join(sql.SQL('{} = %s').format(sql.Identifier(key)) for key in body)
    with connect() as db:
        row = db.execute(
            sql.SQL('UPDATE hunt_logs SET {} WHERE id = %s RETURNING *').format(assignments),
            (*body.values(), hunt_id),
        ).fetchone()
    return respond(row) if row else respond({'error': 'Hunt log not found'}, 404)


@app.delete('/api/hunts/<hunt_id>/')
def delete_hunt(hunt_id):
    hunt_id = positive_id(hunt_id)
    with connect() as db:
        row = db.execute('DELETE FROM hunt_logs WHERE id = %s RETURNING id', (hunt_id,)).fetchone()
    return ('', 204) if row else respond({'error': 'Hunt log not found'}, 404)


if __name__ == '__main__':
    initialize_database()
    if '--init-db' not in sys.argv:
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', '8080')))

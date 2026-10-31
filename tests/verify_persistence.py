"""Exercise persistence on the running Compose project, preserving existing logs."""
import json
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'http://localhost:8081'


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    with urlopen(Request(BASE_URL + path, data=data, method=method,
                         headers={'Content-Type': 'application/json'}), timeout=10) as response:
        payload = response.read()
        return json.loads(payload) if payload else None


before = request('GET', '/api/hunts/')
criminal = request('GET', '/api/criminals/')[0]
created = request('POST', '/api/hunts/', {
    'criminal_id': criminal['id'], 'success': False, 'notes': 'Persistence verification temporary entry',
})
try:
    # Replace both containers, keeping the project's named PostgreSQL volume.
    subprocess.run(['docker', 'compose', 'up', '-d', '--force-recreate', '--wait'], cwd=ROOT, check=True)
    assert request('GET', f"/api/hunts/{created['id']}/") == created
    print('PASS: complete journal entry and timestamp survived recreation of backend AND database containers')
finally:
    request('DELETE', f"/api/hunts/{created['id']}/")
assert request('GET', '/api/hunts/') == before
print('PASS: temporary entry deleted; existing journal unchanged')

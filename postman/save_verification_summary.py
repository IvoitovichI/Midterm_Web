"""Extract compact evidence from an actual Newman JSON report."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
report = json.loads((here / 'newman-results.json').read_text(encoding='utf-8'))
run = report['run']
assert not run['failures'], run['failures']
summary = {
    'collection': report['collection']['info']['name'],
    'target': 'http://localhost:8081',
    'mode': 'live Flask/Gunicorn API with PostgreSQL 17 in Docker Compose',
    'started_at': run['timings']['started'],
    'completed_at': run['timings']['completed'],
    'requests': run['stats']['requests'],
    'assertions': run['stats']['assertions'],
    'failures': run['failures'],
    'exit_code': 0,
}
previous_path = here / 'verification-summary.json'
if previous_path.exists():
    previous = json.loads(previous_path.read_text(encoding='utf-8-sig'))
    for key in ('desktop_gui_tested', 'desktop_run'):
        if key in previous:
            summary[key] = previous[key]
(here / 'verification-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))

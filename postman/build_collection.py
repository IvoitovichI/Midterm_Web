"""Generate the portable v2.1 collection; run with Python standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
items = []


def add(name, method, path, status=200, body=None, checks=(), raw=None, content_type='application/json'):
    scripts = [f"pm.test('HTTP {status}', () => pm.response.to.have.status({status}));"]
    if status != 204:
        scripts.append('const data = pm.response.json();')
    if status >= 400:
        scripts.append("pm.test('JSON error message', () => pm.expect(data.error).to.be.a('string').and.not.empty);")
    scripts.extend(checks)
    request = {'method': method, 'header': [], 'url': '{{baseUrl}}' + path}
    if body is not None or raw is not None:
        request['header'] = [{'key': 'Content-Type', 'value': content_type}]
        request['body'] = {'mode': 'raw', 'raw': raw if raw is not None else json.dumps(body),
                           'options': {'raw': {'language': 'json'}}}
    items.append({'name': name, 'request': request,
                  'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': ['(() => {', *scripts, '})();']}}]})


add('01 List criminals and save reference data', 'GET', '/api/criminals/', checks=[
    "pm.test('At least 5 criminals', () => pm.expect(data.length).to.be.at.least(5));",
    "pm.test('Criminal fields and location', () => data.forEach(c => { pm.expect(c).to.have.all.keys('id','name','nickname','reward','latitude','longitude','location_note','difficulty','armed','has_crew','escape_master'); pm.expect(c.reward).to.be.a('number').and.at.least(0); pm.expect(c.difficulty).to.be.within(1,10); ['armed','has_crew','escape_master'].forEach(k => pm.expect(c[k]).to.be.a('boolean')); if(c.latitude === null) { pm.expect(c.longitude).to.equal(null); pm.expect(c.location_note).to.be.a('string').and.not.empty; } else { pm.expect(c.latitude).to.be.within(-90,90); pm.expect(c.longitude).to.be.within(-180,180); } }));",
    "pm.collectionVariables.set('criminalId', data[0].id);",
    "pm.collectionVariables.set('allCriminals', JSON.stringify(data));",
])
filters = [
    ('Minimum reward', 'min_reward=5000', 'c.reward >= 5000', None),
    ('Maximum reward', 'max_reward=7500', 'c.reward <= 7500', None),
    ('Armed true', 'armed=true', 'c.armed === true', None),
    ('Armed false', 'armed=false', 'c.armed === false', None),
    ('Has crew', 'has_crew=true', 'c.has_crew === true', None),
    ('No crew', 'has_crew=false', 'c.has_crew === false', None),
    ('Escape master', 'escape_master=true', 'c.escape_master === true', None),
    ('Not escape master', 'escape_master=false', 'c.escape_master === false', None),
    ('Reward ascending', 'sort=reward', 'true', 1),
    ('Reward descending', 'sort=-reward', 'true', -1),
    ('Example combined filters', 'min_reward=5000&armed=true&sort=-reward', 'c.reward >= 5000 && c.armed', -1),
    ('All filters together', 'min_reward=3000&max_reward=15000&armed=true&has_crew=true&escape_master=false&sort=-reward', 'c.reward >= 3000 && c.reward <= 15000 && c.armed && c.has_crew && !c.escape_master', -1),
    ('Empty matching set', 'min_reward=999999999999', 'c.reward >= 999999999999', None),
]
for name, query, predicate, order in filters:
    checks = [
        f'const expected = JSON.parse(pm.collectionVariables.get("allCriminals")).filter(c => {predicate});',
        "pm.test('Exact matching set', () => pm.expect(data.map(c => c.id).sort((a,b)=>a-b)).to.eql(expected.map(c => c.id).sort((a,b)=>a-b)));",
    ]
    if order:
        checks.append(f"pm.test('Reward order', () => {{ for(let i=1;i<data.length;i++) pm.expect((data[i].reward-data[i-1].reward)*{order}).to.be.at.least(0); }});")
    add(name, 'GET', '/api/criminals/?' + query, checks=checks)

add('Criminal details', 'GET', '/api/criminals/{{criminalId}}/', checks=[
    "pm.test('Matches listed criminal', () => pm.expect(data).to.eql(JSON.parse(pm.collectionVariables.get('allCriminals'))[0]));",
])
add('List seeded hunt logs', 'GET', '/api/hunts/', checks=[
    "pm.test('At least 10 logs', () => pm.expect(data.length).to.be.at.least(10));",
    "pm.test('Valid criminal references and timestamp', () => data.forEach(h => { pm.expect(JSON.parse(pm.collectionVariables.get('allCriminals')).some(c => c.id === h.criminal_id)).to.equal(true); pm.expect(Number.isNaN(Date.parse(h.created_at))).to.equal(false); }));",
    "pm.collectionVariables.set('baselineLogs', JSON.stringify(data));",
])
add('Filter journal by criminal', 'GET', '/api/hunts/?criminal_id={{criminalId}}', checks=[
    "const expected = JSON.parse(pm.collectionVariables.get('baselineLogs')).filter(h => h.criminal_id === Number(pm.collectionVariables.get('criminalId')));",
    "pm.test('Exact journal subset', () => pm.expect(data).to.eql(expected));",
])
add('Create capture attempt', 'POST', '/api/hunts/', 201,
    raw='{"criminal_id":{{criminalId}},"success":false,"notes":"Target escaped through an asteroid field."}', checks=[
        "pm.test('Saved fields', () => { pm.expect(data.criminal_id).to.equal(Number(pm.collectionVariables.get('criminalId'))); pm.expect(data.success).to.equal(false); pm.expect(data.notes).to.equal('Target escaped through an asteroid field.'); });",
        "pm.test('Server timestamp is recent UTC', () => { pm.expect(data.created_at).to.match(/Z$/); pm.expect(Math.abs(Date.now()-Date.parse(data.created_at))).to.be.below(60000); });",
        "pm.test('Location header', () => pm.expect(pm.response.headers.get('Location')).to.equal('/api/hunts/'+data.id+'/'));",
        "pm.collectionVariables.set('huntId', data.id); pm.collectionVariables.set('createdAt', data.created_at);",
    ])
add('Read created attempt', 'GET', '/api/hunts/{{huntId}}/', checks=[
    "pm.test('Created attempt persists', () => { pm.expect(data.id).to.equal(Number(pm.collectionVariables.get('huntId'))); pm.expect(data.success).to.equal(false); pm.expect(data.created_at).to.equal(pm.collectionVariables.get('createdAt')); });",
])
add('Update success only', 'PATCH', '/api/hunts/{{huntId}}/', body={'success': True}, checks=[
    "pm.test('Partial update preserves notes and timestamp', () => { pm.expect(data.success).to.equal(true); pm.expect(data.notes).to.equal('Target escaped through an asteroid field.'); pm.expect(data.created_at).to.equal(pm.collectionVariables.get('createdAt')); });",
])
add('Update notes only', 'PATCH', '/api/hunts/{{huntId}}/', body={'notes': 'Captured at Titan Outpost.'}, checks=[
    "pm.test('Partial update preserves success and timestamp', () => { pm.expect(data.notes).to.equal('Captured at Titan Outpost.'); pm.expect(data.success).to.equal(true); pm.expect(data.created_at).to.equal(pm.collectionVariables.get('createdAt')); });",
])
add('Read updated attempt', 'GET', '/api/hunts/{{huntId}}/', checks=[
    "pm.test('Updated values persist', () => { pm.expect(data.success).to.equal(true); pm.expect(data.notes).to.equal('Captured at Titan Outpost.'); });",
])
for name, body in [
    ('Invalid criminal reference', {'criminal_id': 9223372036854775807, 'success': False, 'notes': 'Unknown target'}),
    ('Client cannot supply timestamp', {'criminal_id': 1, 'success': False, 'notes': 'Invalid', 'created_at': '2000-01-01T00:00:00Z'}),
    ('String success rejected', {'criminal_id': 1, 'success': 'false', 'notes': 'Invalid'}),
    ('Boolean criminal ID rejected', {'criminal_id': True, 'success': False, 'notes': 'Invalid'}),
    ('String criminal ID rejected', {'criminal_id': '1', 'success': False, 'notes': 'Invalid'}),
    ('Missing notes rejected', {'criminal_id': 1, 'success': False}),
    ('Null notes rejected', {'criminal_id': 1, 'success': False, 'notes': None}),
    ('JSON array rejected', []),
]:
    add(name, 'POST', '/api/hunts/', 400, body=body)
add('Malformed JSON rejected', 'POST', '/api/hunts/', 400, raw='{broken')
add('Wrong content type rejected', 'POST', '/api/hunts/', 415, raw='{}', content_type='text/plain')
for name, body in [
    ('Empty PATCH rejected', {}),
    ('Timestamp immutable', {'created_at': '2000-01-01T00:00:00Z'}),
    ('Criminal reference immutable', {'criminal_id': 2}),
    ('Invalid PATCH success', {'success': 1}),
    ('Unknown PATCH field', {'other': 'x'}),
]:
    add(name, 'PATCH', '/api/hunts/{{huntId}}/', 400, body=body)
for query in ['min_reward=-1','min_reward=NaN','max_reward=Infinity','min_reward=abc',
              'min_reward=9000&max_reward=5000','armed=yes','has_crew=1','escape_master=',
              'sort=name','min_reward=1&min_reward=2','unknown=1']:
    add('Invalid filter: ' + query, 'GET', '/api/criminals/?' + query, 400)
for path in ['/api/criminals/0/','/api/criminals/no/','/api/hunts/-1/',
             '/api/hunts/9223372036854775808/','/api/hunts/?criminal_id=abc']:
    add('Invalid ID: ' + path, 'GET', path, 400)
for path in ['/api/criminals/9223372036854775807/', '/api/hunts/9223372036854775807/']:
    add('Absent resource: ' + path, 'GET', path, 404)
add('Missing criminal filter is empty', 'GET', '/api/hunts/?criminal_id=9223372036854775807', checks=[
    "pm.test('Empty array', () => pm.expect(data).to.eql([]));",
])
add('Unsupported method', 'POST', '/api/criminals/', 405, body={})
add('Delete created attempt', 'DELETE', '/api/hunts/{{huntId}}/', 204, checks=[
    "pm.test('Empty response', () => pm.expect(pm.response.text()).to.equal(''));",
])
add('Deleted attempt is absent', 'GET', '/api/hunts/{{huntId}}/', 404)
add('PATCH deleted attempt', 'PATCH', '/api/hunts/{{huntId}}/', 404, body={'success': False})
add('Repeated DELETE', 'DELETE', '/api/hunts/{{huntId}}/', 404)
add('Baseline logs retained', 'GET', '/api/hunts/', checks=[
    "pm.test('Only temporary test log removed', () => pm.expect(data).to.eql(JSON.parse(pm.collectionVariables.get('baselineLogs'))));",
])
collection = {
    'info': {'name': 'Space Bounty - Midterm',
             'description': 'Flask/PostgreSQL assignment. Run all requests in order. Creates and removes one temporary hunt; preserves seed data. Offline import requires no Postman workspace.',
             'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
    'variable': [{'key': 'baseUrl', 'value': 'http://localhost:8081'}],
    'item': items,
}
(HERE / 'SpaceBounty.postman_collection.json').write_text(json.dumps(collection, indent=2) + '\n', encoding='utf-8')
(HERE / 'SpaceBounty.local.postman_environment.json').write_text(json.dumps({
    'name': 'Space Bounty - Midterm Local', 'values': [{'key': 'baseUrl', 'value': 'http://localhost:8081', 'enabled': True}],
    '_postman_variable_scope': 'environment',
}, indent=2) + '\n', encoding='utf-8')
print(f'Generated {len(items)} requests')

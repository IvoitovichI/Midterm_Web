# Space Bounty API contract

Base URL: `http://localhost:8081`. JSON only; no authentication is required by this assignment.
Both trailing-slash and non-trailing-slash paths work. Lists are JSON arrays, details are objects.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | 200: database readiness |
| GET | `/api/criminals/` | 200: criminals, default order `id ASC` |
| GET | `/api/criminals/{id}/` | 200: criminal; 404 if absent |
| GET | `/api/hunts/` | 200: journal, newest first, then `id DESC` |
| GET | `/api/hunts/{id}/` | 200: journal entry; 404 if absent |
| POST | `/api/hunts/` | 201: created entry and `Location` header |
| PATCH | `/api/hunts/{id}/` | 200: updated entry; 404 if absent |
| DELETE | `/api/hunts/{id}/` | 204: empty body; 404 if absent |

## Criminal filters

`min_reward` / `max_reward`: inclusive non-negative amounts, at most two decimal places, maximum `999999999999.99`.
`armed`, `has_crew`, `escape_master`: `true` or `false`, case insensitive.
`sort`: `reward` ascending or `-reward` descending; ties use `id ASC`.
All supplied filters combine with AND. Unknown or repeated parameters, invalid values and `min_reward > max_reward` return 400.

```http
GET /api/criminals/?min_reward=5000&armed=true&sort=-reward
```

Criminal fields: `id`, nullable `name`, `nickname`, numeric `reward`, nullable `latitude` / `longitude`, nullable `location_note`, integer `difficulty` (1–10), boolean `armed`, `has_crew`, `escape_master`.
Coordinates are a pair in latitude [-90,90], longitude [-180,180]. A nonblank location note is required when coordinates are absent. Coordinates and a note can coexist.

## Journal writes

POST requires exactly these fields:

```json
{
  "criminal_id": 3,
  "success": false,
  "notes": "Target escaped through an asteroid field."
}
```

`criminal_id` must be a positive JSON integer referencing an existing criminal.
`success` must be a JSON boolean, not `0`/`1` or a string.
`notes` must be text containing 1–10000 characters after trimming outer whitespace.
PATCH accepts `success`, `notes`, or both, and preserves omitted fields.
`id`, `criminal_id` (on PATCH), `created_at`, and unknown write fields are rejected.
An empty PATCH is invalid. `created_at` comes from PostgreSQL `CURRENT_TIMESTAMP`, is serialized as ISO 8601 UTC ending in `Z`, and never changes during PATCH.

GET `/api/hunts/?criminal_id=5` returns only attempts for that criminal. A valid but absent criminal ID gives an empty array.

## Errors

Errors use `{"error":"description"}`.

| Status | Meaning |
| --- | --- |
| 400 | Invalid ID, body, filter, malformed JSON, missing criminal reference |
| 404 | Resource or route not found |
| 405 | Unsupported HTTP method |
| 413 | Body exceeds 32768 bytes |
| 415 | Write request does not use `Content-Type: application/json` |
| 503 | Database temporarily unavailable |

IDs must be positive signed 64-bit integers. A syntactically invalid ID returns 400; a valid nonexistent ID returns 404 on detail/update/delete.
Criminal creation/update/deletion endpoints are outside the assignment and are not exposed.

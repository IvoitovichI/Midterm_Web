# Space Bounty API

REST API for browsing wanted criminals and managing bounty hunting logs. Built with Flask and PostgreSQL, served by Gunicorn, and run with Docker Compose.

## Requirements

- Docker with Docker Compose v2 (Docker Desktop on Windows)
- Postman for running the included collection
- Node.js and npm if running the collection from the command line

## Getting started

From the repository root, run:

```sh
docker compose up -d --build --wait
```

The API is available at `http://localhost:8081`. On first startup, the database is initialized with 5 criminals and 10 hunt logs. Existing data is preserved on subsequent starts.

Check that the API and database are ready:

```sh
curl "http://localhost:8081/health"
```

Expected response:

```json
{"database":"connected","status":"healthy"}
```

On Windows PowerShell, use `curl.exe` for the examples below.

### Configuration

Default settings are provided in `compose.yaml`. To override them, copy `.env.example` to `.env` and edit the values before the first startup.

| Variable | Default |
| --- | --- |
| `APP_PORT` | `8081` |
| `POSTGRES_DB` | `space_bounty` |
| `POSTGRES_USER` | `bounty` |
| `POSTGRES_PASSWORD` | `bounty_local_dev` |

Changing database credentials in `.env` does not update credentials in an existing database. If you change `APP_PORT`, update the URLs and the Postman `baseUrl` variable accordingly.

## Usage

Requests and responses use JSON. No authentication is required.

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/criminals/` | List wanted criminals |
| GET | `/api/criminals/{id}/` | Get a criminal |
| GET | `/api/hunts/` | List hunt logs |
| GET | `/api/hunts/{id}/` | Get a hunt log |
| POST | `/api/hunts/` | Create a hunt log |
| PATCH | `/api/hunts/{id}/` | Update a hunt log |
| DELETE | `/api/hunts/{id}/` | Delete a hunt log |

### Browse criminals

Filter by `min_reward`, `max_reward`, `armed`, `has_crew`, and `escape_master`. Boolean filters accept `true` or `false`. Sort by `reward` for ascending order or `-reward` for descending order. Filters can be combined.

```sh
curl "http://localhost:8081/api/criminals/?min_reward=5000&armed=true&sort=-reward"
curl "http://localhost:8081/api/criminals/3/"
```

### Manage hunt logs

List all hunt logs or filter by criminal:

```sh
curl "http://localhost:8081/api/hunts/"
curl "http://localhost:8081/api/hunts/?criminal_id=3"
```

To create a log, send `POST /api/hunts/` with `Content-Type: application/json` and the following body:

```json
{
  "criminal_id": 3,
  "success": false,
  "notes": "Target escaped through an asteroid field."
}
```

The criminal must exist. The server generates `id` and `created_at`; the response returns the created log with status `201`.

To update the log, send `PATCH /api/hunts/{id}/` with either or both of these fields:

```json
{
  "success": true,
  "notes": "Captured at Titan Outpost."
}
```

Use the ID returned by the creation request to read or delete the log. A successful deletion returns `204` with no response body.

See [API.md](API.md) for field validation, response codes, and error details.

## Postman

1. Import [the collection](postman/SpaceBounty.postman_collection.json).
2. Import [the local environment](postman/SpaceBounty.local.postman_environment.json).
3. Select **Space Bounty - Midterm Local** and confirm that `baseUrl` is `http://localhost:8081`.
4. Open **Space Bounty - Midterm**, select **Run**, and run all requests in their original order.

The collection covers criminal filters, sorting, details, journal CRUD, and invalid requests. It creates one temporary hunt log and deletes it at the end. Run the initial criminal listing and log creation requests before using individual requests that depend on `criminalId` or `huntId`.

To run the collection from the command line:

```sh
npx --yes newman run postman/SpaceBounty.postman_collection.json -e postman/SpaceBounty.local.postman_environment.json
```

On Windows PowerShell, use `npx.cmd` if script execution policy prevents `npx` from running.

## Managing the application

Check container status and view backend logs:

```sh
docker compose ps
docker compose logs --tail 50 backend
```

Stop the application:

```sh
docker compose down
```

Database data is stored in a named Docker volume and retained when the application is stopped. To remove the database and start again with the initial data, run `docker compose down -v`, then repeat the startup command.

# Nexora RailRadar acquisition foundation

This stage provides the data-acquisition layer for the Nexora SIH prototype: authenticated RailRadar requests, safe error handling, normalized internal models, and append-only raw response capture. The initial configurable corridor is the Mumbai Central Line corridor from CSMT to Thane.

RailRadar is used here as a prototype/live-data source. It is not official railway signalling, dispatch, or train-control data, and this prototype must not be used to control railway operations.

## Scope

Included:

- station directory lookup
- trains-between-stations discovery
- live train running status
- optional train route/GIS geometry
- normalized station, train, live-status, stop, and route models
- append-only raw JSON capture under `data/raw/`
- mocked unit tests and a one-shot connectivity check

Not included yet: machine learning, OR-Tools, scheduling or optimization, accident handling, rerouting, conflict resolution, dashboard/frontend, or PostgreSQL.

## Setup

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The existing `.env` must contain the API key. The key is read from `RAILRADAR_API_KEY`; it is never printed, stored in source, or written into response metadata.

Optional settings:

```dotenv
RAILRADAR_API_BASE_URL=https://api.railradar.in/v1
RAILRADAR_TIMEOUT=15
RAILRADAR_RETRY_COUNT=2
RAILRADAR_RETRY_DELAY=1
```

Environment variables override values from `.env`. The base URL must use HTTPS.

## Tests

```bash
source .venv/bin/activate
python -m pytest
```

The tests use mocked HTTP responses and do not consume RailRadar quota.

## One-shot API check

```bash
source .venv/bin/activate
python scripts/test_railradar.py
```

Useful options:

```bash
python scripts/test_railradar.py --skip-live
python scripts/test_railradar.py --date YYYY-MM-DD --limit 3
python scripts/test_railradar.py --from-code CSMT --to-code TNA
```

The program authenticates with the station-directory request, verifies the configured corridor codes, discovers trains, requests live status for the first discovered train, prints only normalized fields, and saves successful responses. It performs one request sequence and does not poll continuously. Normal HTTP failures are reported without a traceback.

## Real mini-collection

The standalone collector performs discovery once, selects relevant Mumbai suburban services automatically, fetches route geometry once per selected train, validates one live observation per selected train, and then starts the live collection automatically if validation succeeds.

```bash
source .venv/bin/activate
python scripts/collect_railradar.py
```

The default run is 20 minutes. It enforces a serialized rolling-window limit of no more than 10 requests per 60 seconds, including retries. It uses the documented 1,000-request sandbox quota with a 15% safety reserve and counts successful raw observations already present locally as known prior usage. Optional environment overrides are `NEXORA_COLLECTION_MINUTES`, `NEXORA_STALE_THRESHOLD_SECONDS`, and `RAILRADAR_MONTHLY_QUOTA` when the account quota is known and differs from the documented default.

The collector does not use parallel requests, synthetic data, or repeated train discovery. Every normalized live row is marked `data_source=REAL`.

For a background standalone process with accessible logs:

```bash
nohup .venv/bin/python scripts/collect_railradar.py > data/collector.log 2>&1 &
```

The collector writes:

```text
data/selected_trains.json
data/static/stations/<run_id>_directory.json
data/static/trains/<run_id>_between.json
data/static/routes/<run_id>_<train_number>.json
data/raw/<date>/<run_id>/<train_number>/<timestamp>.json
data/processed/live_observations.csv
data/runs/<run_id>.json
data/reports/<run_id>_quality_report.json
```

The CSV is append-only and has one row per real live observation. Missing values remain empty, stale observations are retained with `is_stale` and `data_age_seconds`, and route information is preserved in `route_json`. Pressing Ctrl+C flushes the CSV and writes partial run metadata and a partial quality report.

## Targeted moving-train augmentation

After an initial collection, the targeted collector reuses the existing static discovery snapshot, probes locally relevant candidates, selects currently running trains, and starts a new rate-limited collection automatically when validation finds usable moving services.

```bash
source .venv/bin/activate
python scripts/collect_targeted_railradar.py
```

It never modifies `data/processed/live_observations.csv`. New raw responses are placed under a new run directory, new observations are written to `data/processed/live_observations_targeted.csv`, and the old plus new real rows with provenance-aware deterministic features are written to `data/processed/live_observations_augmented.csv`.

Derived fields are explicitly labeled with `API`, `DERIVED`, or `MISSING` provenance. No synthetic observations or fabricated values are created.

## Raw response storage

Each saved response is written to a unique file such as:

```text
data/raw/YYYY-MM-DD/HHMMSS-microseconds-v1-trains-12345-...json
```

The JSON document contains the collection timestamp, endpoint, optional train number, HTTP status, and the parsed response. Previous observations are not overwritten. Raw files are ignored by Git; the directory is retained with `.gitkeep`.

## Verified RailRadar API contract

The implementation follows the official documentation at [railradar.in/docs](https://railradar.in/docs):

- Base URL: `https://api.railradar.in/v1`
- Authentication: `Authorization: Bearer <API key>`
- Station directory: `GET /v1/lookup/stations`, returning a `{code: name}` map in `data`
- Trains between stations: `GET /v1/trains/between/{from}/{to}` with optional `date`, `type`, `category`, `byCity`, and `live` query parameters
- Live status: `GET /v1/trains/{number}/live` with optional `date`, `authoritative`, `haltsOnly`, `geometry`, `format`, and `includeCoordinates` query parameters
- Route geometry: `GET /v1/trains/{number}/route` with optional `format` and `stops` query parameters; the documented response supports GeoJSON, encoded polyline, or coordinates

The client keeps endpoint methods separate from generic GET, timeout, retry, and HTTP-error handling. It retries timeouts, connection failures, 429, and temporary 5xx responses according to bounded exponential backoff. It does not retry 401, 404, or other client errors.

## Security

- Keep the real `.env` local and never commit it.
- Never put the API key in source, tests, README files, logs, filenames, or commits.
- The client never logs request headers or response bodies on errors.
- Raw API responses may contain operational data, so they are ignored by Git and should be handled as local development data.

## Architecture and limitations

The API client, models, normalizer, corridor configuration, and raw storage are separate. `src/railradar/corridors.py` contains the prototype corridor so later Western or Harbour configurations can be added without changing the RailRadar client.

The exact station-directory documentation currently describes station metadata as a flat code-to-name map. Coordinates are therefore only normalized when present in documented train status or route-stop payloads; no coordinates or missing live values are fabricated. The live response shape can vary by train and upstream availability, so optional fields remain `None` when absent.

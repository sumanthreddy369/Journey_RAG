# Anonymous local progress history

PostgreSQL persistence is optional. The history is shared by everyone using this
local installation; it is not an individual learner profile. There are no accounts,
cookies, anonymous learner IDs, or authentication. Keep both API and database on
loopback and run one API worker.

## Stored fields

`progress_history` has exactly five columns:

| Column | Source |
| --- | --- |
| `topic_label` | Retrieved citation topic checked against `chunks.json`, or `MATLAB fundamentals`. |
| `score` | Server-computed percentage. |
| `route` | Deterministic reteach, practice, or advance route. |
| `recommendation` | Fixed recommendation from the scoring function. |
| `timestamp` | Timezone-aware UTC completion time, also the row key. |

Names, emails, passwords, IP addresses, raw questions, selected answers, and
answer keys are not stored in this table. Database credentials exist only in the
ignored local `.env.progress` file. Alembic also maintains its schema-version table.
Raw question/answer console printing is removed; use `--no-access-log` to avoid
Uvicorn request/IP access logs. Questions still go to the configured local model
for retrieval and generation. The rate limiter holds client addresses in memory.

## Start locally (PowerShell)

Install dependencies from `requirements.txt` in your virtual environment. Docker
Desktop must be running. Then, from the repository root:

```powershell
.\scripts\start-progress.ps1
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003 --no-access-log
```

The script creates random local credentials if absent, imports them into the
current shell, starts Compose project `journey-progress`, and runs
`python -m alembic upgrade head`. The database is PostgreSQL 16 on
`127.0.0.1:5435`, separate from other projects, with a Docker named volume.
It does not start Qdrant, Ollama, or MCP or download model weights.

`JOURNEY_DATABASE_URL` must use `postgresql+psycopg` and a loopback hostname;
connection query parameters are rejected. No database connection is made until a
history read or write is requested. Clearing that environment variable disables
persistence. The schema is created only by migrations, not application startup.

## API and UI

- `POST /learning-sessions/{session_id}/submit` returns scoring plus
  `progress_saved` and `progress_message`.
- `GET /progress-history?limit=20&offset=0` returns newest-first records. Limit is
  1–100; offset is nonnegative. Disabled or unavailable storage returns HTTP 503
  with a generic message, never a connection string.
- `/app` shows history, an empty state, storage errors, refresh, and older records.

The first valid submission freezes the score. Resubmitting returns that score,
even with different answers. Retry after an outage can save the original attempt.
Repeated saves use the same timestamp and do not add rows. A process lock prevents
concurrent submissions from saving twice. Timestamp allocation is unique within
the single API process. The older synthetic demo endpoints never persist progress.

Database failure does not discard the score: the UI reports that it was not saved.
An unsaved attempt can be retried only while its process-local session remains
alive. Restarting the API retains saved history but discards keys and unsaved
attempts. Pagination uses offsets and can shift if new attempts arrive between
pages; refresh restarts from the newest records.

Quiz generation uses Ollama JSON-schema output and retries once when the returned
payload still fails the server's structural or answer-index validation. A second
failure returns HTTP 503 and does not create a session or progress record.

## Retention and local scope

History stays in the local Docker volume until explicitly removed; no scheduled
retention policy or deletion UI is implemented. Stopping Compose preserves it.
Deleting the named volume permanently deletes the history and must be a deliberate
user action. This feature is for a trusted local installation, not a public or
multi-user deployment. CORS is limited to the local UI origins; it is not authentication.

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

The real PostgreSQL test is opt-in and skips without `JOURNEY_TEST_DATABASE_URL`.
Use a dedicated database whose name ends in `_test`, with the same loopback URL
format. It applies migrations, writes a synthetic attempt twice, reconnects,
checks the five-column schema, reads via the API, and removes its test row.
Unit/API tests cover privacy fields, disabled storage, outages, retry behavior,
pagination bounds, concurrent submissions, and synthetic-session exclusion.

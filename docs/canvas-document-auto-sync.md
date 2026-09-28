# Canvas document auto sync

Core-api consumes a new `canvas_sync` BullMQ queue using the existing Redis.
The Python worker continues consuming `document_processing` for parse/chunk jobs.
No additional service or database migration is required for auto sync itself.
The existing Canvas document sync migrations must already be applied.

## Triggers

- A single `upsertJobScheduler` sweep runs every 15 minutes and enqueues all live
  Canvas courses with a live `lms_course_ref`, in pages of 100 courses.
- A Canvas LTI launch by an instructor or TA triggers a background sync after the
  course/membership transaction commits. Learner/observer launches and other LMSs
  do not trigger it. Launch does not wait for Redis or Canvas.
- The manual button checks instructor/TA access and enqueues the same course job.
  It returns `{ job_id, status: "QUEUED" }`, not a completed sync summary.

All three use `jobId = canvas-sync-<courseId>` (BullMQ forbids colons in custom
IDs). Waiting, active, and retrying jobs retain this ID, so duplicate triggers
do not start a second job. Jobs are removed after completion or final failure,
allowing the next trigger to enqueue again. There are three attempts with
exponential backoff starting at five seconds. Failed attempts are logged.

The LTI cooldown is a Redis key scoped to queue/course, shared by all replicas.
It is refreshed at the start and successful end of sync, suppressing launches
for two minutes even after a failed attempt. Manual and scheduled sync bypass
this cooldown. `lms_course_ref.synced_at` is not reused: it tracks LTI launches,
not document synchronization.

## Configuration

Set these on **core-api** (also wired through the root Docker Compose):

| Variable | Default | Meaning |
| --- | --- | --- |
| `CANVAS_API_URL` | Falls back to `LTI_PLATFORM_URL` | Canvas REST API base URL |
| `CANVAS_API_TOKEN` | Required | Server-side Canvas token |
| `CANVAS_AUTO_SYNC_ENABLED` | Enabled when URL/token are configured | `false` removes the scheduler and disables launch triggers; manual sync remains available |
| `CANVAS_SYNC_INTERVAL_MS` | `900000` | Sweep interval, 15 minutes |
| `CANVAS_SYNC_LAUNCH_COOLDOWN_MS` | `120000` | Launch cooldown, 2 minutes |

Restart core-api after changing configuration. Jobs already accepted may finish
even when automatic triggers are subsequently disabled.

## Scope and processing

Sync still imports supported file items in **Modules** only. The paginated
`GET /courses/:id/files` call provides metadata for comparison; it does not expand
the import scope to every file in Files. Unchanged versions avoid downloads.
Module/chapter placement and teacher-confirmed choices keep existing behavior.
System imports have nullable `created_by`; manual imports record the requesting
user. System deletion is constrained to a Canvas document in the given course.

Each sync downloads at most 30 new/changed files. Remaining files are picked up
by later syncs. Unsupported files, missing metadata, and per-file failures are
reported in the summary in core-api logs. A whole-listing failure is retried by
BullMQ. A listing exceeding the existing 20-page limit fails rather than treating
a partial snapshot as complete and hiding documents. Processing enqueue failures
mark the document ERROR so a later sync can retry it.

The documents page shows the accepted request immediately; reload it to see
new documents and processing status. For diagnosis, inspect core-api logs for
`CanvasSyncProcessor` / `CanvasSyncJobsService` and Python document-worker logs
for parse/chunk failures.

## Validation

Run `pnpm exec jest --runInBand` in `core-api` for unit tests. To verify the
actual BullMQ concurrency/cooldown/retry behavior, point
`CANVAS_SYNC_TEST_REDIS_URL` at a disposable Redis and run
`pnpm exec ts-node test/canvas-sync-redis.smoke.ts`. The smoke test uses a unique
queue and cleans up its own keys; it does not call Canvas or write to Postgres.

# Canvas document auto sync

Core-api consumes a new `canvas_sync` BullMQ queue using the existing Redis.
The Python worker continues consuming `document_processing` for parse/chunk jobs.
No additional service is required for auto sync itself. The existing Canvas
document sync migrations must already be applied. Run history (see
[Sync history and status](#sync-history-and-status)) needs migration
`20261112120000_canvas_sync_runs`; without it sync still works and recording a
run only logs a warning.

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
| `CANVAS_API_URL` | Falls back to `CANVAS_PUBLIC_URL` (Compose) or `LTI_PLATFORM_URL` | Canvas REST API base URL; see [Internal Canvas API URL](#internal-canvas-api-url) |
| `CANVAS_PUBLIC_URL` | Unset | Public Canvas origin; links under it are rewritten to `CANVAS_API_URL` |
| `CANVAS_API_TOKEN` | Required | Server-side Canvas token of the `DA Platform Service` user ([canvas_lti_setup.md](canvas_lti_setup.md#token-rest-api-của-canvas)) |
| `CANVAS_AUTO_SYNC_ENABLED` | Enabled when URL/token are configured | `false` removes the sweep and token-check schedulers and disables launch triggers; manual sync remains available |
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
new documents, processing status and the sync status block. For diagnosis,
inspect core-api logs for `CanvasSyncProcessor` / `CanvasSyncJobsService` and
Python document-worker logs for parse/chunk failures.

## Sync history and status

`CanvasSyncProcessor` writes one `canvas_sync_runs` row per course job, with
`trigger` = `launch`, `sweep` (the 15-minute sweep) or `manual`. The row opens as
`running` when the job starts and closes as `success` with the sync summary, or as
`error` with a message for the instructor. BullMQ retries reuse the same row: it
only becomes `error` after the last attempt. Writing history never fails a sync.
Error messages: HTTP 401 becomes "Token Canvas hết hạn hoặc không hợp lệ";
connection refused, `fetch failed`, 502, 503 and 504 become "Không kết nối được
Canvas"; anything else keeps the original message. A row stuck in `running` for
over 30 minutes (core-api restarted mid-job) is reported as interrupted.

The `GetCanvasSyncStatus` RPC (instructor/TA of the course, like the manual
sync) returns the last run (status, trigger, times, summary counts, error), the
last successful run time and the token check below. **Tài liệu khóa học** shows
it next to the **Đồng bộ từ Canvas** button: last sync time and number of new or
updated files, the error in red when the last run failed (the button then reads
"Thử lại"), "Đang đồng bộ…" while running, and "Token Canvas lỗi: …" when the
token check failed.

## Roster sync (NRPS)

The same three triggers also enqueue a **roster job** (`sync_roster`, `jobId =
canvas-roster-<courseId>`, same queue, same three attempts) that reads the Canvas
class list with NRPS and updates `lms_user_mappings` / `course_memberships`; see
[canvas_lti_setup.md](canvas_lti_setup.md#custom-field-và-danh-sách-lớp-nrps).
The launch trigger has its own Redis cooldown key (`roster-cooldown:<courseId>`,
same duration), so a long document sync never blocks a roster refresh. It is
gated by `CANVAS_AUTO_SYNC_ENABLED` like the sweep. Each job writes a
`canvas_sync_runs` row with `kind = 'roster'` (documents rows have `kind =
'documents'`); `GetCanvasSyncStatus` returns it under `roster` together with the
active learner count, and the documents page shows "Danh sách lớp: n sinh viên ·
đồng bộ …" or the error in red. NRPS is called on the public Canvas host, not on
`CANVAS_API_URL` (Canvas validates the token `aud` against the request host).

## Token check

When auto sync is enabled core-api checks the token with `GET /api/v1/users/self`
once at startup and then every 24 hours (a repeatable job on the same queue).
The result `{ checked_at, ok, http_status, message }` is stored as JSON, without
TTL, under the Redis key `canvas:token-status`. Read it with
`redis-cli GET canvas:token-status`. A 401 shows up in red on the documents page
at the next check instead of at the next failed sync.

## Internal Canvas API URL

By default core-api calls `CANVAS_PUBLIC_URL`, so even when Canvas runs on the
same machine every request leaves through the Cloudflare tunnel and comes back
(roughly 230-380 ms against 120-160 ms for `GET /users/self` measured from the
core-api container). On the machine that runs both Canvas and DA, add to `.env`:

```
CANVAS_API_URL=http://canvas.docker:3000
```

Compose maps `canvas.docker` to the host (`extra_hosts: canvas.docker:host-gateway`
on core-api). Do not use `host.docker.internal`: Canvas development mode blocks
unknown hosts (`403 Blocked hosts`) and only accepts `*.canvas.docker` (its
`VIRTUAL_HOST`), `localhost`, IP addresses and its configured domain. Other
teammates leave `CANVAS_API_URL` unset and keep using the tunnel URL. Recreate
the container to apply (`scripts/dc up -d --no-deps core-api`).

Behaviour observed against local Canvas, which the client relies on:

- With the internal host, Canvas builds API links (`Link: rel="next"`, file
  `url`) from the request host, so pagination stays internal. Links that still
  carry the public host (host of `LTI_PLATFORM_URL` or `CANVAS_PUBLIC_URL`,
  `http` or `https`) are rewritten to the `CANVAS_API_URL` origin; links to any
  other host are never rewritten.
- File downloads cannot finish on the internal host. `GET /files/:id/download`
  answers 302 to `http://<public domain>/files/:id/download?...&sf_verifier=...`
  and Canvas only serves the bytes when the request carries the public domain as
  host (calling the internal address again redirects in a loop; it also answers
  from the public file host directly with 200). So `downloadFile` does not
  rewrite: the listing and the first hop stay internal, the bytes come through
  the tunnel as before. No redirect to object storage (S3) was seen: Canvas
  itself answered 200 with the file bytes.

## Validation

Run `pnpm exec jest --runInBand` in `core-api` for unit tests. To verify the
actual BullMQ concurrency/cooldown/retry behavior, point
`CANVAS_SYNC_TEST_REDIS_URL` at a disposable Redis and run
`pnpm exec ts-node test/canvas-sync-redis.smoke.ts`. The smoke test uses a unique
queue and cleans up its own keys; it does not call Canvas or write to Postgres.

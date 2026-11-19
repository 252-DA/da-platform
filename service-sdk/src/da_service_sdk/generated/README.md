# generated/

Output of `scripts/generate_proto.py`. Committed to the repo, never
hand-edited — CI regenerates and runs `git diff --exit-code` to catch drift
between `proto/` and this directory.

Run `uv run python scripts/generate_proto.py` after any change to
`proto/da_platform/embedding/v1/embedding.proto` to populate this directory.

# Fetch published chart

Reads the tracked immutable publication receipt, checks its version against the
tag and pulls the exact OCI artifact. Missing receipts fail before publication.
See [fixtures](../../scripts/test-actions.py).

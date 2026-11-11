# Publish qualified chart

Requires the source-bound qualification receipt and package-write token through
the action environment. Publishes only exact qualified bytes to this repository's
GHCR chart namespace, refuses replacement and verifies a digest-addressed pull.
Negative preflight is covered by [fixtures](../../scripts/test-actions.py).
Actual publication requires external credentials and separate evidence.

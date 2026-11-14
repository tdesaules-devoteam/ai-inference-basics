# Align HTTP/2 buffers for multimodal responses

## Context

An Omni text/audio request succeeded with Python's HTTP/1.1 client but returned
HTTP 500 with curl negotiating HTTP/2. Envoy logged `response_payload_too_large`.
The connection buffer watermarks were already 32 MiB, but the HTTP/2 listener
still had its default 64-KiB per-stream window. The buffered audio JSON exceeded
that independent stream limit.

## Decision

Set ClientTrafficPolicy `http2.initialStreamWindowSize` and
`http2.initialConnectionWindowSize` from the existing `bufferLimit` chart value.
Keep TLS and Bearer authentication intact. These are buffering/flow-control
settings, not a universal application request-size limit.

`tests/qualify_audio_http2.py` uses curl to explicitly exercise both HTTP/1.1 and
HTTP/2 with the French audio request, checking the negotiated protocol and a
decodable 24-kHz WAV response. This complements the urllib-based API tests, which
do not negotiate HTTP/2.

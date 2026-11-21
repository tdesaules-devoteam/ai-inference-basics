# Align HTTP/2 buffers for multimodal responses

Status: the buffer settings are retained. The multimodal model used to diagnose
the issue is no longer part of the lab.

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

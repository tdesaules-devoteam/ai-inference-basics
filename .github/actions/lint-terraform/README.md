# Terraform validation

Pinned Terraform 1.17.2 checks formatting, initializes provider 2.91.0 against the
committed lock and validates the configuration. Backend initialization and apply
are disabled; no cloud credentials are required. Local native validation and the
Docker runtime check are recorded separately in reports.

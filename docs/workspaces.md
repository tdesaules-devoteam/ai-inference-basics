# Browser administration workspaces

Each participant has a dedicated Pod and read-oriented Kubernetes ServiceAccount.
The administration image uses digest-pinned `quay.io/fedora/fedora-minimal` 45,
with bash, curl, jq, git, kubectl 1.37.2, k9s 0.51.0, Helm 4.2.2, Task 3.54.0 and
checksum-verified Zellij 0.46.0. No nested container engine or privileged terminal.

## Local access

1. Run `task access:tunnel`. The SSH forward listens on **127.0.0.1:30443** only.
2. Resolve `lab.ai-inference-basics.test` to `127.0.0.1` on the workstation (for example, a managed
   hosts-file entry). This repository does not overwrite host DNS configuration.
3. Trust the local lab certificate `.local/secrets/tls.crt` in the browser for this
   disposable lab. Automated browser tests scope their trust bypass to their test
   context; API tests verify this certificate explicitly with curl.
4. Open `https://lab.ai-inference-basics.test:30443/headlamp/`, `/grafana/`, or the terminal URLs below.

| Participant | Terminal | Preview |
| --- | --- | --- |
| A | `https://lab.ai-inference-basics.test:30443/terminal-a/workshop` | `https://lab.ai-inference-basics.test:30443/preview-a/` |
| B | `https://lab.ai-inference-basics.test:30443/terminal-b/workshop` | `https://lab.ai-inference-basics.test:30443/preview-b/` |

## Two intentional authentication steps

First sign in through Dex/oauth2-proxy with the email/password stored in the
instructor-only `.local/secrets/credentials.json`. Initial local test identities
are `alice@example.test` and `bob@example.test`; set LAB_EMAIL_A/LAB_EMAIL_B before
the first `task auth:init` to choose different addresses. Existing credentials are
preserved, not silently rotated.

The Zellij web client then requests its own native login token. Run
`task workspace:credentials` to copy the two tokens to protected instructor files:

- `.local/secrets/zellij-a.token`
- `.local/secrets/zellij-b.token`

Distribute each token only to its participant. Tokens are not printed by automation
or committed. Zellij keeps a hashed authentication database in the workspace;
the instructor's recovery copy is plaintext and protected with mode 0600.
Recreating the workspace Pod replaces its emptyDir and token; collect new tokens.
Browser disconnection leaves the named Zellij session available for reconnection.
Pod recreation disposes of sessions and workspace data in this initial profile.

Zellij listens only on Pod loopback. Caddy publishes it on the terminal Service,
strips the terminal path prefix, and scopes its native `session_token` cookie to
that path with Secure set. This avoids A/B cookie collisions on the local hostname.
The outer Dex session is separate. Both layers are exercised by browser tests.

## Tools and previews

Run `k9s`, `kubectl`, `helm`, `task`, `curl`, `jq` or `git` inside the terminal.
`task workspace:seed` places the current umbrella archive and participant Taskfile
in both Pods. Participants can run `task pods`, `task platform:inspect` and
`task preview`. `task platform:install` requires the instructor-enabled installer
identity. The local seeded archive supports the dry run while GHCR publication
awaits the owner's push.
To preview the demo:

```sh
kubectl -n demo port-forward --address 127.0.0.1 svc/whoami 18080:80
```

Keep the process running in a Zellij pane. Caddy in the same Pod forwards the
preview to this loopback port. Without it the preview returns 502. Ctrl-C stops
the forward. Preview access remains protected by Dex; it does not use the browser's
localhost. Local preview paths suit the demo; subdomains are needed for applications
that assume root-relative assets.

Read identities can inspect workloads, metrics and CRDs and forward demo Pods;
they cannot read Secrets or cluster role bindings. NetworkPolicies reject direct
workspace access to model Services, Headlamp, Grafana and the other preview.

For the explicitly elevated workshop phase, the instructor can run
`task lab:enable-installer`, which switches workspaces to separately labeled
installer SAs. This exposes full lab privileges, including lab Secrets. Run
`task lab:restore` afterwards, collect replacement Zellij tokens and rotate/delete
credentials at teardown. This is a trusted shared lab, not hostile multi-tenancy.

The workstation SSH forward is a transient user systemd service named
`ai-inference-basics-browser-<checkout-uuid>`, so it survives Task exit and reconnects after VM
reboot. `task down` stops it. No web administration service runs on the guest host.

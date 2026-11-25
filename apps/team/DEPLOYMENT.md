# Safe deployment of Team Desk

Team Desk handles private reviewer identities, credentials, unfinished Bible
text, review work, and signatures. Do not expose its Python HTTP port directly
to the internet.

## Security boundary

Run one Team Desk process behind an HTTPS reverse proxy or private access
gateway. The gateway must:

1. authenticate every request before proxying it;
2. remove any incoming `X-LBF-Gateway` header;
3. inject its own `X-LBF-Gateway` header containing the shared gateway secret;
4. preserve the public `Host` header;
5. set `X-Forwarded-For` itself if proxy-aware rate limiting is enabled;
6. terminate TLS and redirect HTTP to HTTPS.

The app refuses to start in production unless its persistent directory,
HTTPS origin, public host, gateway secret, and hashed reviewer credentials are
all configured. `/healthz` is the only endpoint that intentionally bypasses
gateway authentication; it contains no private data.

## Private persistent data

Mount a persistent directory that is readable and writable only by the Team
Desk service account. It holds `people.json`, claims, recovered browser work,
and `peer-review-signoffs.json`.

```sh
export LBF_TEAM_DATA_DIR=/srv/lpf-team-private
```

Back this directory up. Run only one Team Desk process against it because the
private ledgers are atomic JSON files, not a multi-writer database.

## Reviewer credentials

Never copy plaintext `people.json` into production. To hash existing local
credentials in place:

```sh
LBF_TEAM_DATA_DIR=/path/to/private-data python3 apps/team/manage_users.py migrate
```

Add or rotate a reviewer interactively:

```sh
LBF_TEAM_DATA_DIR=/path/to/private-data python3 apps/team/manage_users.py add "Reviewer Name"
```

New credentials must be at least 12 characters. The file stores scrypt
verifiers with unique random salts, never the submitted credential.

## Required production environment

Generate a separate random gateway secret and store it in the service's secret
manager, not in Git:

```sh
openssl rand -hex 32
```

Configure the service with values equivalent to:

```text
LBF_TEAM_ENV=production
LBF_TEAM_HOST=127.0.0.1
LBF_TEAM_PORT=1435
LBF_TEAM_DATA_DIR=/srv/lpf-team-private
LBF_TEAM_ALLOWED_ORIGINS=https://review.example.org
LBF_TEAM_ALLOWED_HOSTS=review.example.org
LBF_TEAM_GATEWAY_SECRET=<64-character-random-secret>
LBF_TEAM_TRUST_PROXY=1
```

Keep `LBF_TEAM_HOST=127.0.0.1` when the proxy runs on the same machine. In a
container network it may bind to `0.0.0.0`, but the container port must remain
private and reachable only by the authenticated reverse proxy.

`LBF_TEAM_TRUST_PROXY=1` is safe only when clients cannot connect directly to
Team Desk and the proxy replaces `X-Forwarded-For` rather than appending an
untrusted client value.

## Reverse-proxy requirements

The proxy must send the same secret configured in
`LBF_TEAM_GATEWAY_SECRET`. For example, the protected proxy location should
behave like this (exact authentication and secret syntax depends on the chosen
gateway):

```nginx
location / {
    # Require the organization's SSO, private-access policy, or strong Basic
    # authentication here before proxying the request.
    proxy_set_header X-LBF-Gateway "<gateway secret from secret manager>";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_pass http://127.0.0.1:1435;
}
```

Do not place the real secret in a committed proxy configuration. Load it from
the deployment platform's secret store or a root-owned configuration file.

## Built-in defenses

Production mode provides:

- scrypt credential verification with constant-time comparisons;
- an authenticated gateway requirement on every private route;
- strict host and request-origin allowlists;
- ten failed sign-in attempts per client per fifteen minutes;
- a one-megabyte request limit;
- no-store responses, HSTS, clickjacking protection, MIME protection, a
  restrictive permissions policy, and a content security policy;
- startup refusal instead of silently accepting an unsafe configuration.

The reviewer credential is sent only in HTTPS JSON requests and is never saved
to browser storage. Chapter-reading progress contains no credential and stays
in that browser's local storage.

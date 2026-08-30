# Live match-day operations

The production path is phone RTMPS → stable relay VPS → disposable RunPod GPU
→ authenticated dashboard. The relay address stays fixed, so replacing a GPU
pod never changes the phone configuration.

## 1. Deploy the relay once

Use a small Ubuntu VPS with DNS pointed at it. Allow SSH, TCP 80 for the ACME
challenge, and TCP 1936 for RTMPS. Then run locally:

```bash
export RTGS_RELAY_PUBLISH_PASSWORD='strong-publisher-secret'
export RTGS_RELAY_READ_PASSWORD='strong-reader-secret'
export RTGS_RELAY_CERTBOT_EMAIL='operator@example.com'
./rtgs relay deploy ubuntu@relay.example.com relay.example.com
./rtgs relay doctor relay.example.com
```

This installs Docker/Certbot when needed, obtains a Let's Encrypt certificate,
configures distinct publisher/reader identities, starts MediaMTX, and adds a
certificate-renewal restart hook. The relay does not record footage. The query
parameter credential form follows the [MediaMTX authentication
contract](https://mediamtx.org/docs/features/authentication).

Configure the phone app with:

```text
rtmps://relay.example.com:1936/live?user=publisher&pass=SECRET
```

If it separates server and stream key, use
`rtmps://relay.example.com:1936` and
`live?user=publisher&pass=SECRET`. Test the exact app before match day; mobile
apps vary in RTMPS and query-parameter support.

## 2. Build and configure the GPU runtime

Relevant pushes to `main` run contracts and publish:

```text
ghcr.io/elleowo/realtimegamestatistics:<full-git-sha>
```

Make the package public or configure a RunPod registry credential. Create one
RunPod network volume for model caches, then run `./rtgs cloud configure`.
Private configuration is stored at `~/.config/rtgs/config.json` with mode 0600;
it includes the image tag pattern, and the environment variables in
`.env.example` can override it.

The lifecycle script uses the current commit's exact image. It does not SSH
into a pod or reinstall dependencies at game time. RunPod's official
[`POST /pods` API](https://docs.runpod.io/api-reference/pods/POST/pods) exposes
only gateway port 8080 and mounts the cache volume at `/workspace`.

## 3. Pre-match gate

```bash
./rtgs test
./rtgs cloud test --clip /secure/path/rtgs-smoke.mp4
./rtgs relay doctor relay.example.com
./rtgs cloud cleanup
```

Run this at least a day before the match and again before leaving. The paid
smoke covers both post-game and the actual RTMPS live path.

## 4. Match day

Prefer dedicated 5G for the phone and wired internet for the analyst. Mount the
phone near midfield in landscape, use the rear wide camera, external power, and
disable auto-lock. Start with 720p30 H.264 and a conservative bitrate; reliable
latency matters more than resolution.

Start publishing from the phone, then run:

```bash
./rtgs cloud live --max-minutes 180
```

It creates the pod, prints a unique dashboard URL and Basic-auth password,
monitors source health, downloads artifacts at full time, and terminates the
pod. The phone can publish first: the backend waits and reconnects until the
relay source appears.

Open the dashboard, confirm `waiting` → `calibrating` → `live`, configure teams
and directions, then choose **1H** at kickoff, **HT**, **2H**, and **FT** at the
whistles. Analytics intentionally pause outside active halves.

The health popover shows frame age, processing time, payload rate, reconnects,
calibration, and coverage. Frame age above three seconds is not ready.
`stalled`/`reconnecting` are explicit states and the backend reopens RTMPS after
repeated failed reads.

Backend freshness is not full phone-to-screen delay. Measure glass-to-glass
latency in the pre-match gate and target less than three seconds at the analyst
screen.

## 5. Recovery and shutdown

- Phone drops: keep the pod running and restart publishing to the same URL.
- Pod fails: run `./rtgs cloud live` again, then restore phase/clock/score.
- Analyst disconnects: reload the same URL; WebSocket reconnect is automatic.
- Billing orphan: `./rtgs cloud cleanup` lists only `rtgs-*` pods and asks before
  terminating. `--yes` is for deliberate automation only.

Normal completion downloads a ZIP with `run-summary.json`, compressed
observations, operator state, and event clips. Full-match video is not retained
by the relay or live pod.

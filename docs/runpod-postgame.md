# RunPod workflows

The canonical RunPod workflow uses the prebuilt commit-tagged GPU image and
automated lifecycle commands:

```bash
./rtgs cloud configure
./rtgs cloud test --clip /secure/path/rtgs-smoke.mp4
./rtgs cloud live
./rtgs cloud cleanup
```

See [testing.md](testing.md) for the free replay loop and paid GPU gate, and
[live-operations.md](live-operations.md) for relay deployment and match-day
operation.

The older `./rtgs bootstrap`, `start`, `stop`, `status`, and `logs`
commands remain available for manually managed development pods. They install
and build inside a pod and are not the match-day path: they start more slowly,
retain more state, and cannot guarantee that the tested Git commit is the exact
runtime image.

The automated path creates a disposable Pod through RunPod's REST API, exposes
only the authenticated port-8080 gateway, attaches an optional `/workspace`
network volume for reusable model caches, downloads compact results, and
terminates the pod in a `finally` block. Use `--keep` only for deliberate
diagnostics and terminate afterward with `./rtgs cloud cleanup`.

#!/usr/bin/env python3
"""Create, validate, and always tear down disposable RTGS RunPod Pods."""

from __future__ import annotations

import argparse
import asyncio
import base64
import getpass
import json
import os
import secrets
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


RUNPOD_API = "https://rest.runpod.io/v1"
ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "rtgs" / "config.json"


def load_config() -> dict[str, Any]:
    value: dict[str, Any] = {}
    try:
        value.update(json.loads(CONFIG_PATH.read_text()))
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read {CONFIG_PATH}: {exc}") from exc
    aliases = {
        "runpod_api_key": "RUNPOD_API_KEY",
        "network_volume_id": "RUNPOD_NETWORK_VOLUME_ID",
        "gpu_image": "RTGS_GPU_IMAGE",
        "container_registry_auth_id": "RUNPOD_CONTAINER_REGISTRY_AUTH_ID",
        "gpu_type_ids": "RUNPOD_GPU_TYPE_IDS",
        "relay_publish_url": "RTGS_RELAY_PUBLISH_URL",
        "relay_read_url": "RTGS_RELAY_READ_URL",
        "roboflow_api_key": "ROBOFLOW_API_KEY",
    }
    for key, environment in aliases.items():
        if os.environ.get(environment):
            value[key] = os.environ[environment]
    return value


def configure() -> None:
    current = load_config()
    fields = [
        ("runpod_api_key", "RunPod API key", True),
        ("network_volume_id", "RunPod model-cache network volume ID", False),
        ("gpu_image", "GPU image, optionally containing {sha}", False),
        ("container_registry_auth_id", "RunPod container registry auth ID (blank for public GHCR)", False),
        ("gpu_type_ids", "Comma-separated GPU type IDs", False),
        ("relay_publish_url", "Phone RTMPS publish URL", True),
        ("relay_read_url", "RunPod RTMPS read URL", True),
        ("roboflow_api_key", "Roboflow API key", True),
    ]
    for key, label, secret in fields:
        existing = str(current.get(key, ""))
        prompt = f"{label}{' [configured]' if existing and secret else f' [{existing}]' if existing else ''}: "
        entered = getpass.getpass(prompt) if secret else input(prompt)
        if entered:
            current[key] = entered.strip()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(current, indent=2) + "\n")
    CONFIG_PATH.chmod(0o600)
    print(f"Saved RTGS cloud configuration to {CONFIG_PATH}")


class RunPodClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{RUNPOD_API}{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"RunPod {method} {path} failed ({exc.code}): {detail}") from exc

    def create(self, config: dict[str, Any], mode: str, run_id: str, operator_token: str) -> dict[str, Any]:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        image = str(config.get("gpu_image", "ghcr.io/elleowo/realtimegamestatistics:{sha}")).replace("{sha}", sha)
        body: dict[str, Any] = {
            "name": f"rtgs-{run_id}",
            "computeType": "GPU",
            "cloudType": str(config.get("cloud_type", "SECURE")),
            "gpuCount": 1,
            "containerDiskInGb": int(config.get("container_disk_gb", 30)),
            "ports": ["8080/http"],
            "supportPublicIp": True,
            "imageName": image,
            "env": {
                "RTGS_MODE": mode,
                "RTGS_RUN_ID": run_id,
                "RTGS_ARTIFACT_POLICY": "compact",
                "RTGS_OPERATOR_USER": "rtgs",
                "RTGS_OPERATOR_TOKEN": operator_token,
                "RTGS_TEST_TOKEN": operator_token,
                "RTGS_RELAY_READ_URL": config["relay_read_url"],
                "ROBOFLOW_API_KEY": config["roboflow_api_key"],
                "PROCESS_EVERY": str(config.get("process_every", 3)),
                "INFER_SCALE": str(config.get("infer_scale", 0.5)),
                "HEADLESS": "1",
                "HF_HOME": "/workspace/cache/huggingface",
            },
        }
        if config.get("container_registry_auth_id"):
            body["containerRegistryAuthId"] = config["container_registry_auth_id"]
        if config.get("network_volume_id"):
            body["networkVolumeId"] = config["network_volume_id"]
            body["volumeMountPath"] = "/workspace"
        gpu_types = [item.strip() for item in str(config.get("gpu_type_ids", "NVIDIA GeForce RTX 4090")).split(",") if item.strip()]
        body["gpuTypeIds"] = gpu_types
        result = self.request("POST", "/pods", body)
        if not isinstance(result, dict) or not result.get("id"):
            raise RuntimeError(f"RunPod returned an invalid create response: {result}")
        return result

    def delete(self, pod_id: str) -> None:
        self.request("DELETE", f"/pods/{pod_id}")

    def pods(self) -> list[dict[str, Any]]:
        result = self.request("GET", "/pods")
        return result if isinstance(result, list) else result.get("items", []) if isinstance(result, dict) else []


class RTGSHTTP:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        basic = base64.b64encode(f"rtgs:{token}".encode()).decode()
        self.headers = {"Authorization": f"Basic {basic}"}
        self.token = token

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 900) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {**self.headers, "X-RTGS-Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw and "json" in response.headers.get("content-type", "") else raw
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"RTGS {method} {path} failed ({exc.code}): {exc.read().decode(errors='replace')}") from exc

    def upload(self, path: str, clip: Path) -> Any:
        boundary = f"----rtgs{secrets.token_hex(12)}"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"clip\"; filename=\"{clip.name}\"\r\n"
            "Content-Type: video/mp4\r\n\r\n"
        ).encode() + clip.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=body, method="POST",
            headers={**self.headers, "Content-Type": f"multipart/form-data; boundary={boundary}", "X-RTGS-Test-Token": self.token},
        )
        # The test API uses a bearer token in addition to gateway Basic auth.
        request.add_header("Authorization", f"Basic {base64.b64encode(f'rtgs:{self.token}'.encode()).decode()}")
        request.add_header("X-RTGS-Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read())

    def download(self, path: str, destination: Path) -> None:
        request = urllib.request.Request(f"{self.base_url}{path}", headers={**self.headers, "X-RTGS-Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(request, timeout=300) as response:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.read())


def wait_http(url: str, timeout_seconds: int = 600) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(3)
    raise TimeoutError(f"Timed out waiting for {url}")


def assert_clean_commit() -> str:
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if status.strip() and os.environ.get("RTGS_ALLOW_DIRTY_CLOUD_TEST") != "1":
        raise RuntimeError("Cloud tests use a commit-tagged image. Commit/push changes first, or set RTGS_ALLOW_DIRTY_CLOUD_TEST=1 deliberately.")
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def postgame_smoke(http: RTGSHTTP, clip: Path, manifest: dict[str, Any], output: Path) -> str:
    print("Uploading private smoke clip…")
    http.upload("/api/test/upload", clip)
    match = http.request("POST", "/api/v1/matches/import", {"filename": clip.name})
    match_id = match["id"]
    duration = int(match["duration_ms"])
    setup = manifest.get("setup", {})
    http.request("PATCH", f"/api/v1/matches/{match_id}/setup", {
        "home_team": setup.get("home_team", "USask"),
        "away_team": setup.get("away_team", "Opponent"),
        "home_score": int(setup.get("home_score", 0)),
        "away_score": int(setup.get("away_score", 0)),
        "usask_side": setup.get("usask_side", "home"),
        "periods": setup.get("periods", [{"number": 1, "start_ms": 0, "end_ms": duration}]),
        "directions": setup.get("directions", {"1": "right"}),
    })
    print("Running GPU team preflight…")
    http.request("POST", f"/api/v1/matches/{match_id}/preflight")
    http.request("PATCH", f"/api/v1/matches/{match_id}/team-mapping", {"usask_cluster": int(setup.get("usask_cluster", 0))})
    http.request("POST", f"/api/v1/matches/{match_id}/analysis")
    deadline = time.monotonic() + 1200
    while time.monotonic() < deadline:
        current = http.request("GET", f"/api/v1/matches/{match_id}")
        state = current["latest_job"]["state"]
        print(f"\rPost-game {state}: {current['latest_job']['progress'] * 100:5.1f}%", end="", flush=True)
        if state == "completed":
            print()
            break
        if state in {"failed", "cancelled", "interrupted"}:
            raise RuntimeError(f"Post-game smoke failed: {current['latest_job']}")
        time.sleep(3)
    else:
        raise TimeoutError("Post-game smoke exceeded 20 minutes")
    job = current["latest_job"]
    minimum_calibration = float(manifest.get("minimum_calibration_coverage", 0.7))
    if job["calibration_coverage"] < minimum_calibration:
        raise RuntimeError(f"Calibration coverage {job['calibration_coverage']:.2f} is below {minimum_calibration:.2f}")
    http.download(f"/api/test/runs/{match_id}/artifacts", output / "postgame-artifacts.zip")
    return match_id


async def live_websocket_smoke(base_url: str, token: str, publisher: subprocess.Popen[bytes]) -> dict[str, Any]:
    import websockets

    uri = base_url.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
    authorization = "Basic " + base64.b64encode(f"rtgs:{token}".encode()).decode()
    import inspect
    header_name = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
    context = websockets.connect(uri, **{header_name: {"Authorization": authorization}})
    frame_arrivals: dict[int, float] = {}
    processing: list[float] = []
    started = time.monotonic()
    async with context as websocket:
        await websocket.send(json.dumps({"type": "match.reset", "command_id": "reset", "payload": {}}))
        await websocket.send(json.dumps({"type": "match.set_phase", "command_id": "phase", "payload": {"phase": "first_half"}}))
        while time.monotonic() - started < 50 and publisher.poll() is None:
            try:
                value = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))
            except asyncio.TimeoutError:
                continue
            if value.get("schema_version") != 2:
                continue
            frame_arrivals[int(value["frame"]["id"])] = time.monotonic()
            latency = value.get("runtime", {}).get("processing_latency_ms")
            if latency is not None:
                processing.append(float(latency))
        await websocket.send(json.dumps({"type": "match.set_phase", "command_id": "finish", "payload": {"phase": "full_time"}}))
    elapsed = max(time.monotonic() - started, 0.001)
    fps = len(frame_arrivals) / elapsed
    if fps < 8:
        raise RuntimeError(f"Live payload rate {fps:.1f}/s is below the 8/s acceptance gate")
    return {
        "unique_frames": len(frame_arrivals),
        "observed_seconds": elapsed,
        "payload_fps": fps,
        "processing_p95_ms": statistics.quantiles(processing, n=20)[18] if len(processing) >= 20 else max(processing, default=0),
    }


def live_smoke(http: RTGSHTTP, config: dict[str, Any], clip: Path, output: Path, base_url: str, token: str) -> None:
    print("Publishing the same clip through the real RTMPS live path…")
    publisher = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-re", "-i", str(clip),
        "-c:v", "copy", "-an", "-f", "flv", config["relay_publish_url"],
    ])
    try:
        wait_http(f"{base_url}/healthz/ready", timeout_seconds=180)
        metrics = asyncio.run(live_websocket_smoke(base_url, token, publisher))
        (output / "live-smoke.json").write_text(json.dumps(metrics, indent=2) + "\n")
    finally:
        if publisher.poll() is None:
            publisher.terminate()
            publisher.wait(timeout=10)
    http.download("/api/live/artifacts", output / "live-artifacts.zip")


def create_pod(config: dict[str, Any], mode: str) -> tuple[RunPodClient, dict[str, Any], str, str]:
    required = ("runpod_api_key", "relay_read_url", "roboflow_api_key")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise RuntimeError(f"Missing cloud configuration: {', '.join(missing)}. Run './rtgs cloud configure'.")
    run_id = time.strftime("%Y%m%d-%H%M%S")
    operator_token = secrets.token_urlsafe(18)
    client = RunPodClient(config["runpod_api_key"])
    pod = client.create(config, mode, run_id, operator_token)
    base_url = f"https://{pod['id']}-8080.proxy.runpod.net"
    print(f"Created RunPod {pod['id']}; waiting for the gateway…")
    wait_http(f"{base_url}/healthz", timeout_seconds=900)
    return client, pod, base_url, operator_token


def cloud_test(args: argparse.Namespace) -> None:
    commit = assert_clean_commit()
    config = load_config()
    clip = args.clip.resolve()
    if not clip.is_file():
        raise RuntimeError(f"Smoke clip does not exist: {clip}")
    manifest = json.loads(args.manifest.read_text()) if args.manifest else {}
    output = ROOT / "downloads" / f"cloud-{time.strftime('%Y%m%d-%H%M%S')}-{commit}"
    output.mkdir(parents=True, exist_ok=True)
    client, pod, base_url, token = create_pod(config, "test")
    http = RTGSHTTP(base_url, token)
    try:
        print(f"Dashboard: {base_url}  user: rtgs  password: {token}")
        postgame_smoke(http, clip, manifest, output)
        live_smoke(http, config, clip, output, base_url, token)
        print(f"Cloud smoke passed. Artifacts: {output}")
    finally:
        if args.keep:
            print(f"Keeping pod {pod['id']} because --keep was supplied.")
        else:
            client.delete(pod["id"])
            print(f"Terminated pod {pod['id']}.")


def cloud_live(args: argparse.Namespace) -> None:
    assert_clean_commit()
    config = load_config()
    output = ROOT / "downloads" / f"live-{time.strftime('%Y%m%d-%H%M%S')}"
    output.mkdir(parents=True, exist_ok=True)
    client, pod, base_url, token = create_pod(config, "live")
    http = RTGSHTTP(base_url, token)
    print(f"Dashboard: {base_url}")
    print(f"Operator login: rtgs / {token}")
    print("The phone can keep using its configured stable relay URL. Waiting for full-time…")
    try:
        deadline = time.monotonic() + args.max_minutes * 60
        while time.monotonic() < deadline:
            try:
                status = http.request("GET", "/api/live/status", timeout=20)
                phase = status.get("match", {}).get("phase")
                print(f"\r{status.get('source_state', 'starting'):12s} phase={phase or '—':12s} last-frame={status.get('last_frame_age_ms')} ms", end="", flush=True)
                if phase == "full_time":
                    print()
                    break
            except (OSError, RuntimeError):
                pass
            time.sleep(5)
        http.download("/api/live/artifacts", output / "live-artifacts.zip")
        print(f"Live artifacts downloaded to {output}")
    finally:
        if args.keep:
            print(f"Keeping pod {pod['id']} because --keep was supplied.")
        else:
            client.delete(pod["id"])
            print(f"Terminated pod {pod['id']}.")


def cleanup_pods(args: argparse.Namespace) -> None:
    config = load_config()
    if not config.get("runpod_api_key"):
        raise RuntimeError("RUNPOD_API_KEY is not configured")
    client = RunPodClient(config["runpod_api_key"])
    pods = [pod for pod in client.pods() if str(pod.get("name", "")).startswith("rtgs-")]
    if not pods:
        print("No RTGS pods are present.")
        return
    for pod in pods:
        print(f"{pod.get('id')}  {pod.get('name')}  {pod.get('desiredStatus') or pod.get('status')}")
    if not args.yes and input(f"Terminate these {len(pods)} RTGS pod(s)? [y/N] ").strip().lower() != "y":
        print("No pods were changed.")
        return
    for pod in pods:
        client.delete(str(pod["id"]))
        print(f"Terminated {pod['id']}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="RTGS disposable RunPod lifecycle")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("configure")
    test = commands.add_parser("test")
    test.add_argument("--clip", type=Path, required=True)
    test.add_argument("--manifest", type=Path)
    test.add_argument("--keep", action="store_true")
    live = commands.add_parser("live")
    live.add_argument("--max-minutes", type=int, default=180)
    live.add_argument("--keep", action="store_true")
    cleanup = commands.add_parser("cleanup")
    cleanup.add_argument("--yes", action="store_true")
    soak = commands.add_parser("soak")
    soak.add_argument("--video", dest="clip", type=Path, required=True)
    soak.add_argument("--manifest", type=Path)
    soak.add_argument("--keep", action="store_true")
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "configure":
        configure()
    elif args.command in {"test", "soak"}:
        cloud_test(args)
    elif args.command == "live":
        cloud_live(args)
    elif args.command == "cleanup":
        cleanup_pods(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

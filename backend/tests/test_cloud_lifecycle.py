from argparse import Namespace
from pathlib import Path

import pytest

import scripts.cloud as cloud


def test_runpod_create_uses_exact_commit_image_and_cache_volume(monkeypatch) -> None:
    monkeypatch.setattr(
        cloud.subprocess,
        "check_output",
        lambda *_args, **_kwargs: "abc123def456\n",
    )
    captured = {}
    client = cloud.RunPodClient("private-key")

    def request(method, path, payload=None):
        captured.update(method=method, path=path, payload=payload)
        return {"id": "pod-1"}

    monkeypatch.setattr(client, "request", request)
    client.create(
        {
            "gpu_image": "ghcr.io/example/rtgs:{sha}",
            "network_volume_id": "volume-1",
            "relay_read_url": "rtmps://relay/live?user=reader&pass=secret",
            "roboflow_api_key": "rf-secret",
        },
        mode="live",
        run_id="run-1",
        operator_token="operator-secret",
    )

    body = captured["payload"]
    assert (captured["method"], captured["path"]) == ("POST", "/pods")
    assert body["imageName"] == "ghcr.io/example/rtgs:abc123def456"
    assert "templateId" not in body
    assert body["networkVolumeId"] == "volume-1"
    assert body["volumeMountPath"] == "/workspace"
    assert body["ports"] == ["8080/http"]
    assert body["env"]["RTGS_MODE"] == "live"


def test_cloud_test_terminates_pod_when_smoke_fails(tmp_path, monkeypatch) -> None:
    clip = tmp_path / "smoke.mp4"
    clip.write_bytes(b"private-smoke")

    class Client:
        deleted: list[str] = []

        def delete(self, pod_id: str) -> None:
            self.deleted.append(pod_id)

    client = Client()
    monkeypatch.setattr(cloud, "ROOT", tmp_path)
    monkeypatch.setattr(cloud, "assert_clean_commit", lambda: "abc123")
    monkeypatch.setattr(cloud, "load_config", lambda: {})
    monkeypatch.setattr(
        cloud,
        "create_pod",
        lambda _config, _mode: (client, {"id": "pod-failed"}, "https://pod.example", "token"),
    )
    monkeypatch.setattr(cloud, "postgame_smoke", lambda *_args: (_ for _ in ()).throw(RuntimeError("smoke failed")))

    with pytest.raises(RuntimeError, match="smoke failed"):
        cloud.cloud_test(Namespace(clip=clip, manifest=None, keep=False))

    assert client.deleted == ["pod-failed"]

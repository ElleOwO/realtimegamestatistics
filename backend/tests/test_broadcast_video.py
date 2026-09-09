"""Synthetic media only: exercise the real decoder and packet remuxer on CPU."""
import time
import uuid

import av
import numpy as np

from broadcast_source import BroadcastSource
from canadawest import Playback
from packet_ring import PacketRing


def make_video(path):
    with av.open(str(path), "w") as output:
        stream = output.add_stream("libx264", rate=10)
        stream.width, stream.height, stream.pix_fmt = 160, 96, "yuv420p"
        stream.options = {"g": "10", "bf": "0"}
        for index in range(40):
            frame = av.VideoFrame.from_ndarray(np.full((96, 160, 3), index * 5, np.uint8), format="bgr24")
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)


def test_one_decoder_produces_frames_and_finalized_clip(tmp_path):
    path = tmp_path / "synthetic.mp4"
    make_video(path)
    ring = PacketRing(tmp_path)
    event_id = str(uuid.uuid4())
    ring.preserve(event_id, 1500)
    class Connector:
        opens = 0
        closed = False
        def refresh(self):
            self.opens += 1
            return Playback(str(path))
        def close(self):
            self.closed = True
    connector = Connector()
    source = BroadcastSource(connector, ring=ring)
    source.start()
    deadline = time.monotonic() + 5
    latest = None
    while time.monotonic() < deadline:
        frame = source.read(timeout=.1)
        if frame:
            latest = frame
        if latest and latest.timestamp_ms >= 3900:
            break
    source.close()
    assert connector.opens == 1
    assert connector.closed
    assert latest is not None and latest.timestamp_ms == 3900
    assert not ring.ring.exists()
    clip = tmp_path / "live-clips" / f"{event_id}.mp4"
    with av.open(str(clip)) as result:
        assert len(list(result.decode(video=0))) >= 30

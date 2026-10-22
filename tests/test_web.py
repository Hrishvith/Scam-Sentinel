"""Browser audio worklet maths, run in Node with stand-ins (skipped if Node is missing)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")


@pytest.mark.skipif(not NODE, reason="Node.js not installed")
@pytest.mark.parametrize("device_rate", [48000, 44100, 16000])
def test_worklet_resamples_to_16k_frames_and_back(device_rate):
    out = subprocess.run([NODE, str(Path(__file__).with_name("worklet_check.mjs")), str(device_rate)],
                         capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    assert r["frame_bytes"] == 640                              # 20 ms of 16 kHz s16le
    assert abs(r["net_seconds"] - 1.0) < 0.03                   # no samples lost or invented
    assert abs(r["net_hz"] - 440) < 5 and 15000 < r["net_peak"] < 17000   # same tone, same level
    assert abs(r["played_hz"] - 440) < 5 and 0.45 < r["played_peak"] < 0.55
    assert 0.10 < r["ducked_peak"] < 0.15                       # warning ducks the call to 25%

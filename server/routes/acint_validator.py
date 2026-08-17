import base64
import hashlib
import json
from typing import Any


MAX_TIME_DRIFT_SECONDS = 300


class ACIntError(Exception):
    pass


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _verify_timestamps(t0: Any, t1: Any, t2: Any) -> None:
    import time

    now_ms = int(time.time() * 1000)

    if not isinstance(t0, int):
        raise ACIntError("t0 must be an integer.")

    drift_ms = abs(now_ms - t0)
    if drift_ms > MAX_TIME_DRIFT_SECONDS * 1000:
        raise ACIntError(f"Timestamp drift too large: {drift_ms}ms.")

    if not isinstance(t1, int) or not (0 <= t1 <= 4294967295):
        raise ACIntError("t1 out of Uint32 range.")

    if not isinstance(t2, int) or not (31 <= t2 <= 60):
        raise ACIntError("t2 out of acceptable range.")


def _verify_fingerprint(fp_list: Any) -> dict:
    if not isinstance(fp_list, list) or len(fp_list) == 0:
        raise ACIntError("Fingerprint slot is empty or malformed.")

    fp_data = fp_list[0]
    if isinstance(fp_data, dict):
        fp = fp_data
    elif isinstance(fp_data, str):
        try:
            fp = json.loads(fp_data)
        except Exception as exc:
            raise ACIntError(f"Fingerprint JSON parse failed: {exc}") from exc
    else:
        raise ACIntError(f"Fingerprint must be dict or string, got {type(fp_data)}")

    required_keys = {"hc", "mem", "lang", "tz", "sw", "sh", "cd", "touch", "canvas", "webgl"}
    missing = required_keys - fp.keys()
    if missing:
        raise ACIntError(f"Fingerprint missing keys: {missing}")

    if not isinstance(fp.get("sw"), int) or not (320 <= fp["sw"] <= 7680):
        raise ACIntError("Screen width out of realistic range.")
    if not isinstance(fp.get("sh"), int) or not (240 <= fp["sh"] <= 4320):
        raise ACIntError("Screen height out of realistic range.")
    if not isinstance(fp.get("hc"), int) or not (1 <= fp["hc"] <= 256):
        raise ACIntError("Hardware concurrency out of realistic range.")

    return fp


def _decode_legacy_packet(encoded_packet) -> list:
    try:
        import msgpack
        import lzstring
    except Exception as exc:
        raise ACIntError(f"Legacy ACInt support unavailable: {exc}") from exc

    if isinstance(encoded_packet, str):
        try:
            packet_bytes = base64.b64decode(encoded_packet)
        except Exception:
            packet_bytes = encoded_packet.encode("utf-8")
    else:
        packet_bytes = bytes(encoded_packet)

    try:
        packet = msgpack.unpackb(packet_bytes, raw=False)
    except Exception as exc:
        raise ACIntError(f"Legacy msgpack decode failed: {exc}") from exc

    if not isinstance(packet, list) or len(packet) != 4:
        raise ACIntError(f"Packet structure invalid: expected list of 4, got {type(packet)}")

    return packet


def validate_acint(ac_int: list) -> dict:
    if not isinstance(ac_int, list) or len(ac_int) != 2:
        raise ACIntError("ACInt must be a list of length 2.")

    time_hash = ac_int[0]
    packet = ac_int[1]

    if isinstance(packet, list):
        if len(packet) != 4:
            raise ACIntError("Packet structure invalid: expected list of 4.")
        t0, t1, t2, fp_list = packet
    else:
        t0, t1, t2, fp_list = _decode_legacy_packet(packet)

    _verify_timestamps(t0, t1, t2)
    fp = _verify_fingerprint(fp_list)

    expected_hash = _sha256(f"{t0}:{t1}:{t2}")
    if not isinstance(time_hash, str) or len(time_hash) != 64:
        raise ACIntError("time_hash format invalid.")
    if time_hash != expected_hash:
        raise ACIntError("time_hash mismatch.")

    return {
        "timestamp": t0,
        "fingerprint": fp,
    }

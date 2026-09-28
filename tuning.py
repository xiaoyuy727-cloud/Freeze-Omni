"""Runtime-tunable turn-taking parameters (hot reloaded).

Edit ./tuning.json while a dialogue is running: the new values take effect
within ~2 seconds, no restart needed. See TUNING.md for the meaning of each key.

Usage:
    from tuning import get as get_tuning
    th1 = get_tuning('state_th1', 0.5)
"""

import json
import os
import threading
import time

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tuning.json")

# seconds between checks of the file mtime, so the 160ms inference loop does not
# stat() the file on every single chunk
_RELOAD_INTERVAL = 2.0

DEFAULTS = {
    "state_th1": 0.5,            # "it's my turn to speak" threshold
    "state_th2": 0.5,            # "user is done / nothing to answer" threshold
    "vad_threshold": 0.8,        # silero VAD speech probability
    "vad_min_silence_ms": 2000,  # silence needed to call the utterance over
    "vad_speech_pad_ms": 30,     # padding added around detected speech
}

_lock = threading.Lock()
_cache = {}
_cache_mtime = None
_last_check = 0.0


def _refresh():
    global _cache, _cache_mtime, _last_check
    now = time.time()
    if now - _last_check < _RELOAD_INTERVAL:
        return
    _last_check = now
    try:
        mtime = os.path.getmtime(_PATH)
    except OSError:
        return
    if mtime == _cache_mtime:
        return
    try:
        with open(_PATH) as fin:
            data = json.load(fin)
    except Exception as e:
        print("[tuning] tuning.json unreadable, keeping previous values: %s" % e)
        return
    if not isinstance(data, dict):
        print("[tuning] tuning.json must be a JSON object, keeping previous values")
        return
    old = dict(_cache)
    _cache = data
    _cache_mtime = mtime
    print("[tuning] reloaded: %s (was: %s)" % (data, old))


def get(key, default=None):
    """Current value of `key`, falling back to tuning.json defaults then `default`."""
    with _lock:
        _refresh()
        val = _cache.get(key, DEFAULTS.get(key, default))
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        # a typo in tuning.json must never kill a live dialogue
        print("[tuning] %s=%r is not a number, using default %s"
              % (key, val, DEFAULTS.get(key, default)))
        return float(DEFAULTS.get(key, default))

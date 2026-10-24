"""Per-tenant in-process cache + DataFrame LRU."""
import hashlib
import json
import os
import threading
import time
from collections import OrderedDict

import pandas as pd

_LOCK = threading.Lock()
_RESULT_CACHE = {}
_DF_LRU = OrderedDict()
_DF_LRU_CAP = 4
_DEFAULT_TTL = 300


def _normalize_params(params):
    items = sorted((str(k), str(v)) for k, v in (params or {}).items() if v not in (None, ""))
    return hashlib.sha1(json.dumps(items).encode()).hexdigest()


def make_key(store_id, dataset_id, endpoint, params):
    return f"{store_id}:{dataset_id}:{endpoint}:{_normalize_params(params)}"


def get_or_set(key, builder, ttl=_DEFAULT_TTL):
    now = time.time()
    with _LOCK:
        entry = _RESULT_CACHE.get(key)
        if entry and entry["expires_at"] > now:
            return entry["value"]
    value = builder()
    with _LOCK:
        _RESULT_CACHE[key] = {"value": value, "expires_at": now + ttl}
    return value


def invalidate_store(store_id, dataset_id=None):
    prefix_store = f"{store_id}:"
    prefix_full = f"{store_id}:{dataset_id}:" if dataset_id else None
    with _LOCK:
        keys = list(_RESULT_CACHE.keys())
        for k in keys:
            if prefix_full and k.startswith(prefix_full):
                _RESULT_CACHE.pop(k, None)
            elif not prefix_full and k.startswith(prefix_store):
                _RESULT_CACHE.pop(k, None)
        df_keys = list(_DF_LRU.keys())
        for k in df_keys:
            sid, did = k
            if sid == store_id and (dataset_id is None or did == dataset_id):
                _DF_LRU.pop(k, None)


def load_dataframe(store_id, dataset_id, parquet_path):
    cache_key = (store_id, dataset_id)
    with _LOCK:
        if cache_key in _DF_LRU:
            _DF_LRU.move_to_end(cache_key)
            return _DF_LRU[cache_key]
    if not parquet_path or not os.path.exists(parquet_path):
        return None
    df = pd.read_parquet(parquet_path)
    with _LOCK:
        _DF_LRU[cache_key] = df
        _DF_LRU.move_to_end(cache_key)
        while len(_DF_LRU) > _DF_LRU_CAP:
            _DF_LRU.popitem(last=False)
    return df

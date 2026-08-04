from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd

# Fuso oficial utilizado pelo aplicativo. Para Rio Grande do Sul e a maior
# parte do Brasil, America/Sao_Paulo corresponde atualmente a UTC-03:00.
APP_TIMEZONE_NAME = "America/Sao_Paulo"
_FALLBACK_TIMEZONE = timezone(timedelta(hours=-3), name="BRT")


def app_timezone():
    """Retorna o fuso do aplicativo usando a base IANA.

    O fallback de UTC-03:00 evita que o app deixe de iniciar caso o sistema
    operacional não possua a base de fusos; a dependência ``tzdata`` também é
    declarada no projeto para garantir compatibilidade no Windows.
    """

    try:
        return ZoneInfo(APP_TIMEZONE_NAME)
    except ZoneInfoNotFoundError:
        return _FALLBACK_TIMEZONE


def local_now_iso() -> str:
    """Data e hora atuais no fuso do aplicativo, em ISO 8601 com offset."""

    return datetime.now(app_timezone()).replace(microsecond=0).isoformat()


def utc_now_iso() -> str:
    """Compatibilidade com versões anteriores.

    O nome antigo foi mantido para não quebrar importações externas, mas o
    valor retornado agora usa o fuso configurado do aplicativo.
    """

    return local_now_iso()


def timestamp_to_local_iso(value: Any) -> str:
    """Converte um timestamp ISO para ``America/Sao_Paulo``.

    Valores com offset, como ``+00:00`` ou ``Z``, são convertidos preservando o
    instante. Valores sem offset são considerados horários locais já gravados
    e apenas recebem o offset do aplicativo. Conteúdos vazios ou inválidos são
    preservados para evitar perda de dados.
    """

    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""

    text = str(value).strip()
    if not text:
        return ""

    parseable = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(parseable)
    except (TypeError, ValueError):
        return text

    target_timezone = app_timezone()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=target_timezone)
    else:
        parsed = parsed.astimezone(target_timezone)

    return parsed.replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text)


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return normalize_text(value) in {"1", "true", "sim", "s", "yes", "ativo"}


def as_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        value = value.strip().replace("R$", "").replace(" ", "")
        if "," in value and "." in value:
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", ".")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def clean_for_storage(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (np.floating, float)):
        if pd.isna(value) or not math.isfinite(float(value)):
            return ""
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return str(value) if not isinstance(value, (int, str)) else value


def dataframe_for_storage(df: pd.DataFrame) -> pd.DataFrame:
    return df.map(clean_for_storage)


def dataframe_fingerprint(*frames: pd.DataFrame, metadata: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {"metadata": metadata or {}}
    for idx, frame in enumerate(frames):
        normalized = frame.copy()
        normalized = normalized.replace({np.nan: None})
        payload[f"frame_{idx}"] = normalized.to_dict(orient="records")
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def format_brl(value: float | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    formatted = f"{float(value):,.{decimals}f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def safe_filename(value: str, fallback: str = "arquivo") -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", normalized).strip("_")
    return normalized or fallback

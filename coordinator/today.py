import json
import threading
from gzip import decompress
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from zlib import decompress as decompress_deflate, error as DeflateError


LOCATIONFORECAST_URL = (
    "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    "?lat=58.4108&lon=15.6214"
)
TIME_ZONE = "Europe/Stockholm"
USER_AGENT = "CortexHome/1.0 github.com/FelixFolkebrant/cortex-home"
MAX_RESPONSE_BYTES = 1_048_576
REFRESH_INTERVAL_SECONDS = 60


class TodayUnavailable(Exception):
    pass


class TodayAdapter:
    def __init__(self, cache_path, report, opener=urlopen, now=None):
        self.cache_path = Path(cache_path)
        self.report = report
        self.opener = opener
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, name="today", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def refresh(self):
        cached = self._read_cache()
        if cached and self._cache_is_fresh(cached):
            return normalize_forecast(cached["forecast"])

        request = Request(
            LOCATIONFORECAST_URL,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
                **(
                    {"If-Modified-Since": cached["lastModified"]}
                    if cached and cached.get("lastModified")
                    else {}
                ),
            },
        )
        try:
            response = self.opener(request, timeout=10)
        except HTTPError as error:
            if error.code == 304 and cached:
                cache = {
                    **cached,
                    "expires": error.headers.get("Expires", cached["expires"]),
                    "lastModified": error.headers.get(
                        "Last-Modified", cached.get("lastModified")
                    ),
                }
                self._write_cache(cache)
                return normalize_forecast(cache["forecast"])
            raise TodayUnavailable from error
        except (OSError, URLError, TimeoutError):
            raise TodayUnavailable from None

        with response:
            if response.status not in {200, 203}:
                raise TodayUnavailable
            if response.status == 203:
                raise TodayUnavailable
            encoded = response.read(MAX_RESPONSE_BYTES + 1)
            if len(encoded) > MAX_RESPONSE_BYTES:
                raise TodayUnavailable
            encoding = response.headers.get("Content-Encoding")
            if encoding == "gzip":
                try:
                    encoded = decompress(encoded)
                except OSError:
                    raise TodayUnavailable from None
                if len(encoded) > MAX_RESPONSE_BYTES:
                    raise TodayUnavailable
            elif encoding == "deflate":
                try:
                    encoded = decompress_deflate(encoded)
                except (OSError, DeflateError):
                    raise TodayUnavailable from None
                if len(encoded) > MAX_RESPONSE_BYTES:
                    raise TodayUnavailable
            try:
                forecast = json.loads(encoded)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise TodayUnavailable from None
            expires = response.headers.get("Expires")
            if not expires:
                raise TodayUnavailable
            cache = {
                "expires": expires,
                "forecast": forecast,
                "lastModified": response.headers.get("Last-Modified"),
            }

        summary = normalize_forecast(forecast)
        self._write_cache(cache)
        return summary

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.report(self.refresh())
            except TodayUnavailable:
                self.report(unavailable_summary())
            self.stop_event.wait(REFRESH_INTERVAL_SECONDS)

    def _read_cache(self):
        try:
            cache = json.loads(self.cache_path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(cache, dict) or not isinstance(cache.get("forecast"), dict):
            return None
        return cache

    def _cache_is_fresh(self, cache):
        try:
            expires = datetime.strptime(
                cache["expires"], "%a, %d %b %Y %H:%M:%S %Z"
            ).replace(tzinfo=timezone.utc)
        except (KeyError, TypeError, ValueError):
            return False
        return self.now() < expires

    def _write_cache(self, cache):
        try:
            self.cache_path.parent.mkdir(mode=0o770, parents=True, exist_ok=True)
            temporary = self.cache_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(cache, separators=(",", ":")))
            temporary.replace(self.cache_path)
        except OSError:
            pass


def normalize_forecast(forecast):
    try:
        series = forecast["properties"]["timeseries"]
        if not isinstance(series, list) or not series:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise TodayUnavailable from None

    local_zone = ZoneInfo(TIME_ZONE)
    days = {}
    for raw_entry in series:
        try:
            local_day = (
                datetime.fromisoformat(raw_entry["time"].replace("Z", "+00:00"))
                .astimezone(local_zone)
                .date()
                .isoformat()
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            raise TodayUnavailable from None
        if local_day not in days and len(days) == 3:
            break
        try:
            entry = normalize_entry(raw_entry)
        except (KeyError, TypeError, ValueError):
            raise TodayUnavailable from None
        days.setdefault(local_day, []).append(entry)

    current = next(iter(days.values()), [None])[0]
    if current is None:
        raise TodayUnavailable

    forecast_days = []
    for day, entries_for_day in list(days.items())[:3]:
        noon_entry = min(
            entries_for_day,
            key=lambda entry: abs(entry["time"].astimezone(local_zone).hour - 12),
        )
        forecast_days.append(
            {
                "condition": noon_entry["condition"],
                "date": day,
                "highC": max(entry["temperatureC"] for entry in entries_for_day),
                "lowC": min(entry["temperatureC"] for entry in entries_for_day),
            }
        )

    if len(forecast_days) != 3:
        raise TodayUnavailable
    return {
        "status": "available",
        "timeZone": TIME_ZONE,
        "current": {
            "condition": current["condition"],
            "temperatureC": current["temperatureC"],
        },
        "forecast": forecast_days,
    }


def unavailable_summary():
    return {
        "status": "unavailable",
        "timeZone": TIME_ZONE,
        "current": None,
        "forecast": [],
    }


def normalize_entry(entry):
    time = datetime.fromisoformat(entry["time"].replace("Z", "+00:00"))
    temperature = entry["data"]["instant"]["details"]["air_temperature"]
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ValueError
    condition = next(
        (
            entry["data"][period]["summary"]["symbol_code"]
            for period in ("next_1_hours", "next_6_hours", "next_12_hours")
            if period in entry["data"]
            and isinstance(entry["data"][period].get("summary"), dict)
        ),
        None,
    )
    if not isinstance(condition, str):
        raise ValueError
    return {
        "condition": normalize_condition(condition),
        "temperatureC": round(temperature),
        "time": time,
    }


def normalize_condition(symbol_code):
    if "thunder" in symbol_code:
        return "thunderstorm"
    if "sleet" in symbol_code:
        return "sleet"
    if "snow" in symbol_code:
        return "snow"
    if "rain" in symbol_code or "showers" in symbol_code:
        return "rain"
    if "fog" in symbol_code:
        return "fog"
    if "partlycloudy" in symbol_code:
        return "partly_cloudy"
    if "cloudy" in symbol_code:
        return "cloudy"
    if "clearsky" in symbol_code or "fair" in symbol_code:
        return "clear"
    return "unknown"

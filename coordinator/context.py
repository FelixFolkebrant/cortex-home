TODAY_SURFACE = "today"
MUSIC_SURFACE = "music"
STATUSES = {"available", "unavailable"}
PLAYBACK_STATES = {"paused", "playing", "stopped", "unavailable"}


def build_room_context(today, music, lighting):
    context = build_answer_context(today, music)
    context["lighting"] = project_lighting(lighting)
    return context


def build_answer_context(today, music):
    return {
        "home": {
            "today": project_today(today),
            "music": project_music(music),
        }
    }


def project_today(snapshot):
    if (
        not isinstance(snapshot, dict)
        or set(snapshot)
        != {"status", "timeZone", "current", "forecast", "observedAt"}
        or snapshot["status"] not in STATUSES
        or not isinstance(snapshot["timeZone"], str)
        or not isinstance(snapshot["observedAt"], str)
    ):
        return unavailable_surface(TODAY_SURFACE)

    if snapshot["status"] == "unavailable":
        if snapshot["current"] is not None or snapshot["forecast"] != []:
            return unavailable_surface(TODAY_SURFACE)
        return {
            "type": TODAY_SURFACE,
            "available": False,
            "timeZone": snapshot["timeZone"],
            "current": None,
            "forecast": [],
            "observedAt": snapshot["observedAt"],
        }

    current = snapshot["current"]
    forecast = snapshot["forecast"]
    if (
        not isinstance(current, dict)
        or set(current) != {"condition", "temperatureC"}
        or not isinstance(current["condition"], str)
        or not number(current["temperatureC"])
        or not isinstance(forecast, list)
    ):
        return unavailable_surface(TODAY_SURFACE)

    projected_forecast = []
    for day in forecast:
        if (
            not isinstance(day, dict)
            or set(day) != {"condition", "date", "highC", "lowC"}
            or not isinstance(day["condition"], str)
            or not isinstance(day["date"], str)
            or not number(day["highC"])
            or not number(day["lowC"])
        ):
            return unavailable_surface(TODAY_SURFACE)
        projected_forecast.append(
            {
                "condition": day["condition"],
                "date": day["date"],
                "highC": day["highC"],
                "lowC": day["lowC"],
            }
        )

    return {
        "type": TODAY_SURFACE,
        "available": True,
        "timeZone": snapshot["timeZone"],
        "current": {
            "condition": current["condition"],
            "temperatureC": current["temperatureC"],
        },
        "forecast": projected_forecast,
        "observedAt": snapshot["observedAt"],
    }


def project_music(snapshot):
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != {"status", "item", "positionMs", "observedAt"}
        or snapshot["status"] not in PLAYBACK_STATES
        or not integer(snapshot["positionMs"])
        or not isinstance(snapshot["observedAt"], str)
    ):
        return unavailable_surface(MUSIC_SURFACE)

    if snapshot["status"] == "unavailable":
        if snapshot["item"] is not None or snapshot["positionMs"] != 0:
            return unavailable_surface(MUSIC_SURFACE)
        return {
            "type": MUSIC_SURFACE,
            "available": False,
            "playbackState": "unavailable",
            "observedAt": snapshot["observedAt"],
        }

    if snapshot["status"] == "stopped":
        if snapshot["item"] is not None or snapshot["positionMs"] != 0:
            return unavailable_surface(MUSIC_SURFACE)
        return {
            "type": MUSIC_SURFACE,
            "available": True,
            "playbackState": "stopped",
            "observedAt": snapshot["observedAt"],
        }

    item = snapshot["item"]
    if (
        not isinstance(item, dict)
        or set(item)
        != {
            "artworkUrl",
            "collection",
            "creators",
            "durationMs",
            "title",
            "type",
            "uri",
        }
        or item["type"] not in {"episode", "track"}
        or not isinstance(item["title"], str)
        or not isinstance(item["collection"], str)
        or not isinstance(item["creators"], list)
        or not all(isinstance(creator, str) for creator in item["creators"])
        or not integer(item["durationMs"])
        or snapshot["positionMs"] > item["durationMs"]
    ):
        return unavailable_surface(MUSIC_SURFACE)

    return {
        "type": MUSIC_SURFACE,
        "available": True,
        "playbackState": snapshot["status"],
        "itemType": item["type"],
        "title": item["title"],
        "creators": list(item["creators"]),
        "collection": item["collection"],
        "positionMs": snapshot["positionMs"],
        "durationMs": item["durationMs"],
        "observedAt": snapshot["observedAt"],
    }


def project_lighting(snapshot):
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != {"status", "scenes", "activeScenes", "observedAt"}
        or snapshot["status"] not in STATUSES
        or not isinstance(snapshot["scenes"], list)
        or not all(isinstance(scene, str) for scene in snapshot["scenes"])
        or not isinstance(snapshot["activeScenes"], list)
        or not all(isinstance(scene, str) for scene in snapshot["activeScenes"])
        or not isinstance(snapshot["observedAt"], str)
    ):
        return unavailable_lighting()

    if (
        snapshot["status"] == "unavailable"
        and (snapshot["scenes"] or snapshot["activeScenes"])
    ):
        return unavailable_lighting()

    if snapshot["activeScenes"] != [
        scene for scene in snapshot["scenes"] if scene in snapshot["activeScenes"]
    ]:
        return unavailable_lighting()

    return {
        "available": snapshot["status"] == "available",
        "scenes": list(snapshot["scenes"]),
        "activeScenes": list(snapshot["activeScenes"]),
        "observedAt": snapshot["observedAt"],
    }


def unavailable_surface(surface_type):
    return {"type": surface_type, "available": False}


def unavailable_lighting():
    return {"available": False, "scenes": [], "activeScenes": []}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)

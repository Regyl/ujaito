from model import GreenhouseJob


def _location_name(job: dict) -> str:
    location = job.get("location")
    if isinstance(location, dict):
        return str(location.get("name") or "")
    return ""


def apply(board: str, payload: dict) -> GreenhouseJob:
    job_id = payload.get("id")
    if not isinstance(job_id, int):
        raise ValueError("job id is missing")
    return GreenhouseJob(
        source="greenhouse",
        board=board,
        job_id=job_id,
        title=str(payload.get("title") or ""),
        absolute_url=str(payload.get("absolute_url") or ""),
        location=_location_name(payload),
        content=str(payload.get("content") or ""),
        payload=dict(payload),
    )
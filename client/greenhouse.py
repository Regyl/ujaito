import json
from urllib.request import Request, urlopen

BOARD_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"


def fetch_jobs(board_token: str) -> list[dict]:
    url = BOARD_JOBS_URL.format(board_token=board_token)
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=60) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8"))
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(jobs, list):
        raise ValueError("jobs response was not a list")
    return [job for job in jobs if isinstance(job, dict)]
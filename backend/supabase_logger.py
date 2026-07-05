import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


class SupabaseLoggerError(Exception):
    pass


def _request_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise SupabaseLoggerError(f"Supabase HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        raise SupabaseLoggerError(f"Supabase network error: {str(exc)}")


def is_supabase_configured(url: str, anon_key: str) -> bool:
    return bool(url and anon_key)


def is_service_logging_configured(url: str, service_role_key: str) -> bool:
    return bool(url and service_role_key)


def sign_up_with_password(
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
) -> Dict[str, Any]:
    endpoint = f"{supabase_url.rstrip('/')}/auth/v1/signup"
    headers = {
        "apikey": anon_key,
        "Content-Type": "application/json",
    }
    return _request_json(
        "POST",
        endpoint,
        headers,
        payload={"email": email, "password": password},
    )


def sign_in_with_password(
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
) -> Dict[str, Any]:
    endpoint = f"{supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": anon_key,
        "Content-Type": "application/json",
    }
    return _request_json(
        "POST",
        endpoint,
        headers,
        payload={"email": email, "password": password},
    )


def insert_user_log(
    supabase_url: str,
    anon_key: str,
    access_token: str,
    log_payload: Dict[str, Any],
) -> None:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/agentos_logs"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    _request_json("POST", endpoint, headers, payload=log_payload)


def fetch_my_logs(
    supabase_url: str,
    anon_key: str,
    access_token: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
        }
    )
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/agentos_logs?{query}"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {access_token}",
    }
    result = _request_json("GET", endpoint, headers)
    if isinstance(result, list):
        return result
    return []


def insert_public_log(
    supabase_url: str,
    service_role_key: str,
    log_payload: Dict[str, Any],
) -> None:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/agentos_public_logs"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    _request_json("POST", endpoint, headers, payload=log_payload)


def extract_session(auth_response: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    access_token = auth_response.get("access_token")
    refresh_token = auth_response.get("refresh_token")
    user = auth_response.get("user") or {}
    user_id = user.get("id")
    return access_token, refresh_token, user_id

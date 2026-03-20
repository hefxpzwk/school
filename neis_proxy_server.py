#!/usr/bin/env python3
"""Local proxy server for NEIS Open API.

Users run this server with a private NEIS key. CLI clients call this server
without handling the key directly.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List


API_BASE_URL = "https://open.neis.go.kr/hub"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
API_SUCCESS_CODES = {"INFO-000", "INFO-200"}


class ProxyError(Exception):
    pass


def get_api_key() -> str:
    key = os.environ.get("NEIS_API_KEY", "").strip()
    if not key:
        raise ProxyError("환경변수 NEIS_API_KEY가 필요합니다.")
    return key


def api_request(endpoint: str, params: Dict[str, str], api_key: str) -> Dict[str, Any]:
    query = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": "1",
        "pSize": "100",
        **params,
    }
    url = f"{API_BASE_URL}/{endpoint}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ProxyError(f"NEIS HTTP 오류: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProxyError(f"NEIS 연결 오류: {exc.reason}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProxyError("NEIS 응답 JSON 파싱 실패") from exc


def extract_rows(payload: Dict[str, Any], top_key: str) -> List[Dict[str, Any]]:
    entries = payload.get(top_key)
    if not isinstance(entries, list):
        return []

    for entry in entries:
        if isinstance(entry, dict) and "row" in entry and isinstance(entry["row"], list):
            return [r for r in entry["row"] if isinstance(r, dict)]
    return []


def extract_result_code_message(payload: Dict[str, Any], top_key: str) -> tuple[str, str] | None:
    entries = payload.get(top_key)
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and "head" in entry and isinstance(entry["head"], list):
                for head_item in entry["head"]:
                    if isinstance(head_item, dict) and "RESULT" in head_item and isinstance(head_item["RESULT"], dict):
                        result = head_item["RESULT"]
                        code = str(result.get("CODE", "")).strip()
                        message = str(result.get("MESSAGE", "")).strip()
                        if code:
                            return code, message

    top_result = payload.get("RESULT")
    if isinstance(top_result, dict):
        code = str(top_result.get("CODE", "")).strip()
        message = str(top_result.get("MESSAGE", "")).strip()
        if code:
            return code, message
    return None


def ensure_api_result_ok(payload: Dict[str, Any], top_key: str) -> None:
    result = extract_result_code_message(payload, top_key)
    if result is None:
        return
    code, message = result
    if code not in API_SUCCESS_CODES:
        raise ProxyError(f"NEIS API 오류 ({code}): {message or '요청 실패'}")


def search_schools(query: str, api_key: str) -> List[Dict[str, str]]:
    payload = api_request("schoolInfo", {"SCHUL_NM": query}, api_key)
    ensure_api_result_ok(payload, "schoolInfo")
    rows = extract_rows(payload, "schoolInfo")
    schools: List[Dict[str, str]] = []
    for row in rows:
        school_name = str(row.get("SCHUL_NM", "")).strip()
        office_code = str(row.get("ATPT_OFCDC_SC_CODE", "")).strip()
        school_code = str(row.get("SD_SCHUL_CODE", "")).strip()
        if school_name and office_code and school_code:
            schools.append(
                {
                    "name": school_name,
                    "office_code": office_code,
                    "school_code": school_code,
                }
            )
    return schools


def fetch_meals(office_code: str, school_code: str, date: str, api_key: str) -> List[Dict[str, str]]:
    payload = api_request(
        "mealServiceDietInfo",
        {
            "ATPT_OFCDC_SC_CODE": office_code,
            "SD_SCHUL_CODE": school_code,
            "MLSV_YMD": date,
        },
        api_key,
    )
    ensure_api_result_ok(payload, "mealServiceDietInfo")
    rows = extract_rows(payload, "mealServiceDietInfo")
    meals: List[Dict[str, str]] = []
    for row in rows:
        meal_name = str(row.get("MMEAL_SC_NM", "")).strip()
        dish_text = str(row.get("DDISH_NM", "")).strip()
        if meal_name and dish_text:
            meals.append({"name": meal_name, "dishes_raw": dish_text})
    return meals


def _extract_timetable_rows(payload: Dict[str, Any], endpoint: str) -> List[Dict[str, str]]:
    ensure_api_result_ok(payload, endpoint)
    rows = extract_rows(payload, endpoint)
    timetable_rows: List[Dict[str, str]] = []
    for row in rows:
        grade = str(row.get("GRADE", "")).strip()
        class_name = str(row.get("CLRM_NM", "")).strip()
        if not class_name:
            class_name = str(row.get("CLASS_NM", "")).strip()
        period = str(row.get("PERIO", "")).strip()
        subject = str(row.get("ITRT_CNTNT", "")).strip()
        if grade and class_name and period and subject:
            timetable_rows.append(
                {
                    "grade": grade,
                    "class_name": class_name,
                    "period": period,
                    "subject": subject,
                }
            )
    return timetable_rows


def fetch_timetable(office_code: str, school_code: str, date: str, api_key: str) -> List[Dict[str, str]]:
    endpoints = ("hisTimetable", "misTimetable", "elsTimetable")
    all_rows: List[Dict[str, str]] = []
    for endpoint in endpoints:
        payload = api_request(
            endpoint,
            {
                "ATPT_OFCDC_SC_CODE": office_code,
                "SD_SCHUL_CODE": school_code,
                "ALL_TI_YMD": date,
            },
            api_key,
        )
        all_rows.extend(_extract_timetable_rows(payload, endpoint))
    return all_rows


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, code: str, message: str) -> None:
        self._send_json(status, {"error": {"code": code, "message": message}})

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        try:
            query = urllib.parse.parse_qs(parsed.query, strict_parsing=True, max_num_fields=20)
        except ValueError:
            self._send_error_json(400, "INVALID_QUERY", "쿼리 문자열이 잘못되었습니다.")
            return

        try:
            if parsed.path == "/health":
                self._send_json(200, {"ok": True})
                return

            api_key = get_api_key()

            if parsed.path == "/schools":
                keyword = query.get("query", [""])[0].strip()
                if not keyword:
                    self._send_error_json(400, "MISSING_QUERY", "query 파라미터가 필요합니다.")
                    return
                schools = search_schools(keyword, api_key)
                self._send_json(200, {"schools": schools})
                return

            if parsed.path == "/meals":
                office_code = query.get("office_code", [""])[0].strip()
                school_code = query.get("school_code", [""])[0].strip()
                date = query.get("date", [""])[0].strip()
                if not office_code or not school_code or not date:
                    self._send_error_json(
                        400,
                        "MISSING_PARAMS",
                        "office_code, school_code, date 파라미터가 필요합니다.",
                    )
                    return
                meals = fetch_meals(office_code, school_code, date, api_key)
                self._send_json(200, {"meals": meals})
                return

            if parsed.path == "/timetable":
                office_code = query.get("office_code", [""])[0].strip()
                school_code = query.get("school_code", [""])[0].strip()
                date = query.get("date", [""])[0].strip()
                if not office_code or not school_code or not date:
                    self._send_error_json(
                        400,
                        "MISSING_PARAMS",
                        "office_code, school_code, date 파라미터가 필요합니다.",
                    )
                    return
                timetable = fetch_timetable(office_code, school_code, date, api_key)
                self._send_json(200, {"timetable": timetable})
                return

            self._send_error_json(404, "NOT_FOUND", "지원하지 않는 경로입니다.")
        except ProxyError as exc:
            self._send_error_json(502, "UPSTREAM_ERROR", str(exc))
        except Exception:
            self._send_error_json(500, "INTERNAL_ERROR", "서버 내부 오류")


def main() -> int:
    host = os.environ.get("MEAL_PROXY_HOST", DEFAULT_HOST)
    port_raw = os.environ.get("MEAL_PROXY_PORT", str(DEFAULT_PORT))
    try:
        port = int(port_raw)
    except ValueError:
        print(f"잘못된 MEAL_PROXY_PORT 값: {port_raw}")
        return 1

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"NEIS proxy running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

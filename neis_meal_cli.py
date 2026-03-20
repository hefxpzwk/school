#!/usr/bin/env python3
"""Simple CLI for fetching school meals from NEIS Open API."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_PROXY_BASE_URL = "https://school-wftk.onrender.com"
MEAL_ORDER = {"조식": 0, "중식": 1, "석식": 2}


@dataclass
class School:
    name: str
    office_code: str
    school_code: str


class NeisError(Exception):
    pass


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        cfg_dir = Path(base) / "neis-meal-cli"
    else:
        cfg_dir = Path.home() / ".config" / "neis-meal-cli"
    return cfg_dir / "config.json"


def save_school(school: School) -> None:
    path = config_path()
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError):
            data = {}
    data["school"] = {
        "name": school.name,
        "office_code": school.office_code,
        "school_code": school.school_code,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise NeisError(f"설정 파일 저장 실패: {path}") from exc


def load_school() -> School:
    path = config_path()
    if not path.exists():
        raise NeisError("학교 설정이 없습니다. 먼저 `set-school` 명령을 실행해 주세요.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw = payload["school"]
        return School(
            name=str(raw["name"]),
            office_code=str(raw["office_code"]),
            school_code=str(raw["school_code"]),
        )
    except OSError as exc:
        raise NeisError(f"설정 파일 읽기 실패: {path}") from exc
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise NeisError(f"설정 파일 형식이 잘못되었습니다: {path}") from exc


def validate_grade(grade: str) -> Tuple[bool, str]:
    if not grade:
        return False, "학년이 비어 있습니다."
    if not grade.isdigit():
        return False, "학년은 숫자로 입력해 주세요."
    grade_num = int(grade)
    if grade_num < 1 or grade_num > 9:
        return False, "학년은 1~9 범위로 입력해 주세요."
    return True, ""


def save_grade(grade: str) -> None:
    is_valid, message = validate_grade(grade)
    if not is_valid:
        raise NeisError(message)

    path = config_path()
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError):
            data = {}

    data["grade"] = grade
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise NeisError(f"설정 파일 저장 실패: {path}") from exc


def load_grade() -> str:
    path = config_path()
    if not path.exists():
        raise NeisError("학년 설정이 없습니다. 먼저 `set-grade` 명령을 실행해 주세요.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        grade = str(payload["grade"]).strip()
        is_valid, message = validate_grade(grade)
        if not is_valid:
            raise NeisError(message)
        return grade
    except OSError as exc:
        raise NeisError(f"설정 파일 읽기 실패: {path}") from exc
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise NeisError(f"설정 파일 형식이 잘못되었습니다: {path}") from exc


def proxy_base_url() -> str:
    return os.environ.get("MEAL_PROXY_BASE_URL", DEFAULT_PROXY_BASE_URL).rstrip("/")


def proxy_get(path: str, params: Dict[str, str]) -> Dict[str, Any]:
    url = f"{proxy_base_url()}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            message = ""
            error_obj = payload.get("error")
            if isinstance(error_obj, dict):
                message = str(error_obj.get("message", "")).strip()
            elif error_obj is not None:
                message = str(error_obj).strip()
            if not message:
                message = raw
        except json.JSONDecodeError:
            message = raw
        raise NeisError(f"프록시 요청 실패 ({exc.code}): {message}") from exc
    except urllib.error.URLError as exc:
        raise NeisError(
            "프록시 연결 오류: 로컬 프록시 서버가 실행 중인지 확인해 주세요. "
            "(python3 neis_proxy_server.py)"
        ) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise NeisError("프록시 응답 JSON 파싱 실패") from exc

    return payload


def find_schools(query: str) -> List[School]:
    payload = proxy_get("/schools", {"query": query})
    rows = payload.get("schools", [])
    if not isinstance(rows, list):
        raise NeisError("프록시 응답 형식 오류: schools")

    schools: List[School] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("SCHUL_NM", "")).strip()
        if not name:
            name = str(row.get("name", "")).strip()
        office = str(row.get("ATPT_OFCDC_SC_CODE", "")).strip()
        if not office:
            office = str(row.get("office_code", "")).strip()
        code = str(row.get("SD_SCHUL_CODE", "")).strip()
        if not code:
            code = str(row.get("school_code", "")).strip()
        if name and office and code:
            schools.append(School(name=name, office_code=office, school_code=code))
    return schools


def normalize_dish_line(line: str) -> str:
    text = re.sub(r"\s*\([0-9.]+\)", "", line)
    return re.sub(r"\s+", " ", text).strip()


def format_meal_text(raw_text: str) -> List[str]:
    lines = re.split(r"<br\s*/?>", raw_text)
    cleaned = [normalize_dish_line(line) for line in lines]
    return [line for line in cleaned if line]


def get_meals_for_day(school: School, date: str) -> List[Dict[str, Any]]:
    payload = proxy_get(
        "/meals",
        {
            "office_code": school.office_code,
            "school_code": school.school_code,
            "date": date,
        },
    )
    rows = payload.get("meals", [])
    if not isinstance(rows, list):
        raise NeisError("프록시 응답 형식 오류: meals")

    grouped: Dict[str, List[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        meal_name = str(row.get("MMEAL_SC_NM", "")).strip()
        if not meal_name:
            meal_name = str(row.get("name", "")).strip()
        dishes_raw = str(row.get("DDISH_NM", "")).strip()
        if not dishes_raw:
            dishes_raw = str(row.get("dishes_raw", "")).strip()
        if meal_name and dishes_raw:
            grouped.setdefault(meal_name, []).extend(format_meal_text(dishes_raw))

    meals = [{"name": name, "dishes": dishes} for name, dishes in grouped.items()]

    meals.sort(key=lambda m: MEAL_ORDER.get(str(m["name"]), 999))
    return meals


def get_timetable_for_day(school: School, date: str) -> List[Dict[str, str]]:
    payload = proxy_get(
        "/timetable",
        {
            "office_code": school.office_code,
            "school_code": school.school_code,
            "date": date,
        },
    )
    rows = payload.get("timetable", [])
    if not isinstance(rows, list):
        raise NeisError("프록시 응답 형식 오류: timetable")

    parsed_rows: List[Dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        grade = str(row.get("GRADE", "")).strip()
        if not grade:
            grade = str(row.get("grade", "")).strip()
        class_name = str(row.get("CLRM_NM", "")).strip()
        if not class_name:
            class_name = str(row.get("CLASS_NM", "")).strip()
        if not class_name:
            class_name = str(row.get("class_name", "")).strip()
        period = str(row.get("PERIO", "")).strip()
        if not period:
            period = str(row.get("period", "")).strip()
        subject = str(row.get("ITRT_CNTNT", "")).strip()
        if not subject:
            subject = str(row.get("subject", "")).strip()
        if grade and class_name and period and subject:
            parsed_rows.append(
                {
                    "grade": grade,
                    "class_name": class_name,
                    "period": period,
                    "subject": subject,
                }
            )

    parsed_rows.sort(
        key=lambda row: (
            int(row["grade"]) if row["grade"].isdigit() else 999,
            int(row["class_name"]) if row["class_name"].isdigit() else 999,
            int(row["period"]) if row["period"].isdigit() else 999,
            row["class_name"],
            row["period"],
        )
    )
    return parsed_rows


def validate_date(date: str) -> Tuple[bool, str]:
    if not re.fullmatch(r"\d{8}", date):
        return False, "날짜 형식이 잘못되었습니다. YYYYMMDD 형식으로 입력해 주세요."
    try:
        dt.datetime.strptime(date, "%Y%m%d")
    except ValueError:
        return False, "유효하지 않은 날짜입니다. YYYYMMDD 형식의 실제 날짜를 입력해 주세요."
    return True, ""


def week_dates_from(date: str) -> List[str]:
    base = dt.datetime.strptime(date, "%Y%m%d").date()
    monday = base - dt.timedelta(days=base.weekday())
    return [(monday + dt.timedelta(days=delta)).strftime("%Y%m%d") for delta in range(5)]


def get_or_setup_school() -> School:
    if config_path().exists():
        return load_school()
    return prompt_and_save_school()


def prompt_and_save_grade() -> str:
    grade = input("학년을 입력해 주세요 (예: 1): ").strip()
    is_valid, message = validate_grade(grade)
    if not is_valid:
        raise NeisError(message)
    save_grade(grade)
    print(f"학년 설정 완료: {grade}학년")
    return grade


def prompt_and_save_school() -> School:
    print("학교 설정이 없습니다. 처음 1회 학교를 설정합니다.")
    query = input("학교 이름을 입력해 주세요: ").strip()
    if not query:
        raise NeisError("학교 이름이 비어 있습니다.")

    schools = find_schools(query)
    if not schools:
        raise NeisError(f"학교를 찾지 못했습니다: {query}")

    if len(schools) == 1:
        selected = schools[0]
    else:
        print("동일한 이름의 학교가 여러 개 있습니다. 번호를 입력해 선택해 주세요:")
        for i, school in enumerate(schools, start=1):
            print(f"  {i}. {school.name} ({school.office_code}/{school.school_code})")
        selected_raw = input("선택 번호: ").strip()
        try:
            selected_index = int(selected_raw)
        except ValueError as exc:
            raise NeisError("선택 번호는 숫자여야 합니다.") from exc

        if selected_index < 1 or selected_index > len(schools):
            raise NeisError(f"유효하지 않은 번호입니다. 1 ~ {len(schools)}")
        selected = schools[selected_index - 1]

    save_school(selected)
    print(f"학교 설정 완료: {selected.name} ({selected.office_code}/{selected.school_code})")
    return selected


def command_set_school(args: argparse.Namespace) -> int:
    schools = find_schools(args.query)

    if not schools:
        print(f"학교를 찾지 못했습니다: {args.query}")
        return 1

    if args.index is None:
        if len(schools) == 1:
            selected = schools[0]
        else:
            print("동일한 이름의 학교가 여러 개 있습니다. --index로 선택해 주세요:")
            for i, school in enumerate(schools, start=1):
                print(f"  {i}. {school.name} ({school.office_code}/{school.school_code})")
            return 1
    else:
        if args.index < 1 or args.index > len(schools):
            print(f"유효하지 않은 index입니다. 1 ~ {len(schools)}")
            return 1
        selected = schools[args.index - 1]

    save_school(selected)
    print(f"학교 설정 완료: {selected.name} ({selected.office_code}/{selected.school_code})")
    return 0


def command_set_grade(args: argparse.Namespace) -> int:
    try:
        save_grade(str(args.grade))
    except NeisError as exc:
        print(str(exc))
        return 1

    print(f"학년 설정 완료: {args.grade}학년")
    return 0


def command_meals(args: argparse.Namespace) -> int:
    date = args.date or dt.datetime.now().strftime("%Y%m%d")
    is_valid_date, error_message = validate_date(date)
    if not is_valid_date:
        print(error_message)
        return 1

    try:
        school = get_or_setup_school()
    except NeisError as exc:
        print(str(exc))
        return 1

    meals = get_meals_for_day(school, date)

    print(f"학교: {school.name}")
    print(f"날짜: {date}")

    if not meals:
        print("해당 날짜의 급식 정보가 없습니다.")
        return 0

    for meal in meals:
        print(f"\n[{meal['name']}]")
        for dish in meal["dishes"]:
            print(f"- {dish}")

    return 0


def command_timetable(args: argparse.Namespace) -> int:
    date = args.date or dt.datetime.now().strftime("%Y%m%d")
    is_valid_date, error_message = validate_date(date)
    if not is_valid_date:
        print(error_message)
        return 1

    try:
        school = get_or_setup_school()
    except NeisError as exc:
        print(str(exc))
        return 1

    try:
        if args.grade is not None:
            selected_grade = str(args.grade)
            is_valid, message = validate_grade(selected_grade)
            if not is_valid:
                print(message)
                return 1
        elif config_path().exists():
            selected_grade = load_grade()
        else:
            selected_grade = prompt_and_save_grade()
    except NeisError:
        try:
            selected_grade = prompt_and_save_grade()
        except NeisError as exc:
            print(str(exc))
            return 1

    target_dates = [date]
    if args.week:
        target_dates = week_dates_from(date)

    print(f"학교: {school.name}")
    if args.week:
        print(f"주간: {target_dates[0]} ~ {target_dates[-1]}")
    else:
        print(f"날짜: {date}")
    print(f"학년: {selected_grade}")

    any_rows = False
    for target_date in target_dates:
        timetable_rows = get_timetable_for_day(school, target_date)
        timetable_rows = [row for row in timetable_rows if row["grade"] == selected_grade]
        if not timetable_rows:
            if args.week:
                print(f"\n[{target_date}]")
                print("해당 날짜의 시간표 정보가 없습니다.")
            continue

        any_rows = True
        if args.week:
            print(f"\n[{target_date}]")

        current_key = None
        for row in timetable_rows:
            class_key = (row["grade"], row["class_name"])
            if class_key != current_key:
                print(f"\n[{row['grade']}학년 {row['class_name']}반]")
                current_key = class_key
            print(f"{row['period']}교시 - {row['subject']}")

    if not any_rows and not args.week:
        print("해당 날짜의 시간표 정보가 없습니다.")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sch", description="NEIS 학교 급식/시간표 조회 CLI")

    sub = parser.add_subparsers(dest="command", required=True)

    set_school_parser = sub.add_parser("set-school", help="학교를 검색하고 기본 학교로 설정")
    set_school_parser.add_argument("query", help="학교 이름")
    set_school_parser.add_argument("--index", type=int, help="동명이 학교 선택 번호")
    set_school_parser.set_defaults(func=command_set_school)

    set_grade_parser = sub.add_parser("set-grade", help="기본 학년 설정 (시간표 조회용)")
    set_grade_parser.add_argument("grade", help="학년 (1~9)")
    set_grade_parser.set_defaults(func=command_set_grade)

    meals_parser = sub.add_parser("food", aliases=["meals"], help="설정된 학교의 급식 조회")
    meals_parser.add_argument("--date", help="조회 날짜 (YYYYMMDD), 기본값: 오늘")
    meals_parser.set_defaults(func=command_meals)

    timetable_parser = sub.add_parser("tt", aliases=["timetable"], help="설정된 학교의 시간표 조회")
    timetable_parser.add_argument("--date", help="조회 날짜 (YYYYMMDD), 기본값: 오늘")
    timetable_parser.add_argument("--grade", help="조회 학년 (기본값: 저장된 학년)")
    timetable_parser.add_argument("--week", action="store_true", help="기준 날짜가 포함된 주(월~금) 시간표 조회")
    timetable_parser.set_defaults(func=command_timetable)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except NeisError as exc:
        print(f"오류: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

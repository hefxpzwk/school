# NEIS School Meal CLI

사용자는 학교 이름만 입력하면 되는 급식 CLI입니다.

NEIS 키는 사용자 CLI가 아니라 로컬 프록시 서버가 보관해 사용합니다.

## Tech Stack

- Python 3.10+
- Python standard library only (no external dependencies)

## Quick Start

1) 프록시 서버용 NEIS 키 설정

```bash
export NEIS_API_KEY="YOUR_NEIS_KEY"
```

2) 프록시 서버 실행 (별도 터미널)

```bash
python3 neis_proxy_server.py
```

3) CLI 실행

```bash
python3 neis_meal_cli.py meals
```

처음 실행 시 학교 설정이 없으면 학교 이름을 물어보고 1회 저장합니다.
그 다음부터는 `meals` 또는 `timetable`만 실행하면 됩니다.

```text
학교 설정이 없습니다. 처음 1회 학교를 설정합니다.
학교 이름을 입력해 주세요: 서울고등학교
```

동명이 학교가 여러 개면 목록을 보여주고 `--index`로 선택할 수 있습니다.

```bash
python3 neis_meal_cli.py set-school "서울고등학교" --index 2
```

특정 날짜 조회:

```bash
python3 neis_meal_cli.py meals --date 20260319
python3 neis_meal_cli.py timetable --date 20260319
```

사용자는 CLI에서 키를 입력할 필요가 없습니다.

## 동작 방식

1. 로컬 프록시(`neis_proxy_server.py`)가 `NEIS_API_KEY`로 NEIS API를 호출
2. CLI(`neis_meal_cli.py`)는 프록시의 `/schools`, `/meals` 엔드포인트만 사용
3. `meals` 첫 실행에서 학교명을 입력받아 코드 저장
4. 이후 `meals` 실행 시 조식/중식/석식을 자동 출력
5. 이후 `timetable` 실행 시 해당 날짜 시간표를 자동 출력

원하면 수동으로 미리 설정할 수도 있습니다:

```bash
python3 neis_meal_cli.py set-school "서울고등학교"
```

설정 파일 경로:

- `${XDG_CONFIG_HOME}/neis-meal-cli/config.json` (설정 시)
- 없으면 `~/.config/neis-meal-cli/config.json`

## Optional 환경 변수

- `MEAL_PROXY_BASE_URL` (CLI용, 기본: `http://127.0.0.1:8787`)
- `MEAL_PROXY_HOST` (프록시용, 기본: `127.0.0.1`)
- `MEAL_PROXY_PORT` (프록시용, 기본: `8787`)

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

시간표(`timetable`)는 학년 설정이 없으면 처음 1회 학년을 물어보고 저장합니다.
다음부터는 저장된 학년 기준으로 자동 조회합니다.

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
python3 neis_meal_cli.py timetable --date 20260319 --week
```

학년 수동 설정:

```bash
python3 neis_meal_cli.py set-grade 2
```

사용자는 CLI에서 키를 입력할 필요가 없습니다.

## 동작 방식

1. 로컬 프록시(`neis_proxy_server.py`)가 `NEIS_API_KEY`로 NEIS API를 호출
2. CLI(`neis_meal_cli.py`)는 프록시의 `/schools`, `/meals` 엔드포인트만 사용
3. `meals` 첫 실행에서 학교명을 입력받아 코드 저장
4. 이후 `meals` 실행 시 조식/중식/석식을 자동 출력
5. 이후 `timetable` 실행 시 저장된 학년의 해당 날짜 시간표를 자동 출력
6. `timetable --week` 실행 시 기준 날짜가 포함된 주(월~금) 전체 시간표를 출력

원하면 수동으로 미리 설정할 수도 있습니다:

```bash
python3 neis_meal_cli.py set-school "서울고등학교"
```

설정 파일 경로:

- `${XDG_CONFIG_HOME}/neis-meal-cli/config.json` (설정 시)
- 없으면 `~/.config/neis-meal-cli/config.json`

## Optional 환경 변수

- `MEAL_PROXY_BASE_URL` (CLI용, 기본: `https://school-wftk.onrender.com`)
- `MEAL_PROXY_HOST` (프록시용, 기본: `127.0.0.1`)
- `MEAL_PROXY_PORT` (프록시용, 기본: `8787`)

## CLI 배포 (GitHub Release 자동화)

이 저장소는 태그를 푸시하면 GitHub Actions가 OS별 실행 파일을 빌드해서 Release에 첨부합니다.

- Linux: `neis-cli-ubuntu-latest`
- macOS: `neis-cli-macos-latest`
- Windows: `neis-cli-windows-latest.exe`

워크플로 파일:

- `.github/workflows/release-cli.yml`

릴리스 생성 방법:

```bash
git tag v1.0.0
git push origin v1.0.0
```

완료되면 GitHub Release의 Assets에서 실행 파일을 내려받아 바로 실행할 수 있습니다.

## 사용자용 실행 방법 (다운로드 후 바로 사용)

1. GitHub Release에서 OS에 맞는 파일을 다운로드
2. 서버 주소를 환경 변수로 설정
3. 실행

macOS / Linux:

```bash
export MEAL_PROXY_BASE_URL="https://school-wftk.onrender.com"
./neis-cli-ubuntu-latest meals
./neis-cli-ubuntu-latest timetable
```

macOS 전용 파일을 받았다면 아래처럼 실행:

```bash
export MEAL_PROXY_BASE_URL="https://school-wftk.onrender.com"
./neis-cli-macos-latest meals
./neis-cli-macos-latest timetable
```

Windows PowerShell:

```powershell
$env:MEAL_PROXY_BASE_URL="https://school-wftk.onrender.com"
.\neis-cli-windows-latest.exe meals
.\neis-cli-windows-latest.exe timetable
```

## 어디서든 실행 (전역 설치)

다운로드한 실행 파일을 PATH에 넣으면 어느 폴더에서든 `neis-cli`로 실행할 수 있습니다.

macOS / Linux:

```bash
chmod +x ./scripts/install_cli_unix.sh
./scripts/install_cli_unix.sh ./neis-cli-ubuntu-latest
# macOS 파일을 받았다면: ./scripts/install_cli_unix.sh ./neis-cli-macos-latest

neis-cli meals
neis-cli timetable --week
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_cli_windows.ps1 -SourceBinary .\neis-cli-windows-latest.exe

neis-cli meals
neis-cli timetable --week
```

## 서버 배포 가이드 (Render)

1. Render에서 `Web Service` 생성 후 GitHub 저장소 연결
2. Environment Variables 설정
   - `NEIS_API_KEY=발급받은키`
   - `MEAL_PROXY_HOST=0.0.0.0`
   - `MEAL_PROXY_PORT=10000`
3. Start Command 설정

```bash
python3 neis_proxy_server.py
```

4. Health Check 경로를 `/health`로 설정
5. 배포 완료 후 발급 URL을 CLI의 `MEAL_PROXY_BASE_URL`로 사용

보안 주의:

- `NEIS_API_KEY`는 서버 환경 변수에만 저장하고 GitHub/CLI에 포함하지 않습니다.

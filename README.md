# NEIS School Meal CLI

사용자는 학교 이름만 입력하면 되는 급식 CLI입니다.

사용자는 키 설정이나 로컬 서버 실행 없이 바로 사용할 수 있습니다.

## Tech Stack

- Python 3.10+
- Python standard library only (no external dependencies)

## 설치 (복사해서 바로 실행)

아래 명령을 그대로 복사해서 실행하면 `sch`가 전역 설치됩니다.

macOS (zsh/bash):

```bash
mkdir -p "$HOME/.local/bin" \
&& curl -fsSL "https://github.com/hefxpzwk/school/releases/latest/download/sch-macos-latest" -o "$HOME/.local/bin/sch" \
&& chmod +x "$HOME/.local/bin/sch" \
&& export PATH="$HOME/.local/bin:$PATH" \
&& echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
```

Linux (bash):

```bash
mkdir -p "$HOME/.local/bin" \
&& curl -fsSL "https://github.com/hefxpzwk/school/releases/latest/download/sch-ubuntu-latest" -o "$HOME/.local/bin/sch" \
&& chmod +x "$HOME/.local/bin/sch" \
&& export PATH="$HOME/.local/bin:$PATH" \
&& echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
```

Windows PowerShell:

```powershell
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\sch"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Invoke-WebRequest -Uri "https://github.com/hefxpzwk/school/releases/latest/download/sch-windows-latest.exe" -OutFile (Join-Path $InstallDir "sch.exe")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not ($userPath -split ";" | Where-Object { $_ -eq $InstallDir })) {
  if ([string]::IsNullOrWhiteSpace($userPath)) {
    [Environment]::SetEnvironmentVariable("Path", $InstallDir, "User")
  } else {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
  }
}
Write-Output "새 PowerShell 창을 연 뒤: sch food"
```

## Quick Start

서버가 이미 배포되어 있으므로 전역 명령 `sch`만으로 바로 사용할 수 있습니다.

1) (선택) 서버 주소 설정

```bash
export MEAL_PROXY_BASE_URL="https://school-wftk.onrender.com"
```

2) 급식/시간표 조회

```bash
sch food
sch tt
sch tt --week
```

처음 실행 시 학교 설정이 없으면 학교 이름을 물어보고 1회 저장합니다.
그 다음부터는 `food` 또는 `tt`만 실행하면 됩니다.

시간표(`tt`)는 학년/반 설정이 없으면 처음 1회 학년과 반을 물어보고 저장합니다.
다음부터는 저장된 학년/반 기준으로 자동 조회합니다.

```text
학교 설정이 없습니다. 처음 1회 학교를 설정합니다.
학교 이름을 입력해 주세요: 서울고등학교
```

동명이 학교가 여러 개면 목록을 보여주고 `--index`로 선택할 수 있습니다.

```bash
sch set-school "서울고등학교" --index 2
```

특정 날짜 조회:

```bash
sch food --date 20260319
sch tt --date 20260319
sch tt --date 20260319 --week
```

학년 수동 설정:

```bash
sch set-grade 2
```

반 수동 설정:

```bash
sch set-class 3
```

학교/학년/반 한 번에 다시 설정:

```bash
sch set-profile
```

## 동작 방식

1. CLI(`sch`)는 배포된 서버로 요청을 보냅니다.
2. `food` 첫 실행에서 학교명을 입력받아 코드 저장
3. 이후 `food` 실행 시 조식/중식/석식을 자동 출력
4. 이후 `tt` 실행 시 저장된 학년/반의 해당 날짜 시간표를 자동 출력
5. `tt --week` 실행 시 기준 날짜가 포함된 주(월~금) 전체 시간표를 출력

원하면 수동으로 미리 설정할 수도 있습니다:

```bash
sch set-school "서울고등학교"
```

설정 파일 경로:

- `${XDG_CONFIG_HOME}/neis-meal-cli/config.json` (설정 시)
- 없으면 `~/.config/neis-meal-cli/config.json`

## Optional 환경 변수

- `MEAL_PROXY_BASE_URL` (CLI용, 기본: `https://school-wftk.onrender.com`)
- `MEAL_PROXY_TIMEOUT` (CLI 요청 타임아웃 초, 기본: `20`)
- `MEAL_PROXY_RETRIES` (타임아웃 시 재시도 횟수, 기본: `2`)

## 설치 후 실행

설치가 끝나면 어느 폴더에서든 아래처럼 실행하면 됩니다.

```bash
sch food
sch tt
sch tt --week
sch tt --class 3
```

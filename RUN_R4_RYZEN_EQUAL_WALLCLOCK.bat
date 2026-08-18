@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo DeepCash R4 - Ryzen equal-wall-clock physical gate
echo ============================================================
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python launcher ^(py^) not found.
  echo Install Python 3.11 x64 and retry.
  exit /b 1
)

py -3.11 -c "import sys; print(sys.version)" >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3.11 not available through py -3.11.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating .venv with Python 3.11...
  py -3.11 -m venv .venv
  if errorlevel 1 exit /b 1
) else (
  echo [1/5] Existing .venv found.
)

set "PY=.venv\Scripts\python.exe"

echo [2/5] Installing DeepCash and test dependencies...
"%PY%" -m pip install --disable-pip-version-check -e ".[dev]"
if errorlevel 1 exit /b 1

echo [3/5] Validating frozen R4 finalists and physical runner...
"%PY%" -m pytest -q tests/test_r4_generation2_freeze.py tests/test_r4_representation_gen2.py tests/test_r4_representation_gen2_finalist_freeze.py tests/test_r4_ryzen_equal_wallclock.py
if errorlevel 1 exit /b 1

echo [4/5] Starting official sequential physical benchmark...
echo This intentionally uses one candidate process at a time to avoid contention.
echo Do not game, train another model, or run heavy workloads while this is executing.
"%PY%" tools/run_r4_ryzen_equal_wallclock.py
if errorlevel 1 exit /b 1

echo [5/5] COMPLETE.
echo.
echo Look in the r4_ryzen_runs folder for the newest *_UPLOAD_ME equivalent ZIP.
echo Send that ZIP back to ChatGPT for audit.
echo.
pause

@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo DeepCash R4 - Ryzen instrumentation repair

echo Fills the missing peak-RSS and affinity evidence only.
echo It does NOT redo strategic selection.
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv not found. Run RUN_R4_RYZEN_EQUAL_WALLCLOCK.bat setup first.
  exit /b 1
)
set "PY=.venv\Scripts\python.exe"

echo [1/4] Installing current DeepCash branch...
"%PY%" -m pip install --disable-pip-version-check -e ".[dev]"
if errorlevel 1 exit /b 1

echo [2/4] Running CI-equivalent repair tests...
"%PY%" -m pytest -q tests/test_r4_ryzen_instrumentation_repair.py
if errorlevel 1 exit /b 1

echo [3/4] Verifying Windows memory/affinity instrumentation before the full diagnostic...
"%PY%" tools\run_r4_ryzen_instrumentation_repair.py --preflight
if errorlevel 1 exit /b 1

echo [4/4] Running frozen 144-cell instrumentation repair...
echo This is much shorter than the 20-second equal-wall-clock benchmark.
"%PY%" tools\run_r4_ryzen_instrumentation_repair.py
if errorlevel 1 exit /b 1

echo.
echo COMPLETE.
echo Send the newest r4_ryzen_instrumentation_repair_*.zip from r4_ryzen_runs to ChatGPT.
echo.
pause

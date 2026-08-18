@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo DeepCash R4/R5/R6 - physical compatibility gate
echo R4: matchup_cluster8 vs equity8
echo R5: ALT_DCFR_150_0_2 post-update discounted semantics
echo R6: first turn-to-river public-state chance-transfer boundary
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv not found.
  echo Run the prior Ryzen setup or create a Python 3.11 virtual environment first.
  exit /b 1
)
set "PY=.venv\Scripts\python.exe"

echo [1/4] Installing current DeepCash checkout...
"%PY%" -m pip install --disable-pip-version-check -e ".[dev]"
if errorlevel 1 exit /b 1

echo [2/4] Running compatibility structural tests...
"%PY%" -m pytest -q tests/test_r4_r5_representation_alternating_compatibility.py tests/test_r6_turn_river_public_state.py tests/test_r4_r5_r6_compatibility_runner.py
if errorlevel 1 exit /b 1

echo [3/4] Checking frozen config plus memory/affinity instrumentation...
"%PY%" tools\run_r4_r5_r6_compatibility.py --preflight
if errorlevel 1 exit /b 1

echo [4/4] Running the frozen physical compatibility battery...
echo Keep the Ryzen free from games, training, solvers, and other heavy workloads.
echo Candidate workers run sequentially in fresh subprocesses.
"%PY%" tools\run_r4_r5_r6_compatibility.py
if errorlevel 1 exit /b 1

echo.
echo COMPLETE.
echo Send the newest r4_r5_r6_compatibility_*.zip from r4_ryzen_runs to ChatGPT.
echo.
pause

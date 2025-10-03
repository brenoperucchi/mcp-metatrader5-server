@echo off
REM Run tick investigation directly on Windows
REM This script runs the investigation using Windows Python

echo ================================================================================
echo MCP Ticks Investigation - Running on Windows
echo ================================================================================
echo.

cd /d "%~dp0"

echo 1. Testing HTTP API Investigation...
echo.
python investigate_ticks_issue_windows.py
echo.

echo 2. Testing Direct MT5 API...
echo.
python diagnose_ticks_access.py
echo.

echo ================================================================================
echo Investigation Complete!
echo Check the output above for results.
echo ================================================================================
pause

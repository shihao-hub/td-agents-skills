@echo off
chcp 65001 >nul
uv run "%~dp0sync_skills.py" %*
exit /b %errorlevel%

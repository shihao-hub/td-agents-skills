@echo off
chcp 65001 >nul
if exist "%~dp0sync_lark_skills.py" (
    uv run "%~dp0sync_lark_skills.py"
)
uv run "%~dp0sync_skills.py" %*
exit /b %errorlevel%

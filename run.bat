@echo off
setlocal
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0src\main.py" %*
) else (
    python "%~dp0src\main.py" %*
)
exit /b %errorlevel%

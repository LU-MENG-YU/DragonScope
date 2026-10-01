@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%
python collectors\run.py
pause

@echo off
REM Batch script to activate virtual environment
cd /d %~dp0
call venv\Scripts\activate.bat
echo Virtual environment activated!
echo Current directory: %CD%
cmd /k

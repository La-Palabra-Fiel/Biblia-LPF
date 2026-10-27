@echo off
setlocal
cd /d "%~dp0"
title LBF Team Review

findstr /b /r /c:"OPENAI_API_KEY=." apps\pipeline\.env >nul 2>nul
if not errorlevel 1 goto start_app

echo Paste the OpenAI API key below, then press Enter.
echo The key is used only for this run and is not saved to a file.
echo.
set /p "OPENAI_API_KEY=OpenAI API key: "

if not defined OPENAI_API_KEY (
  echo.
  echo No key was entered. The app was not started.
  pause
  exit /b 1
)

cls
:start_app
echo Starting LBF Team Review...

where py >nul 2>nul
if errorlevel 1 (
  set "LBF_PYTHON=python"
) else (
  set "LBF_PYTHON=py"
)

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:1435/'"
%LBF_PYTHON% apps\team\server.py

if errorlevel 1 (
  echo.
  echo The app could not start. Make sure Python is installed, then try again.
  pause
)

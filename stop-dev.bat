@echo off
rem One-click dev shutdown: Web + API + Qdrant
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-dev.ps1"
pause

@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0to_cloud.ps1" %*
pause

@echo off
chcp 65001 >nul
start "pnation Watchdog" cmd /k "C:\Users\wake\.workbuddy\binaries\python\versions\3.13.12\python.exe" -X utf8 "C:\Users\wake\WorkBuddy\2026-07-04-13-12-27\pnation_fleet\watchdog.py"

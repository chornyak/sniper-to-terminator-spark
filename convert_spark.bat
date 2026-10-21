@echo off
rem Windows drag-and-drop launcher: drop one or more Sniper .spark files onto this file.
rem Requires template.spark (a base spark table saved from Terminator X) in this folder.
setlocal

if "%~1"=="" (
    echo Drag one or more Sniper .spark files onto this file to convert them.
    echo Put template.spark ^(saved from Terminator X^) in this folder first.
    pause
    exit /b 1
)

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
    echo Python 3 was not found. Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup.
    pause
    exit /b 1
)

:next
if "%~1"=="" goto done
echo.
echo === %~nx1
%PY% "%~dp0convert_spark.py" "%~1"
shift
goto next

:done
echo.
pause

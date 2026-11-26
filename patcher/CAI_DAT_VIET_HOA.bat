@echo off
chcp 65001 >nul
title Cai dat Viet hoa Dynasty Warriors 4 Hyper (PC) - Quan Game Xom
setlocal

where python >nul 2>&1
if %errorlevel%==0 (
    set PYCMD=python
) else (
    where py >nul 2>&1
    if %errorlevel%==0 (
        set PYCMD=py -3
    ) else (
        echo [LOI] May ban chua cai Python 3.
        echo Vui long tai Python 3 mien phi tai: https://www.python.org/downloads/
        echo (Nho tick "Add Python to PATH" khi cai, sau do chay lai file nay.)
        echo.
        pause
        exit /b 1
    )
)

if "%~1"=="" (
    %PYCMD% "%~dp0patcher.py" install
) else (
    %PYCMD% "%~dp0patcher.py" install "%~1"
)
echo.
pause

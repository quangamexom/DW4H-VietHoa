@echo off
chcp 65001 >nul
title Go cai dat Viet hoa Dynasty Warriors 4 Hyper (PC)
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
        echo.
        pause
        exit /b 1
    )
)

if "%~1"=="" (
    %PYCMD% "%~dp0patcher.py" uninstall
) else (
    %PYCMD% "%~dp0patcher.py" uninstall "%~1"
)
echo.
pause

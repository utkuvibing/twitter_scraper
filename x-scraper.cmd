@echo off
setlocal

set "APP_ROOT=%~dp0"
set "APP_ROOT=%APP_ROOT:~0,-1%"
set "APP_PYTHON=%APP_ROOT%\.venv\Scripts\python.exe"

if not exist "%APP_PYTHON%" (
    echo Ilk kurulum yapiliyor, bir dakika surebilir...
    python -m venv "%APP_ROOT%\.venv"
    if errorlevel 1 (
        echo Hata: Python bulunamadi veya sanal ortam olusturulamadi.
        exit /b 1
    )
)

"%APP_PYTHON%" -c "import selenium, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Ilk kurulum yapiliyor, bir dakika surebilir...
    "%APP_PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 exit /b 1

    "%APP_PYTHON%" -m pip install "%APP_ROOT%"
    if errorlevel 1 exit /b 1
)

"%APP_PYTHON%" "%APP_ROOT%\main.py" %*
exit /b %errorlevel%

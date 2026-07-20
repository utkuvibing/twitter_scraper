@echo off
setlocal

set "APP_ROOT=%~dp0"
set "APP_ROOT=%APP_ROOT:~0,-1%"
set "APP_PYTHON=%APP_ROOT%\.venv\Scripts\python.exe"

if not exist "%APP_PYTHON%" (
    echo Installing x-scraper into its local environment...
    python -m venv "%APP_ROOT%\.venv"
    if errorlevel 1 (
        echo Error: Python was not found or the local environment could not be created.
        exit /b 1
    )
)

"%APP_PYTHON%" -c "import selenium, docx" >nul 2>&1
if errorlevel 1 (
    echo Installing x-scraper dependencies...
    "%APP_PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 exit /b 1

    "%APP_PYTHON%" -m pip install "%APP_ROOT%"
    if errorlevel 1 exit /b 1
)

"%APP_PYTHON%" "%APP_ROOT%\main.py" %*
exit /b %errorlevel%

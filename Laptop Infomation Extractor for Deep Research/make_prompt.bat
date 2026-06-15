@echo off
setlocal

cd /d "%~dp0"

py -3 --version >nul 2>nul
if %ERRORLEVEL%==0 goto run_py

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" goto run_codex_python

python --version >nul 2>nul
if %ERRORLEVEL%==0 goto run_python

echo Python 3 was not found.
echo Install Python 3.10+ from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
exit /b 1

:run_py
py -3 -m infomation_extractor %*
exit /b %ERRORLEVEL%

:run_codex_python
"%CODEX_PY%" -m infomation_extractor %*
exit /b %ERRORLEVEL%

:run_python
python -m infomation_extractor %*
exit /b %ERRORLEVEL%

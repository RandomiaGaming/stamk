@echo off

:: Save a good copy of the script dir since shift will break this
set "scriptdir=%~dp0"

:: Ensure python has been installed
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo MiniBuild requires python to run but it could not be found.
    echo You may need to edit your PATH or download it from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Combine the command line args so they are ready to forward to python
set args=
:argLoopContinue
if "%~1"=="" goto argLoopBreak
set args=%args% "%~1"
shift
goto argLoopContinue
:argLoopBreak

:: Launch stamk.py and return it's status code
python "%scriptdir%..\stamk.py" %args%
exit /b %errorlevel%
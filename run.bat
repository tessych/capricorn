@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0out\windows\Capri.exe" (
    echo [Capri] Capri.exe не найден. Запускаю сборку...
    call "%~dp0build.bat"
)
if exist "%~dp0out\windows\Capri.exe" (
    start "" "%~dp0out\windows\Capri.exe"
)

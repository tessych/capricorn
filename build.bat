@echo off
setlocal
cd /d "%~dp0"
echo [Capri] Сборка Capri для Windows...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ci\build-windows.ps1"
if %ERRORLEVEL% equ 0 (
    echo.
    echo [Capri] Сборка успешно завершена! Исполняемый файл: out\windows\Capri.exe
) else (
    echo.
    echo [Capri] Ошибка сборки. Убедись, что на Windows установлен .NET Framework 4.8.
)
pause

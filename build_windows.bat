@echo off
REM Build a standalone Windows executable (run this ON WINDOWS, with
REM Python 3.11+ installed and on PATH).

setlocal
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm escape_room_master.spec

echo.
echo Done. The executable is at dist\EscapeRoomMaster.exe
endlocal

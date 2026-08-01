@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Escape Room Master — Build
echo ============================================================
echo.

REM Build the executable
echo [1/4] Building executable...
.venv\Scripts\pyinstaller.exe EscapeRoomMaster.spec --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. See output above.
    pause
    exit /b 1
)

echo.
REM Copy python DLL if PyInstaller missed it (common with Python 3.14)
echo      Ensuring python DLL is bundled...
for /f "delims=" %%D in ('where python 2^>nul') do (
    for %%F in ("%%~dpDpython3*.dll") do (
        if exist "%%F" copy /Y "%%F" "dist\EscapeRoomMaster\_internal\" >nul 2>nul
    )
)

echo [2/4] Setting up app folder structure...
set OUT=dist\EscapeRoomMaster

REM Create the media subfolders inside the built app
mkdir "%OUT%\data"         2>nul
mkdir "%OUT%\media\videos" 2>nul
mkdir "%OUT%\media\audio"  2>nul
mkdir "%OUT%\media\images" 2>nul

REM Copy existing database if present
if exist "data\escape_rooms.db" (
    copy /Y "data\escape_rooms.db" "%OUT%\data\escape_rooms.db" >nul
    echo      Copied existing database to dist folder.
) else (
    echo      No database found — a fresh one will be created on first run.
)

echo [3/4] Copying credentials / config...

REM Copy .env file (Turso API credentials) if present
if exist ".env" (
    copy /Y ".env" "%OUT%\.env" >nul
    echo      Copied .env  (Turso credentials included^).
) else (
    echo      No .env file found — booking sync will be disabled.
    echo      Create .env next to this script with:
    echo        TURSO_DATABASE_URL=libsql://your-db.turso.io
    echo        TURSO_AUTH_TOKEN=your-token-here
    echo      Then rebuild, or copy .env manually to dist\EscapeRoomMaster\.env
)

echo.
echo [4/4] Done!
echo.
echo Your packaged app is in:
echo   %~dp0dist\EscapeRoomMaster\
echo.
echo To share it: zip or copy that entire folder to another PC.
echo              Put your videos/audio/images inside  media\
echo              The database lives in                data\
echo              Booking sync credentials are in      .env
echo.
pause

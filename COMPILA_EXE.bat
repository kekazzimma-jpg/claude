@echo off
:: ============================================================
::  COMPILA_EXE.bat
::  Compila pdf_p7m_extractor.py in un singolo file .exe
::  Non serve Python installato sul computer dell'utente finale.
:: ============================================================

echo.
echo ============================================================
echo   Compilazione P7M Extract - creazione file .exe
echo ============================================================
echo.

:: --- Controlla che Python sia installato ---
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato.
    echo Scaricalo da https://www.python.org e riavvia questo script.
    pause
    exit /b 1
)

echo [1/3] Python trovato. Installo/aggiorno PyInstaller...
python -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 (
    echo ERRORE: impossibile installare PyInstaller.
    pause
    exit /b 1
)

echo [2/3] Installo le dipendenze del programma...
python -m pip install --quiet asn1crypto Pillow
if errorlevel 1 (
    echo ERRORE: impossibile installare le dipendenze.
    pause
    exit /b 1
)

echo [3/3] Compilo in un unico file .exe (ci vogliono 1-3 minuti)...
echo.

:: Includi assets/ solo se la cartella esiste (contiene il logo SGC)
set ASSETS_FLAG=
if exist "assets\" set ASSETS_FLAG=--add-data "assets;assets"

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "P7M_Extract" ^
    %ASSETS_FLAG% ^
    pdf_p7m_extractor.py

if errorlevel 1 (
    echo.
    echo ERRORE durante la compilazione. Leggi i messaggi qui sopra.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   COMPLETATO!
echo ============================================================
echo.
echo   Il file .exe si trova in:
echo   %~dp0dist\P7M_Extract.exe
echo.
echo   Puoi copiare quel file dove vuoi e distribuirlo.
echo   Non richiede Python installato per funzionare.
echo.
pause

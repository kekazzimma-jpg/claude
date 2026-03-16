@echo off
:: ============================================================
::  PDF P7M Signature Extractor
::  Installa Python (se mancante) e avvia il programma
:: ============================================================
title PDF P7M Extractor - Installazione

echo.
echo  =====================================================
echo   PDF P7M Signature Extractor
echo   Estrai il PDF dai file firmati digitalmente (.p7m)
echo  =====================================================
echo.

:: --- Controlla se Python e' gia' installato ---
python --version >nul 2>&1
if not errorlevel 1 goto :python_ok

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :python_ok
)

:: --- Python non trovato: scaricalo e installalo ---
echo [1/3] Python non e' installato sul tuo PC.
echo       Lo scarico e installo automaticamente...
echo       (potrebbe volerci qualche minuto)
echo.

:: Prova con winget (Windows 10/11 moderno)
winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
if not errorlevel 1 (
    echo [OK] Python installato tramite winget.
    :: Aggiorna PATH per questa sessione
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
    goto :install_deps
)

:: Fallback: scarica l'installer di Python dal sito ufficiale
echo       Scarico l'installer Python da python.org...
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing"
if errorlevel 1 (
    echo.
    echo [ERRORE] Impossibile scaricare Python.
    echo.
    echo Installa Python manualmente da: https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione,
    echo poi riesegui questo file.
    echo.
    pause
    exit /b 1
)

:: Installa Python silenziosamente con opzione "add to PATH"
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if errorlevel 1 (
    echo [ERRORE] Installazione Python fallita.
    echo Prova ad eseguire questo file come Amministratore.
    pause
    exit /b 1
)

set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
echo [OK] Python installato.

:install_deps
set PYTHON_CMD=python

:python_ok
if not defined PYTHON_CMD set PYTHON_CMD=python

echo [2/3] Installo le dipendenze del programma...
%PYTHON_CMD% -m pip install --quiet --upgrade pip >nul 2>&1
%PYTHON_CMD% -m pip install --quiet asn1crypto tkinterdnd2
if errorlevel 1 (
    :: Prova senza tkinterdnd2 (drag and drop opzionale)
    %PYTHON_CMD% -m pip install --quiet asn1crypto
)
echo [OK] Dipendenze installate.

echo [3/3] Avvio il programma...
echo.

:: Avvia il programma nella stessa cartella di questo bat
%PYTHON_CMD% "%~dp0pdf_p7m_extractor.py" %*

:: Se il programma si chiude con errore, mostra un messaggio
if errorlevel 1 (
    echo.
    echo [ERRORE] Il programma si e' chiuso con un errore.
    pause
)

@echo off
:: PDF P7M Signature Extractor - Avvio per Windows
:: Installa le dipendenze e avvia l'applicazione

title PDF P7M Signature Extractor

:: Controlla se Python è installato
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato nel PATH.
    echo Scarica Python da https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    pause
    exit /b 1
)

:: Installa le dipendenze necessarie (silenziosa se già installate)
echo Verifica dipendenze...
python -m pip install --quiet asn1crypto tkinterdnd2 2>nul
if errorlevel 1 (
    echo Installo le dipendenze...
    python -m pip install asn1crypto tkinterdnd2
)

:: Avvia l'applicazione (con eventuali file p7m passati come argomento)
python "%~dp0pdf_p7m_extractor.py" %*

@echo off
:: Crea un eseguibile .exe portabile con PyInstaller (Windows)
:: L'exe risultante non richiede Python installato sul sistema

title Build PDF P7M Extractor - Portabile

echo Installazione PyInstaller e dipendenze...
python -m pip install --quiet pyinstaller asn1crypto tkinterdnd2

echo.
echo Creazione eseguibile portabile...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "PDF_P7M_Extractor" ^
    --add-data "requirements.txt;." ^
    "%~dp0pdf_p7m_extractor.py"

if errorlevel 1 (
    echo.
    echo [ERRORE] Build fallita. Controlla i messaggi sopra.
    pause
    exit /b 1
)

echo.
echo [OK] Eseguibile creato in: dist\PDF_P7M_Extractor.exe
echo.
echo Puoi distribuire il file dist\PDF_P7M_Extractor.exe
echo senza bisogno di Python installato sul PC di destinazione.
echo.
pause

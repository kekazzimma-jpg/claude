@echo off
:: Aggiunge "Estrai PDF da P7M" al menu contestuale di Windows per i file .p7m
:: Richiede privilegi di amministratore

title Installazione menu contestuale P7M

net session >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Questo script richiede privilegi di amministratore.
    echo Fai clic destro sul file e seleziona "Esegui come amministratore".
    pause
    exit /b 1
)

:: Percorso dello script principale (stesso di questo bat)
set "SCRIPT_PATH=%~dp0pdf_p7m_extractor.py"
set "AVVIA_PATH=%~dp0avvia.bat"

:: Trova Python nel PATH
for /f "delims=" %%i in ('where python 2^>nul') do (
    set "PYTHON_PATH=%%i"
    goto :found_python
)
echo [ERRORE] Python non trovato. Installa Python prima di continuare.
pause
exit /b 1

:found_python
echo Python trovato: %PYTHON_PATH%

:: Crea associazione file .p7m (se non esiste)
reg add "HKCR\.p7m" /ve /d "P7MFile" /f >nul 2>&1
reg add "HKCR\P7MFile" /ve /d "File P7M (Firma Digitale)" /f >nul 2>&1

:: Aggiunge voce al menu contestuale per tutti i .p7m
reg add "HKCR\.p7m\shell\EstraiPDF" /ve /d "Estrai PDF (Firma Digitale)" /f
reg add "HKCR\.p7m\shell\EstraiPDF" /v "Icon" /d "shell32.dll,71" /f
reg add "HKCR\.p7m\shell\EstraiPDF\command" /ve /d "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\" \"%%1\"" /f

:: Aggiunge anche voce "Apri con PDF P7M Extractor" per qualsiasi file
reg add "HKCR\*\shell\P7MExtractor" /ve /d "PDF P7M Signature Extractor" /f
reg add "HKCR\*\shell\P7MExtractor" /v "Icon" /d "shell32.dll,71" /f
reg add "HKCR\*\shell\P7MExtractor\command" /ve /d "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\" \"%%1\"" /f

echo.
echo [OK] Menu contestuale installato con successo!
echo Ora puoi fare clic destro su qualsiasi file .p7m e scegliere
echo "Estrai PDF (Firma Digitale)"
echo.
pause

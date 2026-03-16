@echo off
:: Rimuove le voci di menu contestuale aggiunte da installa_menu_contestuale_windows.bat
:: Richiede privilegi di amministratore

title Rimozione menu contestuale P7M

net session >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Questo script richiede privilegi di amministratore.
    pause
    exit /b 1
)

reg delete "HKCR\.p7m\shell\EstraiPDF" /f >nul 2>&1
reg delete "HKCR\*\shell\P7MExtractor" /f >nul 2>&1

echo [OK] Menu contestuale rimosso.
pause

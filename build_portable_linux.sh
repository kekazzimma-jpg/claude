#!/usr/bin/env bash
# Crea un eseguibile portabile con PyInstaller (Linux)
# L'eseguibile risultante non richiede Python installato

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installazione PyInstaller e dipendenze..."
python3 -m pip install --quiet pyinstaller asn1crypto tkinterdnd2

echo ""
echo "Creazione eseguibile portabile..."
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name "pdf_p7m_extractor" \
    --add-data "requirements.txt:." \
    "$SCRIPT_DIR/pdf_p7m_extractor.py"

echo ""
echo "[OK] Eseguibile creato in: dist/pdf_p7m_extractor"
echo ""
echo "Puoi distribuire il file dist/pdf_p7m_extractor"
echo "su sistemi Linux compatibili (stessa architettura)."

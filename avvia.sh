#!/usr/bin/env bash
# PDF P7M Signature Extractor - Avvio per Linux/macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Controlla Python 3
if ! command -v python3 &>/dev/null; then
    echo "[ERRORE] Python 3 non trovato."
    echo "Installa Python 3 con il tuo gestore pacchetti:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Fedora:        sudo dnf install python3 python3-pip"
    echo "  macOS:         brew install python3"
    exit 1
fi

# Installa dipendenze
echo "Verifica dipendenze Python..."
python3 -m pip install --quiet asn1crypto tkinterdnd2 2>/dev/null || \
    python3 -m pip install asn1crypto tkinterdnd2

# Avvia l'applicazione
python3 "$SCRIPT_DIR/pdf_p7m_extractor.py" "$@"

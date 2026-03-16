#!/usr/bin/env bash
# Aggiunge "Estrai PDF da P7M" al menu contestuale di Nautilus (GNOME)
# e associa l'estensione .p7m all'applicazione.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="pdf-p7m-extractor"
DESKTOP_FILE="$HOME/.local/share/applications/${APP_NAME}.desktop"
MIME_FILE="$HOME/.local/share/mime/packages/${APP_NAME}.xml"

echo "Installazione menu contestuale per P7M..."

# 1. Crea il file .desktop
mkdir -p "$HOME/.local/share/applications"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=PDF P7M Signature Extractor
Comment=Estrai PDF da file firmati digitalmente P7M
Exec=python3 ${SCRIPT_DIR}/pdf_p7m_extractor.py %F
Icon=document-open
Terminal=false
Type=Application
MimeType=application/pkcs7-mime;application/x-pkcs7-mime;
Categories=Office;Utility;
EOF

chmod +x "$DESKTOP_FILE"
echo "  [OK] File .desktop creato: $DESKTOP_FILE"

# 2. Registra il tipo MIME per .p7m
mkdir -p "$HOME/.local/share/mime/packages"
cat > "$MIME_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/pkcs7-mime">
    <comment>File P7M (Firma Digitale)</comment>
    <glob pattern="*.p7m"/>
    <glob pattern="*.P7M"/>
  </mime-type>
</mime-info>
EOF

echo "  [OK] Tipo MIME registrato: $MIME_FILE"

# 3. Aggiorna il database MIME e delle applicazioni
update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
xdg-mime default "${APP_NAME}.desktop" application/pkcs7-mime 2>/dev/null || true

echo ""
echo "[OK] Installazione completata!"
echo "Riavvia il file manager per vedere le modifiche."
echo ""
echo "Per aprire un file P7M dal terminale:"
echo "  python3 ${SCRIPT_DIR}/pdf_p7m_extractor.py file.pdf.p7m"

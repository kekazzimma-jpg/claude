# PDF P7M Signature Extractor

Strumento portabile per **estrarre il PDF** da file firmati digitalmente in formato **P7M** e visualizzare le **informazioni sulla firma digitale**.

## Funzionalità

- Apre file `.p7m` tramite finestra di dialogo, drag & drop o menu contestuale
- Estrae il PDF incorporato e lo salva o lo apre direttamente
- Mostra per ogni firma: firmatario, CA, date validità certificato, data firma, algoritmi
- Supporta più firme sullo stesso documento
- Elaborazione multipla: puoi caricare più file contemporaneamente
- Portabile: funziona su Windows, Linux e macOS con solo Python installato

## Avvio rapido

### Requisiti
- Python 3.8 o superiore
- Connessione internet (solo per la prima installazione delle dipendenze)

### Windows
Doppio clic su **`avvia.bat`** — installa le dipendenze in automatico e avvia l'applicazione.

### Linux / macOS
```bash
bash avvia.sh
```

### Da riga di comando (tutti i sistemi)
```bash
pip install asn1crypto tkinterdnd2
python pdf_p7m_extractor.py [file1.p7m file2.p7m ...]
```

## Menu contestuale

### Windows
Esegui come amministratore:
```
installa_menu_contestuale_windows.bat
```
Poi fai clic destro su qualsiasi file `.p7m` → **"Estrai PDF (Firma Digitale)"**

Per rimuovere il menu contestuale:
```
rimuovi_menu_contestuale_windows.bat
```

### Linux (GNOME/Nautilus)
```bash
bash installa_menu_contestuale_linux.sh
```

## Creare un eseguibile portabile (senza Python)

Se vuoi distribuire l'applicazione senza richiedere Python:

### Windows
```
build_portable_windows.bat
```
Produce `dist\PDF_P7M_Extractor.exe`

### Linux
```bash
bash build_portable_linux.sh
```
Produce `dist/pdf_p7m_extractor`

## Formato P7M

Il formato P7M (PKCS#7 / CMS SignedData, RFC 5652) è il formato standard per le **firme digitali in Italia** (CAdES-BES). Contiene:
- Il documento originale (PDF, XML, ecc.)
- Una o più firme digitali
- I certificati dei firmatari e la catena di CA

## Dipendenze Python

| Pacchetto | Uso | Obbligatorio |
|-----------|-----|:---:|
| `asn1crypto` | Parsing struttura P7M/CMS | ✓ |
| `tkinterdnd2` | Drag & drop nella finestra | No |

## Struttura file

```
pdf_p7m_extractor.py              # Applicazione principale
avvia.bat                          # Avvio Windows
avvia.sh                           # Avvio Linux/macOS
installa_menu_contestuale_windows.bat   # Menu contestuale Windows
rimuovi_menu_contestuale_windows.bat    # Rimuove menu contestuale Windows
installa_menu_contestuale_linux.sh      # Menu contestuale Linux (GNOME)
build_portable_windows.bat         # Build .exe portabile
build_portable_linux.sh            # Build eseguibile Linux portabile
requirements.txt                   # Dipendenze Python
```

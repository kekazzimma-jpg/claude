#!/usr/bin/env python3
"""
Estrai P7M v1.0
---------------
Strumento portabile per estrarre il PDF da file P7M firmati digitalmente
e visualizzare le informazioni sulla firma digitale.

Utilizzo:
  python pdf_p7m_extractor.py [file1.p7m file2.p7m ...]
  Oppure apri i file trascinandoli sulla finestra (drag & drop).

Dipendenze: asn1crypto, tkinterdnd2, Pillow
"""

import os
import sys
import platform
import subprocess
import threading
import tempfile
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime

# Cartella degli asset (relativa allo script)
_ASSETS_DIR = Path(__file__).parent / 'assets'

# ---------------------------------------------------------------------------
# Dependency check / auto-install
# ---------------------------------------------------------------------------

def _check_deps():
    missing = []
    for mod in ('asn1crypto', 'tkinterdnd2'):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if not missing:
        return
    # Try to install silently first
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '--quiet'] + missing,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return
    except Exception:
        pass
    # Ask user
    root = tk.Tk()
    root.withdraw()
    ok = messagebox.askyesno(
        "Dipendenze mancanti",
        f"I seguenti pacchetti Python sono richiesti ma non installati:\n"
        f"  {', '.join(missing)}\n\n"
        f"Vuoi installarli adesso?",
    )
    root.destroy()
    if ok:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        except Exception as e:
            tk.Tk().withdraw()
            messagebox.showerror("Errore installazione", str(e))
            sys.exit(1)
        messagebox.showinfo("Fatto", "Pacchetti installati. Riavvia l'applicazione.")
    sys.exit(0)

_check_deps()

# ---------------------------------------------------------------------------
# Imports after dep check
# ---------------------------------------------------------------------------
from asn1crypto import cms, pem, core  # noqa: E402

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _load_logo(size: tuple[int, int] | None = None):
    """Carica il logo SGC come PhotoImage. Ritorna None se non disponibile."""
    if not _HAS_PIL:
        return None
    logo_path = _ASSETS_DIR / 'logo_sgc.png'
    if not logo_path.exists():
        return None
    try:
        img = Image.open(logo_path).convert('RGBA')
        if size:
            img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# P7M Parser
# ---------------------------------------------------------------------------

class P7MParser:
    """Parse P7M (PKCS#7 / CMS SignedData) files and extract content + signature info."""

    @staticmethod
    def extract(file_path: str) -> dict:
        """
        Returns:
            {
              'pdf_data': bytes,
              'signatures': [...],
              'all_certificates': [...],
            }
        """
        with open(file_path, 'rb') as fh:
            data = fh.read()

        # Handle PEM-encoded P7M
        if pem.detect(data):
            _, _, data = pem.unarmor(data)

        try:
            content_info = cms.ContentInfo.load(data)
        except Exception as exc:
            raise ValueError(f"File non valido (parsing fallito): {exc}") from exc

        if content_info['content_type'].native != 'signed_data':
            raise ValueError(
                f"Tipo contenuto inatteso: {content_info['content_type'].native}"
            )

        signed_data = content_info['content']

        # --- Extract embedded content (the PDF) ---
        pdf_data = P7MParser._extract_pdf(signed_data)

        # --- Parse certificates ---
        certs_by_key = P7MParser._parse_certificates(signed_data)

        # --- Parse signer infos ---
        signatures = P7MParser._parse_signers(signed_data, certs_by_key)

        return {
            'pdf_data': pdf_data,
            'signatures': signatures,
            'all_certificates': list(certs_by_key.values()),
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_pdf(signed_data) -> bytes:
        encap = signed_data['encap_content_info']
        content = encap['content']

        candidates = []

        # Attempt 1: asn1crypto native parsing
        try:
            raw = content.native
            if isinstance(raw, bytes):
                candidates.append(raw)
        except Exception:
            pass

        # Attempt 2: parse the inner DER as OctetString
        try:
            inner = core.OctetString.load(content.contents)
            raw = inner.native
            if isinstance(raw, bytes):
                candidates.append(raw)
        except Exception:
            pass

        # Attempt 3: raw DER contents (sometimes the OCTET STRING IS the DER)
        try:
            raw = content.contents
            if isinstance(raw, bytes):
                candidates.append(raw)
        except Exception:
            pass

        # Attempt 4: direct DER of the Any field
        try:
            raw = bytes(content)
            if isinstance(raw, bytes):
                candidates.append(raw)
        except Exception:
            pass

        for cand in candidates:
            if cand and cand.lstrip()[:4] == b'%PDF':
                return cand
            # Strip a leading OCTET STRING tag if present (04 xx ...)
            if cand and len(cand) > 2 and cand[0] == 0x04:
                stripped = P7MParser._strip_octet_string(cand)
                if stripped and stripped.lstrip()[:4] == b'%PDF':
                    return stripped

        raise ValueError(
            "Impossibile estrarre il PDF dal file P7M. "
            "Il contenuto incorporato non sembra un PDF valido."
        )

    @staticmethod
    def _strip_octet_string(data: bytes) -> bytes:
        """Strip DER OCTET STRING tag+length, return raw payload."""
        if not data or data[0] != 0x04:
            return data
        idx = 1
        length_byte = data[idx]
        idx += 1
        if length_byte & 0x80:
            n = length_byte & 0x7F
            length = int.from_bytes(data[idx:idx + n], 'big')
            idx += n
        else:
            length = length_byte
        return data[idx:idx + length]

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_certificates(signed_data) -> dict:
        certs = {}
        if not signed_data['certificates']:
            return certs
        for cert_choice in signed_data['certificates']:
            try:
                cert = cert_choice.chosen
                validity = cert['tbs_certificate']['validity']
                key = (cert.issuer.human_friendly, str(cert.serial_number))
                certs[key] = {
                    'subject': cert.subject.human_friendly,
                    'issuer': cert.issuer.human_friendly,
                    'serial': str(cert.serial_number),
                    'not_before': validity['not_before'].native,
                    'not_after': validity['not_after'].native,
                }
            except Exception:
                continue
        return certs

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_signers(signed_data, certs_by_key: dict) -> list:
        signatures = []
        for signer_info in signed_data['signer_infos']:
            sig = {
                'signing_time': None,
                'certificate': None,
                'digest_algorithm': None,
                'signature_algorithm': None,
            }

            try:
                sig['digest_algorithm'] = (
                    signer_info['digest_algorithm']['algorithm'].native.upper()
                )
            except Exception:
                pass

            try:
                sig['signature_algorithm'] = (
                    signer_info['signature_algorithm']['algorithm'].native.upper()
                )
            except Exception:
                pass

            # Authenticated attributes
            signed_attrs = signer_info['signed_attrs']
            if signed_attrs:
                for attr in signed_attrs:
                    try:
                        if attr['type'].native == 'signing_time':
                            sig['signing_time'] = attr['values'][0].native
                    except Exception:
                        continue

            # Link certificate
            sid = signer_info['sid']
            try:
                if sid.name == 'issuer_and_serial_number':
                    issuer = sid.chosen['issuer'].human_friendly
                    serial = str(sid.chosen['serial_number'].native)
                    sig['certificate'] = certs_by_key.get((issuer, serial))
            except Exception:
                pass

            signatures.append(sig)
        return signatures


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _extract_cn(dn_string: str) -> str:
    """Extract CN value from a Distinguished Name string."""
    for part in dn_string.split(','):
        part = part.strip()
        if re.match(r'(?i)^CN\s*=', part):
            return part.split('=', 1)[1].strip()
    return dn_string.split(',')[0].strip()


def _fmt_date(dt) -> str:
    if dt is None:
        return 'N/D'
    try:
        return dt.strftime('%d/%m/%Y %H:%M:%S %Z').strip()
    except Exception:
        return str(dt)


def _is_expired(dt) -> bool:
    if dt is None:
        return False
    try:
        naive = dt.replace(tzinfo=None)
        return naive < datetime.now()
    except Exception:
        return False


def _open_file(path: str):
    """Open a file with the system default application."""
    try:
        if platform.system() == 'Windows':
            os.startfile(path)
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
    except Exception as exc:
        messagebox.showerror("Errore apertura", f"Impossibile aprire il file:\n{exc}")


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

FONT_MONO = ('Courier', 10)
FONT_MONO_BOLD = ('Courier', 10, 'bold')
FONT_HEADER = ('Courier', 11, 'bold')

COLOR_HEADER = '#1565c0'
COLOR_OK = '#2e7d32'
COLOR_WARN = '#b71c1c'
COLOR_KEY = '#333333'
COLOR_BG_DROP = '#e3f2fd'
COLOR_FG_DROP = '#1565c0'
COLOR_BG_TEXT = '#fafafa'


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Estrai P7M")
        self.root.geometry("980x680")
        self.root.minsize(720, 520)

        # Icona della finestra
        self._logo_icon = _load_logo(size=(64, 81))
        if self._logo_icon:
            try:
                self.root.iconphoto(True, self._logo_icon)
            except Exception:
                pass

        self.results: dict = {}   # file_path -> {'ok': bool, 'data': ..., 'error': ...}
        self.output_dir: str | None = None

        self._build_menu()
        self._build_ui()
        self._setup_dnd()

        # Handle command-line arguments
        if len(sys.argv) > 1:
            files = [a for a in sys.argv[1:] if os.path.isfile(a)]
            if files:
                self.root.after(150, lambda: self._process_files(files))

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Apri P7M…", accelerator="Ctrl+O", command=self._open_files)
        file_menu.add_command(label="Salva PDF selezionato…", command=self._save_pdf)
        file_menu.add_separator()
        file_menu.add_command(
            label="Estrai tutto — crea cartelle estratti/certificati",
            command=self._save_all,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Pulisci lista", command=self._clear_list)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.root.quit)

        self.root.bind_all('<Control-o>', lambda _e: self._open_files())

        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        help_menu.add_command(label="Informazioni…", command=self._show_about)

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Toolbar ──────────────────────────────────────────────────
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=6, pady=4)

        ttk.Button(toolbar, text="Apri P7M…", command=self._open_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Estrai tutto", command=self._save_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Pulisci lista", command=self._clear_list).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        ttk.Label(toolbar, text="Salva in:").pack(side=tk.LEFT, padx=(0, 2))
        self._out_label_var = tk.StringVar(value="stessa cartella del file originale")
        ttk.Button(toolbar, text="Scegli cartella…", command=self._choose_output).pack(side=tk.LEFT, padx=2)
        ttk.Label(toolbar, textvariable=self._out_label_var, foreground='gray').pack(side=tk.LEFT, padx=4)

        # ── Drop zone ────────────────────────────────────────────────
        self._drop_label = tk.Label(
            self.root,
            text="  Trascina qui i file P7M  —  oppure usa il pulsante «Apri P7M»  ",
            bg=COLOR_BG_DROP, fg=COLOR_FG_DROP,
            font=('TkDefaultFont', 11),
            relief=tk.GROOVE, bd=2,
            pady=14,
        )
        self._drop_label.pack(fill=tk.X, padx=6, pady=(0, 4))

        # ── PanedWindow ──────────────────────────────────────────────
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left: file list
        left = ttk.LabelFrame(paned, text="File elaborati")
        paned.add(left, weight=1)

        self._tree = ttk.Treeview(
            left,
            columns=('status',),
            show='tree headings',
            selectmode='browse',
        )
        self._tree.heading('#0', text='File')
        self._tree.heading('status', text='Stato')
        self._tree.column('#0', minwidth=120)
        self._tree.column('status', width=100, anchor=tk.CENTER, stretch=False)
        self._tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        vsb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self._tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.bind('<<TreeviewSelect>>', self._on_select)

        # Right: detail + action buttons
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        btn_row = ttk.Frame(right)
        btn_row.pack(fill=tk.X, pady=(0, 4))

        self._save_btn = ttk.Button(
            btn_row, text="Salva PDF", command=self._save_pdf, state=tk.DISABLED
        )
        self._save_btn.pack(side=tk.LEFT, padx=2)

        self._open_btn = ttk.Button(
            btn_row, text="Apri PDF", command=self._open_pdf, state=tk.DISABLED
        )
        self._open_btn.pack(side=tk.LEFT, padx=2)

        detail_frame = ttk.LabelFrame(right, text="Informazioni firma digitale")
        detail_frame.pack(fill=tk.BOTH, expand=True)

        self._detail = tk.Text(
            detail_frame,
            wrap=tk.WORD,
            font=FONT_MONO,
            state=tk.DISABLED,
            bg=COLOR_BG_TEXT,
            relief=tk.FLAT,
        )
        self._detail.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        detail_vsb = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self._detail.yview)
        detail_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._detail.configure(yscrollcommand=detail_vsb.set)

        # Text tags
        self._detail.tag_configure('header', font=FONT_HEADER, foreground=COLOR_HEADER)
        self._detail.tag_configure('key', font=FONT_MONO_BOLD)
        self._detail.tag_configure('ok', foreground=COLOR_OK)
        self._detail.tag_configure('warn', foreground=COLOR_WARN)
        self._detail.tag_configure('separator', foreground='#9e9e9e')

        # ── Status bar ───────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Pronto. Apri o trascina file P7M per iniziare.")
        status_bar = ttk.Label(
            self.root, textvariable=self._status_var,
            relief=tk.SUNKEN, anchor=tk.W,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=2)

    # ------------------------------------------------------------------
    # Drag & Drop
    # ------------------------------------------------------------------
    def _setup_dnd(self):
        if _HAS_DND:
            for widget in (self.root, self._drop_label, self._tree):
                try:
                    widget.drop_target_register(DND_FILES)
                    widget.dnd_bind('<<Drop>>', self._on_drop)
                except Exception:
                    pass
        else:
            self._drop_label.config(
                text="Apri file P7M con il pulsante «Apri P7M»",
                fg='gray',
                bg='#f5f5f5',
            )

    def _on_drop(self, event):
        files = []
        # tkinterdnd2 wraps paths with spaces in {}
        for m in re.finditer(r'\{([^}]+)\}|(\S+)', event.data):
            path = m.group(1) or m.group(2)
            if os.path.isfile(path):
                files.append(path)
        if files:
            self._process_files(files)
        else:
            messagebox.showwarning("Nessun file", "Nessun file valido trovato nel rilascio.")

    # ------------------------------------------------------------------
    # File processing
    # ------------------------------------------------------------------
    def _open_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona file P7M",
            filetypes=[
                ("File P7M firmati", "*.p7m *.P7M *.pdf.p7m"),
                ("Tutti i file", "*.*"),
            ],
        )
        if files:
            self._process_files(list(files))

    def _choose_output(self):
        folder = filedialog.askdirectory(title="Cartella di destinazione per i PDF estratti")
        if folder:
            self.output_dir = folder
            self._out_label_var.set(f"→ {folder}")

    def _process_files(self, file_paths: list):
        for fp in file_paths:
            fp = os.path.normpath(fp)
            name = os.path.basename(fp)
            if fp not in self.results:
                self._tree.insert('', tk.END, iid=fp, text=name, values=('In corso…',))
            else:
                self._tree.set(fp, 'status', 'In corso…')
            self.results[fp] = None
            threading.Thread(target=self._process_one, args=(fp,), daemon=True).start()

    def _process_one(self, file_path: str):
        try:
            result = P7MParser.extract(file_path)
            self.results[file_path] = {'ok': True, 'data': result}
            self.root.after(0, lambda fp=file_path: self._update_item(fp, 'OK ✓'))
        except Exception as exc:
            self.results[file_path] = {'ok': False, 'error': str(exc)}
            self.root.after(0, lambda fp=file_path: self._update_item(fp, 'Errore ✗'))

    def _update_item(self, file_path: str, status: str):
        try:
            self._tree.set(file_path, 'status', status)
        except Exception:
            pass
        self._status_var.set(f"Elaborato: {os.path.basename(file_path)}")
        # Auto-select if it's the only item
        if len(self._tree.get_children()) == 1:
            self._tree.selection_set(file_path)
            self._tree.focus(file_path)
            self._on_select(None)

    # ------------------------------------------------------------------
    # Selection & Detail panel
    # ------------------------------------------------------------------
    def _on_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        fp = sel[0]
        result = self.results.get(fp)
        self._show_detail(fp, result)
        has_result = result and result.get('ok')
        state = tk.NORMAL if has_result else tk.DISABLED
        self._save_btn.config(state=state)
        self._open_btn.config(state=state)

    def _show_detail(self, file_path: str, result):
        t = self._detail
        t.config(state=tk.NORMAL)
        t.delete('1.0', tk.END)

        def w(text, tag=None):
            if tag:
                t.insert(tk.END, text, tag)
            else:
                t.insert(tk.END, text)

        if result is None:
            w("Elaborazione in corso…")
            t.config(state=tk.DISABLED)
            return

        if not result.get('ok'):
            w("ERRORE DURANTE L'ELABORAZIONE\n\n", 'header')
            w(result.get('error', 'Errore sconosciuto'), 'warn')
            t.config(state=tk.DISABLED)
            return

        data = result['data']
        pdf_size = len(data['pdf_data'])
        sigs = data['signatures']
        all_certs = data['all_certificates']

        # ── File info ──
        w("INFORMAZIONI FILE\n", 'header')
        w("  File: ", 'key'); w(f"{os.path.basename(file_path)}\n")
        w("  Percorso: ", 'key'); w(f"{file_path}\n")
        w("  Dimensione PDF estratto: ", 'key')
        w(f"{pdf_size:,} byte ({pdf_size / 1024:.1f} KB)\n")
        w("  Numero firme trovate: ", 'key'); w(f"{len(sigs)}\n\n")

        # ── Signatures ──
        w(f"FIRME DIGITALI ({len(sigs)})\n", 'header')

        for i, sig in enumerate(sigs, 1):
            w(f"\n  ╔══ Firma #{i} ", 'separator')
            w("═" * 50 + "\n", 'separator')

            cert = sig.get('certificate')
            if cert:
                cn = _extract_cn(cert['subject'])
                w("  ║  Firmatario:        ", 'key'); w(f"{cn}\n")
                w("  ║  Soggetto (DN):     ", 'key'); w(f"{cert['subject']}\n")
                w("  ║  Emittente (CA):    ", 'key'); w(f"{cert['issuer']}\n")
                w("  ║  Numero seriale:    ", 'key'); w(f"{cert['serial']}\n")

                nb = cert['not_before']
                na = cert['not_after']
                w("  ║  Cert. valido dal:  ", 'key'); w(f"{_fmt_date(nb)}\n")
                w("  ║  Cert. valido fino: ", 'key')
                w(f"{_fmt_date(na)}")
                if _is_expired(na):
                    w("  ⚠ SCADUTO\n", 'warn')
                else:
                    w("  ✓ valido\n", 'ok')
            else:
                w("  ║  Certificato:       ", 'key'); w("non trovato nella busta\n", 'warn')

            st = sig.get('signing_time')
            w("  ║  Data firma:        ", 'key')
            if st:
                w(f"{_fmt_date(st)}\n", 'ok')
            else:
                w("non presente negli attributi firmati\n", 'warn')

            w("  ║  Algoritmo digest:  ", 'key'); w(f"{sig.get('digest_algorithm', 'N/D')}\n")
            w("  ║  Algoritmo firma:   ", 'key'); w(f"{sig.get('signature_algorithm', 'N/D')}\n")
            w("  ╚" + "═" * 57 + "\n", 'separator')

        # ── Certificate chain ──
        if len(all_certs) > len(sigs):
            w(f"\nCATENA CERTIFICATI ({len(all_certs)} certificati)\n", 'header')
            for i, cert in enumerate(all_certs, 1):
                cn = _extract_cn(cert['subject'])
                issuer_cn = _extract_cn(cert['issuer'])
                w(f"  [{i}] ", 'key'); w(f"{cn}\n")
                w(f"      Emittente: "); w(f"{issuer_cn}\n")
                w(f"      Validità:  ")
                w(f"{_fmt_date(cert['not_before'])} → {_fmt_date(cert['not_after'])}\n")

        t.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Save / Open PDF
    # ------------------------------------------------------------------
    def _get_default_output_path(self, source_path: str) -> str:
        source = Path(source_path)
        stem = source.stem  # e.g. "doc.pdf" from "doc.pdf.p7m"
        if not stem.lower().endswith('.pdf'):
            stem += '.pdf'
        base = Path(self.output_dir) if self.output_dir else source.parent
        return str(base / stem)

    def _save_pdf(self):
        sel = self._tree.selection()
        if not sel:
            return
        fp = sel[0]
        result = self.results.get(fp)
        if not result or not result.get('ok'):
            return
        suggested = self._get_default_output_path(fp)
        out_path = filedialog.asksaveasfilename(
            title="Salva PDF estratto",
            initialfile=os.path.basename(suggested),
            initialdir=os.path.dirname(suggested),
            defaultextension='.pdf',
            filetypes=[("File PDF", "*.pdf"), ("Tutti i file", "*.*")],
        )
        if out_path:
            with open(out_path, 'wb') as fh:
                fh.write(result['data']['pdf_data'])
            self._status_var.set(f"Salvato: {out_path}")
            messagebox.showinfo("Salvato", f"PDF salvato in:\n{out_path}")

    def _save_all(self):
        """Salvataggio bulk: PDF in estratti/, dettagli certificati in estratti/certificati/."""
        ok_files = {fp: r for fp, r in self.results.items() if r and r.get('ok')}
        if not ok_files:
            messagebox.showwarning("Nessun file", "Nessun PDF estratto con successo da salvare.")
            return

        # Determina cartella base: output_dir se impostato, altrimenti cartella del primo file
        if self.output_dir:
            base = Path(self.output_dir)
        else:
            base = Path(next(iter(ok_files))).parent

        estratti_dir = base / 'estratti'
        certificati_dir = estratti_dir / 'certificati'

        try:
            estratti_dir.mkdir(parents=True, exist_ok=True)
            certificati_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Errore cartella", f"Impossibile creare le cartelle:\n{exc}")
            return

        done_pdf, done_cert, errors = 0, 0, []

        for fp, result in ok_files.items():
            source = Path(fp)
            stem = source.stem
            if not stem.lower().endswith('.pdf'):
                stem += '.pdf'
            pdf_path = estratti_dir / stem

            try:
                with open(pdf_path, 'wb') as fh:
                    fh.write(result['data']['pdf_data'])
                done_pdf += 1
            except Exception as exc:
                errors.append(f"PDF {source.name}: {exc}")
                continue

            cert_text = self._build_cert_text(fp, result['data'])
            cert_path = certificati_dir / (source.name + '.txt')
            try:
                with open(cert_path, 'w', encoding='utf-8') as fh:
                    fh.write(cert_text)
                done_cert += 1
            except Exception as exc:
                errors.append(f"Certificato {source.name}: {exc}")

        self._status_var.set(f"Bulk: {done_pdf} PDF e {done_cert} certificati salvati.")
        msg = (
            f"Operazione completata!\n\n"
            f"  PDF salvati:        {done_pdf}\n"
            f"  File certificati:   {done_cert}\n\n"
            f"Cartella PDF:         {estratti_dir}\n"
            f"Cartella certificati: {certificati_dir}"
        )
        if errors:
            msg += "\n\nErrori:\n" + "\n".join(errors)
        messagebox.showinfo("Salvataggio bulk completato", msg)

    def _build_cert_text(self, file_path: str, data: dict) -> str:
        """Genera un report testuale con i dettagli dei certificati di un file P7M."""
        lines = []
        sep = "=" * 60
        lines.append(sep)
        lines.append("INFORMAZIONI FIRMA DIGITALE")
        lines.append(sep)
        lines.append(f"File sorgente:  {os.path.basename(file_path)}")
        lines.append(f"Percorso:       {file_path}")
        pdf_size = len(data['pdf_data'])
        lines.append(f"Dimensione PDF: {pdf_size:,} byte ({pdf_size / 1024:.1f} KB)")
        sigs = data['signatures']
        all_certs = data['all_certificates']
        lines.append(f"Numero firme:   {len(sigs)}")
        lines.append("")

        lines.append(f"FIRME DIGITALI ({len(sigs)})")
        lines.append("-" * 60)
        for i, sig in enumerate(sigs, 1):
            lines.append(f"\nFirma #{i}:")
            cert = sig.get('certificate')
            if cert:
                cn = _extract_cn(cert['subject'])
                lines.append(f"  Firmatario:        {cn}")
                lines.append(f"  Soggetto (DN):     {cert['subject']}")
                lines.append(f"  Emittente (CA):    {cert['issuer']}")
                lines.append(f"  Numero seriale:    {cert['serial']}")
                nb = cert['not_before']
                na = cert['not_after']
                lines.append(f"  Cert. valido dal:  {_fmt_date(nb)}")
                expired_tag = "  [SCADUTO]" if _is_expired(na) else "  [valido]"
                lines.append(f"  Cert. valido fino: {_fmt_date(na)}{expired_tag}")
            else:
                lines.append("  Certificato: non trovato nella busta")
            st = sig.get('signing_time')
            lines.append(f"  Data firma:        {_fmt_date(st) if st else 'non presente'}")
            lines.append(f"  Algoritmo digest:  {sig.get('digest_algorithm', 'N/D')}")
            lines.append(f"  Algoritmo firma:   {sig.get('signature_algorithm', 'N/D')}")

        if len(all_certs) > len(sigs):
            lines.append("")
            lines.append(f"CATENA CERTIFICATI ({len(all_certs)} certificati)")
            lines.append("-" * 60)
            for i, cert in enumerate(all_certs, 1):
                cn = _extract_cn(cert['subject'])
                issuer_cn = _extract_cn(cert['issuer'])
                lines.append(f"  [{i}] {cn}")
                lines.append(f"      Emittente: {issuer_cn}")
                lines.append(f"      Validita:  {_fmt_date(cert['not_before'])} -> {_fmt_date(cert['not_after'])}")

        lines.append("")
        lines.append(sep)
        lines.append(f"Report generato il: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(sep)
        return "\n".join(lines)

    def _open_pdf(self):
        sel = self._tree.selection()
        if not sel:
            return
        fp = sel[0]
        result = self.results.get(fp)
        if not result or not result.get('ok'):
            return
        stem = Path(fp).stem
        if not stem.lower().endswith('.pdf'):
            stem += '.pdf'
        tmp_dir = tempfile.mkdtemp(prefix='p7m_extractor_')
        tmp_path = os.path.join(tmp_dir, stem)
        with open(tmp_path, 'wb') as fh:
            fh.write(result['data']['pdf_data'])
        self._status_var.set(f"Aperto: {tmp_path}")
        _open_file(tmp_path)

    def _clear_list(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        self.results.clear()
        self._detail.config(state=tk.NORMAL)
        self._detail.delete('1.0', tk.END)
        self._detail.config(state=tk.DISABLED)
        self._save_btn.config(state=tk.DISABLED)
        self._open_btn.config(state=tk.DISABLED)
        self._status_var.set("Lista pulita.")

    def _show_about(self):
        win = tk.Toplevel(self.root)
        win.title("Informazioni")
        win.resizable(False, False)
        win.grab_set()

        logo = _load_logo(size=(82, 104))
        if logo:
            lbl_logo = tk.Label(win, image=logo, bg='white')
            lbl_logo.image = logo  # keep reference
            lbl_logo.pack(pady=(16, 8))

        tk.Label(
            win,
            text="Estrai P7M v1.0",
            font=('TkDefaultFont', 13, 'bold'),
        ).pack()
        tk.Label(
            win,
            text="Comune di San Giorgio a Cremano",
            font=('TkDefaultFont', 10, 'italic'),
            foreground='#1565c0',
        ).pack(pady=(2, 4))
        tk.Label(
            win,
            text="Sviluppato per il IV Settore",
            font=('TkDefaultFont', 9),
            foreground='#555555',
        ).pack(pady=(0, 10))

        info = (
            "Estrae il PDF da file firmati digitalmente in formato P7M\n"
            "e mostra le informazioni sulla firma digitale.\n\n"
            "Formati supportati: P7M (PKCS#7 / CMS SignedData)\n"
            "Codifiche: DER e PEM\n\n"
            "Librerie: asn1crypto, tkinterdnd2, Pillow, tkinter"
        )
        tk.Label(win, text=info, justify=tk.CENTER, font=('TkDefaultFont', 10)).pack(padx=20)

        ttk.Button(win, text="Chiudi", command=win.destroy).pack(pady=14)
        win.wait_window()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente local de Direct Print Pro
=================================

Corre esto en la computadora donde está físicamente conectada (o emparejada
por Bluetooth) la impresora. Se conecta a tu Odoo, pregunta cada pocos
segundos si hay trabajos de impresión pendientes para esta estación, y los
manda a la impresora indicada usando lo que ya tiene instalado Windows/CUPS.

No necesita nada raro: solo Python 3 (que ya trae la mayoría de sistemas) y,
en Windows, el paquete "pywin32" (`pip install pywin32`). En Linux/Mac usa
el comando `lp` de CUPS, que ya viene instalado en casi cualquier distro.

Configuración: completa ODOO_URL y AGENT_TOKEN abajo (el token se genera
solo al crear el "Agente / Estación" en Odoo, en Direct Print Pro).
"""

import base64
import json
import platform
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# CONFIGURACIÓN — edita estas dos líneas
# ---------------------------------------------------------------------------
ODOO_URL = "http://localhost:8069"       # URL pública de tu Odoo, sin / al final
AGENT_TOKEN = "PEGA-AQUI-EL-TOKEN"        # Token del agente (Direct Print Pro > Agentes)
POLL_INTERVAL_SECONDS = 3


def log(msg):
    print("[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg), flush=True)


def http_post_json(path, payload, timeout=15):
    url = ODOO_URL.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def poll_jobs():
    return http_post_json("/direct_print/agent/poll", {"token": AGENT_TOKEN})


def ack_job(job_id, success, error_message=None):
    http_post_json("/direct_print/agent/ack", {
        "token": AGENT_TOKEN, "job_id": job_id, "success": success, "error_message": error_message,
    })


# ---------------------------------------------------------------------------
# Impresión — Windows (pywin32) o Linux/Mac (CUPS `lp`)
# ---------------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    try:
        import win32print
    except ImportError:
        win32print = None
else:
    win32print = None


def print_raw_windows(printer_name, data):
    h_printer = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(h_printer, 1, ("Direct Print Pro", None, "RAW"))
        try:
            win32print.StartPagePrinter(h_printer)
            win32print.WritePrinter(h_printer, data)
            win32print.EndPagePrinter(h_printer)
        finally:
            win32print.EndDocPrinter(h_printer)
    finally:
        win32print.ClosePrinter(h_printer)


def find_sumatra():
    import os
    for path in (r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
                 r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe"):
        if os.path.isfile(path):
            return path
    return None


def print_pdf_windows(printer_name, data):
    sumatra = find_sumatra()
    if not sumatra:
        raise RuntimeError(
            "Para imprimir PDF hace falta SumatraPDF instalado en esta PC "
            "(gratis: sumatrapdfreader.org/download-free-pdf-viewer). "
            "Las impresoras de etiquetas/recibos no necesitan esto.")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data)
        tmp_path = f.name
    result = subprocess.run(
        [sumatra, "-print-to", printer_name, "-silent", "-exit-when-done", tmp_path],
        timeout=60, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("SumatraPDF terminó con error: %s" % (result.stderr.decode(errors="replace")))


def print_unix(printer_name, data, is_pdf):
    suffix = ".pdf" if is_pdf else ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        tmp_path = f.name
    args = ["lp", "-d", printer_name]
    if not is_pdf:
        args += ["-o", "raw"]
    args.append(tmp_path)
    result = subprocess.run(args, timeout=60, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("`lp` terminó con error: %s" % (result.stderr.decode(errors="replace")))


def print_job(printer_name, content_type, data):
    if IS_WINDOWS:
        if win32print is None:
            raise RuntimeError("Instala pywin32 en esta PC: pip install pywin32")
        if content_type == "raw":
            print_raw_windows(printer_name, data)
        else:
            print_pdf_windows(printer_name, data)
    else:
        print_unix(printer_name, data, is_pdf=(content_type != "raw"))


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------
def main():
    if AGENT_TOKEN == "PEGA-AQUI-EL-TOKEN":
        log("ERROR: edita este archivo y pon tu token real (Direct Print Pro > Agentes / Estaciones).")
        sys.exit(1)

    log("Agente de Direct Print Pro iniciado. Conectando a %s ..." % ODOO_URL)
    while True:
        try:
            result = poll_jobs()
            for job in result.get("jobs", []):
                job_id = job["job_id"]
                printer_name = job["printer_name"]
                log("Imprimiendo trabajo #%s en '%s' (%s)..." % (job_id, printer_name, job["filename"]))
                try:
                    data = base64.b64decode(job["content"]) if job["content"] else b""
                    print_job(printer_name, job["content_type"], data)
                    ack_job(job_id, True)
                    log("  -> impreso OK")
                except Exception as exc:
                    ack_job(job_id, False, str(exc))
                    log("  -> ERROR: %s" % exc)
        except urllib.error.URLError as exc:
            log("No se pudo contactar a Odoo (%s); reintentando..." % exc)
        except Exception as exc:
            log("Error inesperado: %s" % exc)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

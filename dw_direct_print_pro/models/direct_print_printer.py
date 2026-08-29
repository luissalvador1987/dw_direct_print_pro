# -*- coding: utf-8 -*-
import base64
import os
import socket
import subprocess
import tempfile

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import win32print
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

SUMATRA_CANDIDATE_PATHS = [
    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
]


class DirectPrintPrinter(models.Model):
    _name = 'direct.print.printer'
    _description = 'Impresora (Direct Print Pro)'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    connection_type = fields.Selection([
        ('network', 'Red / Wi-Fi (IP directa)'),
        ('server_local', 'Conectada a este servidor'),
        ('agent', 'Conectada a una estación (agente local)'),
    ], string="Tipo de conexión", required=True, default='network')

    host = fields.Char(string="Dirección IP",
                        help="IP de la impresora en la red (Wi-Fi o Ethernet). Se le manda el trabajo "
                             "directo al puerto RAW/JetDirect (9100 por defecto), el estándar que soporta "
                             "prácticamente cualquier impresora de red.")
    port = fields.Integer(string="Puerto", default=9100)

    os_printer_name = fields.Char(
        string="Nombre de la impresora en este servidor",
        help="El nombre exacto tal como aparece en Windows (Dispositivos e impresoras). Cubre impresoras "
             "USB y también Bluetooth, siempre que ya estén emparejadas con esta computadora.")

    agent_id = fields.Many2one('direct.print.agent', string="Agente / estación")
    agent_printer_name = fields.Char(
        string="Nombre de la impresora en esa estación",
        help="El nombre exacto de la impresora tal como aparece instalada en la computadora del agente.")

    is_label_printer = fields.Boolean(
        string="Es impresora de etiquetas/recibos (ESC-POS, ZPL...)",
        help="Actívalo para impresoras térmicas que reciben comandos crudos en vez de un PDF. Estas se "
             "imprimen siempre de forma 100% directa, sin depender de ningún visor de PDF.")

    job_ids = fields.One2many('direct.print.job', 'printer_id', string="Trabajos")
    job_count = fields.Integer(compute='_compute_job_count')

    default_for_picking_type_ids = fields.Many2many(
        'stock.picking.type', string="Impresora por defecto de etiquetas para",
        help="Al imprimir la etiqueta de envío de una entrega de este tipo de operación, se usa esta "
             "impresora automáticamente, sin preguntar nada.")
    is_default_invoice_printer = fields.Boolean(string="Impresora por defecto para facturas")

    @api.depends('job_ids')
    def _compute_job_count(self):
        for p in self:
            p.job_count = len(p.job_ids)

    @api.constrains('connection_type', 'host', 'os_printer_name', 'agent_id', 'agent_printer_name')
    def _check_connection_fields(self):
        for p in self:
            if p.connection_type == 'network' and not p.host:
                raise UserError(_("Falta la dirección IP de la impresora de red '%s'.") % p.name)
            if p.connection_type == 'server_local' and not p.os_printer_name:
                raise UserError(_("Falta el nombre de la impresora en este servidor para '%s'.") % p.name)
            if p.connection_type == 'agent' and not (p.agent_id and p.agent_printer_name):
                raise UserError(_(
                    "Falta el agente y/o el nombre de la impresora en la estación para '%s'.") % p.name)

    @api.constrains('is_default_invoice_printer')
    def _check_single_default_invoice_printer(self):
        dupes = self.search([('is_default_invoice_printer', '=', True)])
        if len(dupes) > 1:
            raise UserError(_("Solo puede haber una impresora por defecto para facturas a la vez."))

    def action_open_jobs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Trabajos de impresión', 'res_model': 'direct.print.job',
            'view_mode': 'list,form', 'domain': [('printer_id', '=', self.id)],
        }

    def action_test_print(self):
        self.ensure_one()
        if self.is_label_printer:
            content = (
                "*** PRUEBA DE IMPRESION ***\n"
                "Direct Print Pro\n"
                "Impresora: %s\n"
                "Si ves esto, la conexion funciona.\n\n\n\n" % self.name
            ).encode('utf-8', errors='replace')
            job = self.print_document(content, content_type='raw', filename='prueba.txt')
        else:
            report = self.env.ref('dw_direct_print_pro.action_report_test_page')
            pdf_content, _fmt = report.sudo()._render_qweb_pdf('dw_direct_print_pro.report_test_page', res_ids=self.ids)
            job = self.print_document(pdf_content, content_type='pdf', filename='prueba.pdf')
        if job.state == 'error':
            raise UserError(_("La prueba de impresión falló: %s") % (job.error_message or _("error desconocido")))
        return True

    # ------------------------------------------------------------------
    # Motor de impresión
    # ------------------------------------------------------------------
    def print_document(self, content, content_type='pdf', filename=None, res_model=None, res_id=None,
                        report_id=None):
        self.ensure_one()
        if not self.active:
            raise UserError(_("La impresora '%s' está desactivada.") % self.name)
        job = self.env['direct.print.job'].sudo().create({
            'printer_id': self.id, 'content_type': content_type,
            'content': base64.b64encode(content) if content else False, 'content_filename': filename,
            'res_model': res_model, 'res_id': res_id, 'report_id': report_id and report_id.id,
            'user_id': self.env.user.id,
        })
        self._dispatch(job)
        return job

    def _dispatch(self, job):
        self.ensure_one()
        try:
            if self.connection_type == 'network':
                self._print_network(job)
            elif self.connection_type == 'server_local':
                self._print_server_local(job)
            elif self.connection_type == 'agent':
                self._print_agent(job)
            else:
                raise UserError(_("Tipo de conexión desconocido."))
        except Exception as exc:
            job.sudo().write({'state': 'error', 'error_message': str(exc)})

    def _print_network(self, job):
        self.ensure_one()
        if not self.host:
            raise UserError(_("La impresora '%s' no tiene una dirección IP configurada.") % self.name)
        data = job.content_bytes()
        with socket.create_connection((self.host, self.port or 9100), timeout=10) as sock:
            sock.sendall(data)
        job.sudo().write({'state': 'printed', 'sent_date': fields.Datetime.now()})

    def _print_server_local(self, job):
        self.ensure_one()
        if not HAS_WIN32:
            raise UserError(_(
                "Este servidor no tiene pywin32 instalado, así que no puede imprimir en impresoras "
                "locales/USB/Bluetooth propias. Instala pywin32 o usa una impresora de red."))
        data = job.content_bytes()
        if job.content_type == 'raw':
            self._win32_send_raw(self.os_printer_name, data)
        else:
            self._print_pdf_windows(self.os_printer_name, data)
        job.sudo().write({'state': 'printed', 'sent_date': fields.Datetime.now()})

    def _print_agent(self, job):
        # El agente local hace polling de trabajos 'sent' y los imprime él mismo en su impresora
        # (ver controllers/direct_print_agent_controller.py); acá solo lo dejamos listo para recoger.
        job.sudo().write({'state': 'sent', 'sent_date': fields.Datetime.now()})

    @staticmethod
    def _win32_send_raw(printer_name, data, doc_name="Direct Print Pro"):
        h_printer = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(h_printer, 1, (doc_name, None, "RAW"))
            try:
                win32print.StartPagePrinter(h_printer)
                win32print.WritePrinter(h_printer, data)
                win32print.EndPagePrinter(h_printer)
            finally:
                win32print.EndDocPrinter(h_printer)
        finally:
            win32print.ClosePrinter(h_printer)

    def _find_sumatra(self):
        custom = self.env['ir.config_parameter'].sudo().get_param('dw_direct_print_pro.sumatra_path')
        for candidate in ([custom] if custom else []) + SUMATRA_CANDIDATE_PATHS:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _print_pdf_windows(self, printer_name, pdf_bytes):
        sumatra = self._find_sumatra()
        if not sumatra:
            raise UserError(_(
                "Para imprimir un PDF directo en una impresora local hace falta SumatraPDF (gratis, un "
                "programa liviano de ~10MB hecho justo para esto): "
                "https://www.sumatrapdfreader.org/download-free-pdf-viewer — instálalo y vuelve a "
                "intentar. Las impresoras marcadas como 'de etiquetas/recibos' no necesitan esto."))
        fd, tmp_path = tempfile.mkstemp(suffix='.pdf')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(pdf_bytes)
            result = subprocess.run(
                [sumatra, '-print-to', printer_name, '-silent', '-exit-when-done', tmp_path],
                timeout=60, capture_output=True)
            if result.returncode != 0:
                raise UserError(_("SumatraPDF terminó con error (%(code)s): %(err)s") % {
                    'code': result.returncode,
                    'err': (result.stderr or b'').decode(errors='replace') or _("sin detalle"),
                })
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

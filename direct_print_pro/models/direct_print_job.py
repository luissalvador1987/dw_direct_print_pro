# -*- coding: utf-8 -*-
import base64
from datetime import timedelta

from odoo import api, fields, models, _

STUCK_AFTER_MINUTES = 30


class DirectPrintJob(models.Model):
    _name = 'direct.print.job'
    _description = 'Trabajo de Impresión Directa'
    _order = 'id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')
    printer_id = fields.Many2one('direct.print.printer', string="Impresora", required=True, ondelete='cascade')
    connection_type = fields.Selection(related='printer_id.connection_type', store=True)

    state = fields.Selection([
        ('draft', 'Pendiente'), ('sent', 'Enviado'), ('printed', 'Impreso'), ('error', 'Error'),
    ], string="Estado", default='draft', required=True)
    error_message = fields.Text(string="Error")

    content_type = fields.Selection([('pdf', 'PDF'), ('raw', 'Datos crudos')], default='pdf', required=True)
    content = fields.Binary(string="Contenido", attachment=True)
    content_filename = fields.Char(string="Nombre de archivo")

    report_id = fields.Many2one('ir.actions.report', string="Reporte de origen")
    res_model = fields.Char(string="Modelo de origen")
    res_id = fields.Integer(string="Registro de origen")

    user_id = fields.Many2one('res.users', string="Solicitado por", default=lambda self: self.env.user)
    sent_date = fields.Datetime(string="Enviado el")

    @api.depends('printer_id', 'report_id', 'create_date', 'state')
    def _compute_display_name(self):
        for job in self:
            job.display_name = "%s — %s (%s)" % (
                job.printer_id.name or '?', job.report_id.name or job.content_filename or 'Documento',
                dict(job._fields['state'].selection).get(job.state))

    def content_bytes(self):
        self.ensure_one()
        if not self.content:
            return b''
        return base64.b64decode(self.content)

    @api.model
    def _cron_mark_stuck_jobs_as_error(self):
        """Un trabajo 'enviado' a un agente que nunca confirma (estación apagada, agente cerrado...)
        se quedaría 'Enviado' para siempre. Después de un rato razonable, se marca como error para
        que no parezca que sigue en curso."""
        limit = fields.Datetime.now() - timedelta(minutes=STUCK_AFTER_MINUTES)
        stuck = self.search([('state', '=', 'sent'), ('create_date', '<', limit)])
        stuck.write({
            'state': 'error',
            'error_message': _("El agente de la estación no confirmó este trabajo a tiempo "
                                "(¿está apagado o sin conexión?)."),
        })

    def action_view_source_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            'type': 'ir.actions.act_window', 'res_model': self.res_model,
            'view_mode': 'form', 'res_id': self.res_id,
        }

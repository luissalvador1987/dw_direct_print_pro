# -*- coding: utf-8 -*-
import ast

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DirectPrintWizard(models.TransientModel):
    _name = 'direct.print.wizard'
    _description = 'Imprimir Directo'

    res_model = fields.Char(string="Modelo", required=True)
    res_ids = fields.Char(string="Registros (ids)", required=True, default='[]')
    record_count = fields.Integer(compute='_compute_record_count')

    report_id = fields.Many2one('ir.actions.report', string="Reporte", required=True,
                                 domain="[('model', '=', res_model)]")
    printer_id = fields.Many2one('direct.print.printer', string="Impresora",
                                  domain="[('active', '=', True)]")
    mode = fields.Selection([
        ('direct', 'Imprimir directo a una impresora'),
        ('browser', 'Vista previa / diálogo del navegador (sin instalar nada)'),
    ], default='direct', required=True)

    @api.depends('res_ids')
    def _compute_record_count(self):
        for wiz in self:
            wiz.record_count = len(wiz._get_ids())

    def _get_ids(self):
        self.ensure_one()
        try:
            ids = ast.literal_eval(self.res_ids or '[]')
        except (ValueError, SyntaxError):
            ids = []
        if isinstance(ids, int):
            ids = [ids]
        return list(ids)

    @api.onchange('mode')
    def _onchange_mode(self):
        if self.mode == 'browser':
            self.printer_id = False

    def action_print(self):
        self.ensure_one()
        ids = self._get_ids()
        if not ids:
            raise UserError(_("No hay ningún registro para imprimir."))
        if not self.report_id:
            raise UserError(_("Elige qué reporte quieres imprimir."))

        if self.mode == 'browser':
            records = self.env[self.res_model].browse(ids)
            return self.report_id.report_action(records)

        if not self.printer_id:
            raise UserError(_("Elige una impresora, o usa la opción de vista previa del navegador."))

        pdf_content, _fmt = self.report_id.sudo()._render_qweb_pdf(self.report_id.id, res_ids=ids)
        job = self.printer_id.print_document(
            pdf_content, content_type='pdf', filename='%s.pdf' % (self.report_id.name or 'documento'),
            res_model=self.res_model, res_id=ids[0], report_id=self.report_id,
        )
        if job.state == 'error':
            raise UserError(_("No se pudo imprimir: %s") % (job.error_message or _("error desconocido")))
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _("Enviado a imprimir"),
                'message': _("'%(report)s' se envió a '%(printer)s'.") % {
                    'report': self.report_id.name, 'printer': self.printer_id.name},
                'type': 'success', 'sticky': False,
            },
        }

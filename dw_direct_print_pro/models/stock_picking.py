# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_print_shipping_label_direct(self):
        self.ensure_one()
        printer = self.env['direct.print.printer'].search([
            ('default_for_picking_type_ids', 'in', self.picking_type_id.id),
        ], limit=1)
        report = self.env.ref('stock.action_report_delivery', raise_if_not_found=False)
        if not printer or not report:
            return self._open_direct_print_wizard(report)
        pdf_content, _fmt = report.sudo()._render_qweb_pdf('stock.action_report_delivery', res_ids=self.ids)
        job = printer.print_document(
            pdf_content, content_type='pdf', filename='%s.pdf' % (self.name or 'Etiqueta'),
            res_model=self._name, res_id=self.id, report_id=report,
        )
        if job.state == 'error':
            raise UserError(_("No se pudo imprimir la etiqueta: %s") % (job.error_message or _("error desconocido")))
        return True

    def action_open_direct_print_wizard(self):
        self.ensure_one()
        report = self.env.ref('stock.action_report_delivery', raise_if_not_found=False)
        return self._open_direct_print_wizard(report)

    def _open_direct_print_wizard(self, report):
        return {
            'type': 'ir.actions.act_window', 'name': _("Imprimir etiqueta directo"),
            'res_model': 'direct.print.wizard', 'view_mode': 'form', 'target': 'new',
            'context': {
                'default_res_model': self._name, 'default_res_ids': str(self.ids),
                'default_report_id': report.id if report else False,
            },
        }

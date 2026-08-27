# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_print_invoice_direct(self):
        self.ensure_one()
        printer = self.env['direct.print.printer'].search([('is_default_invoice_printer', '=', True)], limit=1)
        if not printer:
            return self._open_direct_print_wizard()
        report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        if not report:
            raise UserError(_("No se encontró el reporte de factura estándar."))
        pdf_content, _fmt = report.sudo()._render_qweb_pdf('account.account_invoices', res_ids=self.ids)
        job = printer.print_document(
            pdf_content, content_type='pdf', filename='%s.pdf' % (self.name or 'Factura'),
            res_model=self._name, res_id=self.id, report_id=report,
        )
        if job.state == 'error':
            raise UserError(_("No se pudo imprimir la factura: %s") % (job.error_message or _("error desconocido")))
        return True

    def action_open_direct_print_wizard(self):
        self.ensure_one()
        return self._open_direct_print_wizard()

    def _open_direct_print_wizard(self):
        report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window', 'name': _("Imprimir factura directo"),
            'res_model': 'direct.print.wizard', 'view_mode': 'form', 'target': 'new',
            'context': {
                'default_res_model': self._name, 'default_res_ids': str(self.ids),
                'default_report_id': report.id if report else False,
            },
        }

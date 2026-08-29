# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models, _

ONLINE_THRESHOLD_SECONDS = 90


class DirectPrintAgent(models.Model):
    _name = 'direct.print.agent'
    _description = 'Agente de Impresión Local (Direct Print Pro)'
    _order = 'name'

    name = fields.Char(string="Nombre de la estación", required=True,
                        help="ej: PC Recepción, Tablet Almacén...")
    token = fields.Char(string="Token", required=True, copy=False, readonly=True,
                         default=lambda self: str(uuid.uuid4()))
    active = fields.Boolean(default=True)

    last_seen = fields.Datetime(string="Última conexión", readonly=True, copy=False)
    state = fields.Selection([('online', 'En línea'), ('offline', 'Desconectado')],
                              string="Estado", compute='_compute_state')

    printer_ids = fields.One2many('direct.print.printer', 'agent_id', string="Impresoras")
    printer_count = fields.Integer(compute='_compute_printer_count')

    setup_instructions = fields.Html(string="Cómo instalar el agente", compute='_compute_setup_instructions')

    @api.depends('last_seen')
    def _compute_state(self):
        now = fields.Datetime.now()
        for agent in self:
            agent.state = 'online' if (
                agent.last_seen and (now - agent.last_seen).total_seconds() < ONLINE_THRESHOLD_SECONDS
            ) else 'offline'

    @api.depends('printer_ids')
    def _compute_printer_count(self):
        for agent in self:
            agent.printer_count = len(agent.printer_ids)

    def _compute_setup_instructions(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for agent in self:
            agent.setup_instructions = _(
                "<p>En la computadora donde está la impresora:</p>"
                "<ol>"
                "<li>Copia el archivo <code>direct_print_agent.py</code> "
                "(carpeta <code>dw_direct_print_pro/agent/</code> del módulo, o descárgalo desde "
                "<code>%(url)s/direct_print/agent/download</code>).</li>"
                "<li>Edita, al inicio del archivo, <code>ODOO_URL</code> con <code>%(url)s</code> "
                "y <code>AGENT_TOKEN</code> con: <code>%(token)s</code></li>"
                "<li>Ejecútalo con Python 3: <code>python direct_print_agent.py</code> "
                "(necesita <code>pywin32</code> en Windows: <code>pip install pywin32</code>; "
                "en Linux/Mac usa el comando <code>lp</code> del sistema, ya viene instalado con CUPS).</li>"
                "<li>Déjalo corriendo (puedes agregar un acceso directo a la carpeta de Inicio de "
                "Windows para que arranque solo). Mientras corre, esta estación queda 'En línea' aquí.</li>"
                "</ol>"
            ) % {'url': base_url, 'token': agent.token}

    def action_regenerate_token(self):
        for agent in self:
            agent.token = str(uuid.uuid4())

    def action_open_printers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Impresoras', 'res_model': 'direct.print.printer',
            'view_mode': 'list,form', 'domain': [('agent_id', '=', self.id)],
            'context': {'default_agent_id': self.id, 'default_connection_type': 'agent'},
        }

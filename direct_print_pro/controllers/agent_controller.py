# -*- coding: utf-8 -*-
import json
import logging
import os

from odoo import fields, http
from odoo.http import request
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)


class DirectPrintAgentController(http.Controller):
    """API que consume el script del agente local (direct_print_pro/agent/direct_print_agent.py).

    No usa sesión de usuario de Odoo: el agente se autentica con un token propio por estación,
    igual de simple que un webhook. Por eso son rutas HTTP planas (no JSON-RPC): piden y devuelven
    JSON común y corriente, sin el sobre jsonrpc que exige type='json'.
    """

    def _json_response(self, data, status=200):
        body = json.dumps(data)
        return request.make_response(
            body, status=status, headers=[('Content-Type', 'application/json')])

    def _get_agent(self, token):
        if not token:
            return None
        return request.env['direct.print.agent'].sudo().search([('token', '=', token)], limit=1)

    @http.route('/direct_print/agent/download', type='http', auth='user', methods=['GET'], csrf=False)
    def download_agent_script(self, **kwargs):
        module_path = get_module_path('direct_print_pro')
        file_path = os.path.join(module_path, 'agent', 'direct_print_agent.py')
        with open(file_path, 'rb') as f:
            content = f.read()
        return request.make_response(content, headers=[
            ('Content-Type', 'text/x-python'),
            ('Content-Disposition', 'attachment; filename="direct_print_agent.py"'),
        ])

    @http.route('/direct_print/agent/poll', type='http', auth='public', methods=['POST'], csrf=False)
    def poll(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return self._json_response({'error': 'JSON inválido'}, status=400)

        agent = self._get_agent(payload.get('token'))
        if not agent:
            return self._json_response({'error': 'Token inválido'}, status=403)

        agent.sudo().write({'last_seen': fields.Datetime.now()})

        jobs = request.env['direct.print.job'].sudo().search([
            ('printer_id.agent_id', '=', agent.id), ('state', '=', 'sent'),
        ])
        result = []
        for job in jobs:
            result.append({
                'job_id': job.id,
                'printer_name': job.printer_id.agent_printer_name,
                'content_type': job.content_type,
                'content': (job.content or b'').decode('ascii') if job.content else '',
                'filename': job.content_filename or 'documento',
            })
        return self._json_response({'jobs': result})

    @http.route('/direct_print/agent/ack', type='http', auth='public', methods=['POST'], csrf=False)
    def ack(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return self._json_response({'error': 'JSON inválido'}, status=400)

        agent = self._get_agent(payload.get('token'))
        if not agent:
            return self._json_response({'error': 'Token inválido'}, status=403)

        job = request.env['direct.print.job'].sudo().search([
            ('id', '=', payload.get('job_id')), ('printer_id.agent_id', '=', agent.id),
        ], limit=1)
        if not job:
            return self._json_response({'error': 'Trabajo no encontrado'}, status=404)

        if payload.get('success'):
            job.write({'state': 'printed', 'sent_date': fields.Datetime.now()})
        else:
            job.write({'state': 'error', 'error_message': payload.get('error_message') or 'Error en el agente'})
        agent.sudo().write({'last_seen': fields.Datetime.now()})
        return self._json_response({'ok': True})

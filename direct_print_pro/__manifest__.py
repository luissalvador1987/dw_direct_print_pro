{
    'name': "Direct Print Pro",
    'summary': "Imprime cualquier documento de Odoo (reportes, facturas, etiquetas de envío) directo a "
               "impresoras de red, Wi-Fi o Bluetooth, sin descargar el PDF primero.",
    'description': """
Direct Print Pro
=================

Imprime cualquier reporte de Odoo directamente en una impresora, sin pasar
por "descargar el PDF y abrirlo a mano". Funciona en tres niveles, según
dónde esté la impresora:

1. **Impresoras de red / Wi-Fi** — se les manda el trabajo directo por IP
   (protocolo RAW/JetDirect, puerto 9100), desde el propio servidor de Odoo.
   Cero configuración en cada equipo: cualquiera que use Odoo puede
   imprimir ahí.
2. **Impresoras conectadas a este servidor** (USB o Bluetooth ya
   emparejada con esta PC) — se imprimen usando la cola de impresión de
   Windows, igual de directo.
3. **Impresoras conectadas a OTRA computadora/tablet de la red**
   (recepción, almacén, otra oficina) — un pequeño agente local (un script
   liviano, no un instalador pesado) corre en esa PC, recibe los trabajos
   de Odoo y los manda a la impresora que esa PC tiene instalada
   (incluyendo Bluetooth emparejada ahí). Así cada estación imprime en SU
   propia impresora sin que el servidor necesite verla directamente.

Además, para cualquier caso no cubierto (o como respaldo si una impresora
está desconectada), siempre queda disponible la opción de vista previa +
diálogo de impresión del navegador — tampoco descarga ningún archivo.

Incluye accesos directos de un clic para los casos de uso más comunes:

* **Facturas** — botón "Imprimir factura directo" en la factura.
* **Etiquetas de envío** — botón "Imprimir etiqueta directo" en la entrega,
  con impresora por defecto configurable por tipo de operación (ideal para
  impresoras térmicas de etiquetas dedicadas en el área de despacho).
* **Cualquier otro reporte** — un asistente genérico (modelo + reporte +
  impresora) disponible desde cualquier registro o desde el menú de la app.

Cada trabajo de impresión queda registrado (impresora, momento, éxito o
error) para poder revisar qué se imprimió y detectar impresoras con
problemas.

Nota: la "impresión directa" a una impresora Bluetooth o USB solo es
posible desde la computadora a la que esa impresora está físicamente
conectada o emparejada — ninguna aplicación web, de Odoo o de cualquier
otro proveedor, puede saltarse esa limitación del sistema operativo y el
navegador. Por eso el nivel 3 (agente local) existe: es la forma honesta
de lograr impresión directa en la impresora de OTRA computadora.
    """,
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'author': "Designweblp",
    'maintainer': "Designweblp",
    'website': "https://github.com/luissalvador1987/direct_print_pro",
    'support': "luissalvador1987@gmail.com",
    'license': 'OPL-1',
    'price': 100.0,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'depends': ['base', 'web', 'mail', 'account', 'stock', 'sale'],
    'data': [
        'security/direct_print_pro_groups.xml',
        'security/ir.model.access.csv',
        'wizards/direct_print_wizard_views.xml',
        'views/direct_print_printer_views.xml',
        'views/direct_print_agent_views.xml',
        'views/direct_print_job_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/direct_print_menus.xml',
        'data/direct_print_report_templates.xml',
        'data/direct_print_cron.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

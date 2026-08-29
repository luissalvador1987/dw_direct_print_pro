# Direct Print Pro — Odoo 18

Imprime cualquier documento de Odoo (reportes, facturas, etiquetas de envío) directo a impresoras de red, Wi-Fi o Bluetooth, sin descargar el PDF primero.

Ficha completa con capturas: [`static/description/index.html`](./dw_direct_print_pro/static/description/index.html)

> **Nombre técnico del módulo**: `dw_direct_print_pro` (antes `direct_print_pro` — se renombró porque ese
> nombre ya estaba tomado por otro publicador en la Apps Store de Odoo). El nombre visible en Odoo
> sigue siendo "Direct Print Pro".

## Tres niveles de impresión directa

1. **Impresoras de red / Wi-Fi** — trabajo enviado directo por IP (protocolo RAW/JetDirect, puerto 9100) desde el propio servidor de Odoo. Cero configuración en cada equipo.
2. **Impresoras conectadas a este servidor** (USB o Bluetooth ya emparejada) — se imprimen usando la cola de impresión de Windows.
3. **Impresoras conectadas a OTRA computadora/tablet de la red** (recepción, almacén, otra oficina) — un pequeño [agente local](./dw_direct_print_pro/agent/direct_print_agent.py) (script liviano, no un instalador pesado) recibe los trabajos de Odoo y los manda a la impresora de esa estación.

Para cualquier caso no cubierto (o como respaldo), siempre queda disponible la vista previa + diálogo de impresión del navegador.

## Accesos directos de un clic

- **Facturas** — botón "Imprimir factura directo" en la factura.
- **Etiquetas de envío** — botón "Imprimir etiqueta directo" en la entrega, con impresora por defecto configurable por tipo de operación.
- **Cualquier otro reporte** — asistente genérico (modelo + reporte + impresora) desde cualquier registro o desde el menú de la app.

Cada trabajo de impresión queda registrado (impresora, momento, éxito o error).

## Honestidad técnica

La impresión directa a una impresora Bluetooth o USB solo es posible desde la computadora a la que esa impresora está físicamente conectada o emparejada — ninguna aplicación web puede saltarse esa limitación del sistema operativo y el navegador. Por eso existe el agente local (nivel 3): es la forma honesta de lograrlo en la impresora de OTRA computadora.

## Requisitos

- Odoo **18.0** (Community o Enterprise).
- Aplicaciones estándar de Odoo: `account`, `stock`, `sale`.
- Para el agente local: Python 3 en la estación con la impresora, y en Windows el paquete `pywin32` (`pip install pywin32`); en Linux/Mac usa el comando `lp` de CUPS.

## Instalación

1. Copia la carpeta `dw_direct_print_pro` a tu carpeta de `addons` personalizada.
2. Reinicia el servidor de Odoo y actualiza la lista de aplicaciones.
3. Instala **Direct Print Pro** desde Aplicaciones.
4. Configura tus impresoras en **Direct Print Pro > Impresoras**.
5. Si necesitas imprimir en la impresora de otra computadora, crea un "Agente / Estación" en Odoo (genera un token) y corre `agent/direct_print_agent.py` en esa PC con `ODOO_URL` y `AGENT_TOKEN` completados.

## Licencia

[Odoo Proprietary License v1.0 (OPL-1)](./LICENSE). Requiere una licencia válida para su uso (ver [Odoo Apps](https://apps.odoo.com)).

## Soporte

luissalvador1987@gmail.com

# Automatización y auditoría de la Sucursal 01

Autor: ADONIS LLERENA
Curso: GESTION DE LA INFRAESTRUCTURA DE RED

## Descripción

Proyecto que configura la Sucursal 01 con Ansible y audita el resultado con Python.

## Función de cada herramienta

**Ansible** aplica y respalda la configuración:
- Crea las VLAN 10, 20 y 99 con sus nombres.
- Configura troncales (nativa 99, VLAN permitidas 10, 20, 99) y puertos de acceso con descripción.
- Configura las subinterfaces del router (router on a stick).
- Guarda la configuración y guarda los respaldos en `backups/`.
- Es idempotente: una segunda ejecución no produce cambios.

**Python** analiza la evidencia y determina el cumplimiento:
- Lee el diseño esperado desde `vars/diseno.yml`.
- Lee los respaldos generados por Ansible.
- Audita VLAN, puertos de acceso y troncales, e indica CUMPLE / NO CUMPLE y qué condición no coincide.
- No configura equipos ni abre sesiones SSH.

## Estructura

    ansible.cfg
    inventory/        inventario y variables de conexión
    vars/diseno.yml   diseño esperado (fuente de verdad)
    playbooks/        switches.yml, router.yml, respaldo_switches.yml
    backups/          respaldos por equipo
    audit/auditoria.py
    docs/             capturas y evidencias

## Preparación manual (bootstrap)

Antes de automatizar se dejó a mano lo mínimo para llegar por SSH: hostname,
usuario, claves RSA, IP de gestión (VLAN 99), ruta por defecto y subinterfaces
del router. Switch1 no se incluye en el inventario.

## Uso

    ansible-playbook playbooks/router.yml
    ansible-playbook playbooks/switches.yml
    ansible-playbook playbooks/respaldo_switches.yml
    python3 audit/auditoria.py

## Dependencias

ansible-core, cisco.ios, ansible.netcommon, paramiko, PyYAML.

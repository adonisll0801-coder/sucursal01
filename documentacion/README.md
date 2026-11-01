# Actividad: prototipos de Python aplicados a redes (Sucursal 01)

Autor: Adonis Llerena. Curso: Gestion de la Infraestructura de Red.
Repositorio: https://github.com/adonisll0801-coder/sucursal01

## Proposito y reglas

Cinco prototipos en Python construidos sobre la Sucursal 01 ya automatizada con Ansible.
Python analiza, organiza o produce informacion; Ansible consulta, configura y obtiene
evidencias de los equipos. Reglas que se respetan en todo el repositorio:

- Los programas Python no configuran equipos ni abren sesiones SSH.
- Cuando se necesita informacion de un equipo, Ansible la obtiene primero y la guarda
  como evidencia en texto, YAML o CSV dentro del repositorio.
- Cada programa informa que datos leyo, que condicion evaluo y cual fue el resultado.
- No hay contrasenas ni secretos en el repositorio: las credenciales viven en
  inventory/group_vars/sucursal01.yml (excluido por .gitignore) y las lineas "secret"
  de las configuraciones se guardan enmascaradas como <OCULTO>.

## Estructura

- python/ : validar_cambio.py, generar_sucursal_02.py, auditar_flota.py,
  validar_inventario.py y medir_conectividad.py.
- datos/ : sucursal_02_entrada.yml, ipam_sucursal_01.json e ipam_sucursal_01_prueba.json.
- variables/ : sucursal_02_generada.yml (generado por el Prototipo 2).
- evidencias/ : salidas de Ansible (ansible/, antes/, despues/) y resultados en CSV.
- playbooks/ : evidencias_flota.yml, captura_estado.yml, cambio_descripcion.yml y
  revertir_descripcion.yml, ademas de los de la Actividad 1.
- La etiqueta Git actividad1-sucursal01 marca el repositorio tal como se entrego la
  Actividad 1.

## Prototipo 1: validacion antes y despues de un cambio (validar_cambio.py)

- Proposito: demostrar que un cambio aprobado ocurrio y que lo critico no se altero.
- Entradas: evidencias/antes y evidencias/despues (VLAN, troncales, interfaces de gestion
  y rutas, obtenidas con captura_estado.yml), vars/diseno.yml y cambio_descripcion.yml.
- Cambio aplicado con Ansible: descripcion de SW-SUC-01-CORE Gi0/1, de "Acceso VLAN 10 PC1"
  a "Acceso VLAN 10 PC1 - cambio aprobado". Despues se revirtio con revertir_descripcion.yml.
- Salida: evidencias/validacion_cambio.csv y resumen en pantalla.
- Resultado: cambio aplicado correctamente y 12 de 12 elementos criticos sin cambios
  (VLAN 99, direcciones de gestion, troncales, rutas), 0 diferencias.
- Python y Ansible: Ansible captura el estado y aplica el cambio; Python compara y decide.

## Prototipo 2: datos para una nueva sede (generar_sucursal_02.py)

- Proposito: calcular el direccionamiento de la Sucursal 02 sin configurar ninguna sede real.
- Entrada: datos/sucursal_02_entrada.yml (bloque 10.20.0.0/23; VLAN 10 ADMINISTRACION con
  50 dispositivos, VLAN 20 OPERACION con 25 y VLAN 99 GESTION con 10).
- Salida: variables/sucursal_02_generada.yml y un resumen en pantalla.
- Resultado: VLAN 10 10.20.0.0/26 (gateway 10.20.0.1), VLAN 20 10.20.0.64/27
  (gateway 10.20.0.65) y VLAN 99 10.20.0.96/28 (gateway 10.20.0.97). Sin solapamiento;
  112 de 512 direcciones usadas.
- Python y Ansible: Python genera las variables y Ansible podra usarlas despues para
  configurar la sede.

## Prototipo 3: auditoria de una flota pequena (auditar_flota.py)

- Proposito: evaluar R-SUC-01, SW-SUC-01-CORE y SW-SUC-01-ACC1 como muestra de una flota.
- Entradas: salidas de evidencias_flota.yml (show version, show vlan brief, show interfaces
  trunk, show ip interface brief y configuracion) y vars/diseno.yml.
- Salida: evidencias/auditoria_flota.csv (equipo, condicion, resultado, evidencia, detalle).
- Resultado: 23 de 23 condiciones cumplen.
- Python y Ansible: Ansible recolecta las evidencias de solo lectura; Python las evalua.

## Prototipo 4: relacion de fuentes de informacion (validar_inventario.py)

- Proposito: cruzar el diseno YAML, el JSON que simula un IPAM, el inventario y las
  evidencias de los equipos.
- Entradas: vars/diseno.yml, datos/ipam_sucursal_01.json, inventory/hosts.yml y evidencias.
- Salida: evidencias/validacion_inventario.csv, con coincidencias, faltantes y diferencias.
- Resultado: 20 comparaciones, 20 coinciden. En la prueba con
  datos/ipam_sucursal_01_prueba.json (4 alteraciones intencionales) detecto 14
  coincidencias, 3 faltantes y 3 diferencias (red de la VLAN 10, gateway de la VLAN 20
  y direccion de gestion de ACC1).
- Python y Ansible: es la logica de integracion que se aplicaria al consultar APIs de IPAM,
  DNS o inventario; Ansible aporta la evidencia real de los equipos.

## Prototipo 5: conectividad de gestion (medir_conectividad.py)

- Proposito: medir y clasificar la calidad de la conexion de gestion.
- Entrada: destinos de inventory/hosts.yml; diez pruebas ICMP por destino.
- Salida: evidencias/mediciones_conectividad.csv (cada ejecucion agrega filas).
- Criterio: CUMPLE si no hay perdida y la latencia promedio es de 50 ms o menos.
- Resultado: R-SUC-01 4,98 ms, SW-SUC-01-CORE 19,61 ms y SW-SUC-01-ACC1 36,48 ms
  promedio, sin perdida: 3 de 3 cumplen.
- Limitacion: el criterio evalua solo el promedio y no detecta picos aislados
  (ACC1 llego a 79 ms de maximo).

## Como ejecutar

    python3 python/generar_sucursal_02.py
    python3 python/medir_conectividad.py
    ansible-playbook playbooks/evidencias_flota.yml 2>/dev/null
    python3 python/auditar_flota.py
    python3 python/validar_inventario.py
    ansible-playbook playbooks/captura_estado.yml -e fase=antes 2>/dev/null
    ansible-playbook playbooks/cambio_descripcion.yml 2>/dev/null
    ansible-playbook playbooks/captura_estado.yml -e fase=despues 2>/dev/null
    python3 python/validar_cambio.py

## Seguridad del repositorio

El repositorio es publico. Se encontraron contrasenas de laboratorio en el primer commit y
hashes de secretos en los respaldos de configuracion, y se limpio el historial en dos
etapas: primero se retiro el archivo con las contrasenas y despues se enmascararon las
lineas "secret". Las credenciales reales solo existen en el servidor de automatizacion.

## Conclusion tecnica

Ansible y Python se complementan: Ansible es la mano que consulta y cambia los equipos de
forma repetible y deja evidencia; Python es el criterio que lee esa evidencia, la compara
con el diseno y otras fuentes, y concluye si se cumple o no.

Para una organizacion con multiples sedes, Ansible aporta mas valor. Sin el no hay
configuracion consistente ni evidencia actualizada: el mismo playbook aplica el mismo
diseno en todas las sedes, es idempotente y deja trazabilidad, mientras que Python no puede
cambiar nada ni obtener datos por si solo. Python multiplica ese valor a escala, porque la
auditoria de flota, el cruce de fuentes y la validacion de cambios detectan desviaciones
que nadie revisaria equipo por equipo, pero depende de las evidencias que Ansible entrega.# Actividad: prototipos de Python aplicados a redes (Sucursal 01)

Autor: Adonis Llerena. Curso: Gestion de la Infraestructura de Red.
Repositorio: https://github.com/adonisll0801-coder/sucursal01

## Proposito y reglas

Cinco prototipos en Python construidos sobre la Sucursal 01 ya automatizada con Ansible.
Python analiza, organiza o produce informacion; Ansible consulta, configura y obtiene
evidencias de los equipos. Reglas que se respetan en todo el repositorio:

- Los programas Python no configuran equipos ni abren sesiones SSH.
- Cuando se necesita informacion de un equipo, Ansible la obtiene primero y la guarda
  como evidencia en texto, YAML o CSV dentro del repositorio.
- Cada programa informa que datos leyo, que condicion evaluo y cual fue el resultado.
- No hay contrasenas ni secretos en el repositorio: las credenciales viven en
  inventory/group_vars/sucursal01.yml (excluido por .gitignore) y las lineas "secret"
  de las configuraciones se guardan enmascaradas como <OCULTO>.

## Estructura

- python/ : validar_cambio.py, generar_sucursal_02.py, auditar_flota.py,
  validar_inventario.py y medir_conectividad.py.
- datos/ : sucursal_02_entrada.yml, ipam_sucursal_01.json e ipam_sucursal_01_prueba.json.
- variables/ : sucursal_02_generada.yml (generado por el Prototipo 2).
- evidencias/ : salidas de Ansible (ansible/, antes/, despues/) y resultados en CSV.
- playbooks/ : evidencias_flota.yml, captura_estado.yml, cambio_descripcion.yml y
  revertir_descripcion.yml, ademas de los de la Actividad 1.
- La etiqueta Git actividad1-sucursal01 marca el repositorio tal como se entrego la
  Actividad 1.

## Prototipo 1: validacion antes y despues de un cambio (validar_cambio.py)

- Proposito: demostrar que un cambio aprobado ocurrio y que lo critico no se altero.
- Entradas: evidencias/antes y evidencias/despues (VLAN, troncales, interfaces de gestion
  y rutas, obtenidas con captura_estado.yml), vars/diseno.yml y cambio_descripcion.yml.
- Cambio aplicado con Ansible: descripcion de SW-SUC-01-CORE Gi0/1, de "Acceso VLAN 10 PC1"
  a "Acceso VLAN 10 PC1 - cambio aprobado". Despues se revirtio con revertir_descripcion.yml.
- Salida: evidencias/validacion_cambio.csv y resumen en pantalla.
- Resultado: cambio aplicado correctamente y 12 de 12 elementos criticos sin cambios
  (VLAN 99, direcciones de gestion, troncales, rutas), 0 diferencias.
- Python y Ansible: Ansible captura el estado y aplica el cambio; Python compara y decide.

## Prototipo 2: datos para una nueva sede (generar_sucursal_02.py)

- Proposito: calcular el direccionamiento de la Sucursal 02 sin configurar ninguna sede real.
- Entrada: datos/sucursal_02_entrada.yml (bloque 10.20.0.0/23; VLAN 10 ADMINISTRACION con
  50 dispositivos, VLAN 20 OPERACION con 25 y VLAN 99 GESTION con 10).
- Salida: variables/sucursal_02_generada.yml y un resumen en pantalla.
- Resultado: VLAN 10 10.20.0.0/26 (gateway 10.20.0.1), VLAN 20 10.20.0.64/27
  (gateway 10.20.0.65) y VLAN 99 10.20.0.96/28 (gateway 10.20.0.97). Sin solapamiento;
  112 de 512 direcciones usadas.
- Python y Ansible: Python genera las variables y Ansible podra usarlas despues para
  configurar la sede.

## Prototipo 3: auditoria de una flota pequena (auditar_flota.py)

- Proposito: evaluar R-SUC-01, SW-SUC-01-CORE y SW-SUC-01-ACC1 como muestra de una flota.
- Entradas: salidas de evidencias_flota.yml (show version, show vlan brief, show interfaces
  trunk, show ip interface brief y configuracion) y vars/diseno.yml.
- Salida: evidencias/auditoria_flota.csv (equipo, condicion, resultado, evidencia, detalle).
- Resultado: 23 de 23 condiciones cumplen.
- Python y Ansible: Ansible recolecta las evidencias de solo lectura; Python las evalua.

## Prototipo 4: relacion de fuentes de informacion (validar_inventario.py)

- Proposito: cruzar el diseno YAML, el JSON que simula un IPAM, el inventario y las
  evidencias de los equipos.
- Entradas: vars/diseno.yml, datos/ipam_sucursal_01.json, inventory/hosts.yml y evidencias.
- Salida: evidencias/validacion_inventario.csv, con coincidencias, faltantes y diferencias.
- Resultado: 20 comparaciones, 20 coinciden. En la prueba con
  datos/ipam_sucursal_01_prueba.json (4 alteraciones intencionales) detecto 14
  coincidencias, 3 faltantes y 3 diferencias (red de la VLAN 10, gateway de la VLAN 20
  y direccion de gestion de ACC1).
- Python y Ansible: es la logica de integracion que se aplicaria al consultar APIs de IPAM,
  DNS o inventario; Ansible aporta la evidencia real de los equipos.

## Prototipo 5: conectividad de gestion (medir_conectividad.py)

- Proposito: medir y clasificar la calidad de la conexion de gestion.
- Entrada: destinos de inventory/hosts.yml; diez pruebas ICMP por destino.
- Salida: evidencias/mediciones_conectividad.csv (cada ejecucion agrega filas).
- Criterio: CUMPLE si no hay perdida y la latencia promedio es de 50 ms o menos.
- Resultado: R-SUC-01 4,98 ms, SW-SUC-01-CORE 19,61 ms y SW-SUC-01-ACC1 36,48 ms
  promedio, sin perdida: 3 de 3 cumplen.
- Limitacion: el criterio evalua solo el promedio y no detecta picos aislados
  (ACC1 llego a 79 ms de maximo).

## Como ejecutar

    python3 python/generar_sucursal_02.py
    python3 python/medir_conectividad.py
    ansible-playbook playbooks/evidencias_flota.yml 2>/dev/null
    python3 python/auditar_flota.py
    python3 python/validar_inventario.py
    ansible-playbook playbooks/captura_estado.yml -e fase=antes 2>/dev/null
    ansible-playbook playbooks/cambio_descripcion.yml 2>/dev/null
    ansible-playbook playbooks/captura_estado.yml -e fase=despues 2>/dev/null
    python3 python/validar_cambio.py

## Seguridad del repositorio

El repositorio es publico. Se encontraron contrasenas de laboratorio en el primer commit y
hashes de secretos en los respaldos de configuracion, y se limpio el historial en dos
etapas: primero se retiro el archivo con las contrasenas y despues se enmascararon las
lineas "secret". Las credenciales reales solo existen en el servidor de automatizacion.

## Conclusion tecnica

Ansible y Python se complementan: Ansible es la mano que consulta y cambia los equipos de
forma repetible y deja evidencia; Python es el criterio que lee esa evidencia, la compara
con el diseno y otras fuentes, y concluye si se cumple o no.

Para una organizacion con multiples sedes, Ansible aporta mas valor. Sin el no hay
configuracion consistente ni evidencia actualizada: el mismo playbook aplica el mismo
diseno en todas las sedes, es idempotente y deja trazabilidad, mientras que Python no puede
cambiar nada ni obtener datos por si solo. Python multiplica ese valor a escala, porque la
auditoria de flota, el cruce de fuentes y la validacion de cambios detectan desviaciones
que nadie revisaria equipo por equipo, pero depende de las evidencias que Ansible entrega.

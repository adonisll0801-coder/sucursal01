#!/usr/bin/env python3
"""Prototipo 1 - Validacion antes y despues de un cambio aprobado.

Compara evidencias/antes y evidencias/despues (obtenidas con Ansible) y el
cambio declarado en playbooks/cambio_descripcion.yml. No abre sesiones SSH ni
configura equipos.
"""
import csv
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(RAIZ / "audit"))
import auditoria as base  # lector de 'show vlan brief' de la Actividad 1

ANTES = RAIZ / "evidencias" / "antes"
DESPUES = RAIZ / "evidencias" / "despues"
PLAYBOOK = RAIZ / "playbooks" / "cambio_descripcion.yml"
DISENO = RAIZ / "vars" / "diseno.yml"
SALIDA = RAIZ / "evidencias" / "validacion_cambio.csv"
PATRON_DESC = re.compile(r"^(\S+)\s+(?:up|down|admin down|deleted)\s+(?:up|down)\s*(.*)$")

filas = []  # equipo, elemento, resultado, evidencia, detalle


def leer(carpeta, host, archivo):
    return (carpeta / host / archivo).read_text()


def norm(texto):
    return [" ".join(l.split()) for l in texto.splitlines() if l.strip()]


def registrar(host, elemento, archivo, difs):
    filas.append([host, elemento,
                  "SIN CAMBIOS" if not difs else "DIFERENCIA DETECTADA",
                  f"antes y despues: {host}/{archivo}", "; ".join(difs)])


def comparar_archivo(host, elemento, archivo, filtro=None):
    a = norm(leer(ANTES, host, archivo))
    d = norm(leer(DESPUES, host, archivo))
    if filtro:
        a = [l for l in a if filtro(l)]
        d = [l for l in d if filtro(l)]
    difs = []
    quitadas = [l for l in a if l not in d]
    nuevas = [l for l in d if l not in a]
    if quitadas:
        difs.append("antes: " + " / ".join(quitadas))
    if nuevas:
        difs.append("despues: " + " / ".join(nuevas))
    if not difs and a != d:
        difs.append("cambio en el orden de las lineas")
    if not a and not d:
        difs.append("el elemento no aparece en la evidencia")
    registrar(host, elemento, archivo, difs)


def comparar_vlans(host):
    a = base.leer_vlan_brief(ANTES / host / "vlan-brief.txt")
    d = base.leer_vlan_brief(DESPUES / host / "vlan-brief.txt")
    difs = []
    for vid in sorted(set(a) | set(d)):
        va, vd = a.get(vid), d.get(vid)
        if va is None or vd is None:
            donde = "despues" if va is None else "antes"
            difs.append(f"VLAN {vid} solo existe {donde}")
            continue
        for campo in ("name", "status"):
            if va[campo] != vd[campo]:
                difs.append(f"VLAN {vid} {campo}: {va[campo]} -> {vd[campo]}")
        if va["ports"] != vd["ports"]:
            difs.append(f"VLAN {vid} puertos: {sorted(va['ports'])} -> {sorted(vd['ports'])}")
    registrar(host, "VLAN (nombre, estado y puertos)", "vlan-brief.txt", difs)


def descripciones(texto):
    datos = {}
    for linea in texto.splitlines():
        m = PATRON_DESC.match(linea.strip())
        if m:
            datos[m.group(1)] = m.group(2).strip()
    return datos


def validar_cambio_solicitado(host, puerto, nueva):
    corto = base.corto(puerto)
    a = descripciones(leer(ANTES, host, "interfaces-description.txt")).get(corto)
    d = descripciones(leer(DESPUES, host, "interfaces-description.txt")).get(corto)
    difs = []
    if a is None or d is None:
        difs.append(f"{corto} no aparece en la evidencia")
    else:
        if a == nueva:
            difs.append("la descripcion nueva ya estaba antes del cambio")
        if d != nueva:
            difs.append(f"esperada '{nueva}', encontrada '{d}'")
    detalle = "; ".join(difs) if difs else f"'{a}' -> '{d}'"
    filas.append([host, f"Cambio solicitado: descripcion de {corto}",
                  "CAMBIO APLICADO" if not difs else "DIFERENCIA DETECTADA",
                  f"antes y despues: {host}/interfaces-description.txt", detalle])
    return not difs


def comparar_descripciones(host, excluir):
    a = descripciones(leer(ANTES, host, "interfaces-description.txt"))
    d = descripciones(leer(DESPUES, host, "interfaces-description.txt"))
    difs = []
    for p in sorted(set(a) | set(d)):
        if p != excluir and a.get(p) != d.get(p):
            difs.append(f"{p}: '{a.get(p)}' -> '{d.get(p)}'")
    registrar(host, "Descripciones de los demas puertos", "interfaces-description.txt", difs)


def main():
    play = yaml.safe_load(PLAYBOOK.read_text())[0]
    host_cambio = play["hosts"]
    puerto = play["vars"]["puerto"]
    nueva = play["vars"]["descripcion_nueva"]
    diseno = yaml.safe_load(DISENO.read_text())
    router = diseno["router"]["hostname"]
    switches = list(diseno["switches"])
    try:
        cambio_ok = validar_cambio_solicitado(host_cambio, puerto, nueva)
        comparar_archivo(router, "Gestion: Gi0/2 y Gi0/0.99 (IP, estado)", "ip-interface-brief.txt",
                         lambda l: l.startswith(("GigabitEthernet0/2 ", "GigabitEthernet0/0.99 ")))
        comparar_archivo(router, "Rutas del router (show ip route)", "ip-route.txt")
        for h in switches:
            comparar_vlans(h)
            comparar_archivo(h, "Troncales (modo, nativa y VLAN permitidas)", "interfaces-trunk.txt")
            comparar_archivo(h, "Gestion Vlan99 (IP y estado)", "ip-interface-brief.txt",
                             lambda l: l.startswith("Vlan99 "))
            comparar_archivo(h, "Ruta por defecto configurada", "rutas-config.txt")
            comparar_descripciones(h, base.corto(puerto) if h == host_cambio else None)
    except FileNotFoundError as e:
        print(f"Falta evidencia: {e.filename}")
        sys.exit(2)

    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["equipo", "elemento", "resultado", "evidencia", "detalle"])
        w.writerows(filas)

    print("=" * 78)
    print("PROTOTIPO 1 - VALIDACION ANTES Y DESPUES DE UN CAMBIO")
    print("=" * 78)
    print("DATOS LEIDOS")
    print("  Antes    : evidencias/antes/<equipo>/")
    print("  Despues  : evidencias/despues/<equipo>/")
    print(f"  Cambio   : playbooks/cambio_descripcion.yml ({host_cambio}, {puerto})")
    print("CONDICION EVALUADA")
    print("  1) La descripcion del puerto cambio al valor aprobado.")
    print("  2) VLAN, troncales, gestion, rutas y las demas descripciones no cambiaron.")
    print("RESULTADO")
    print(f"  {'EQUIPO':<15} {'ELEMENTO':<46} RESULTADO")
    for e, el, r, _, _ in filas:
        print(f"  {e:<15} {el:<46} {r}")
    criticos = filas[1:]
    sin = sum(1 for f in criticos if f[2] == "SIN CAMBIOS")
    difs = [f for f in filas if f[2] == "DIFERENCIA DETECTADA"]
    if difs:
        print("DIFERENCIAS DETECTADAS")
        for e, el, _, _, d in difs:
            print(f"  {e} | {el}\n      {d}")
    print("=" * 78)
    print(f"  Cambio aplicado correctamente  : {'SI' if cambio_ok else 'NO'}")
    print(f"  Elementos criticos sin cambios : {sin} de {len(criticos)}")
    print(f"  Diferencias detectadas         : {len(difs)}")
    print("  Registro guardado en: evidencias/validacion_cambio.csv")
    sys.exit(0 if not difs else 1)


if __name__ == "__main__":
    main()

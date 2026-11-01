#!/usr/bin/env python3
"""Prototipo 3 - Auditoria de la flota (R-SUC-01, SW-SUC-01-CORE, SW-SUC-01-ACC1).

Lee vars/diseno.yml, inventory/hosts.yml y las evidencias que Ansible dejo en
evidencias/ansible/<equipo>/. No abre sesiones SSH ni configura equipos.
"""
import csv
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(RAIZ / "audit"))
import auditoria as base  # lectores de la auditoria de la Actividad 1

DISENO = RAIZ / "vars" / "diseno.yml"
INVENTARIO = RAIZ / "inventory" / "hosts.yml"
EVID = RAIZ / "evidencias" / "ansible"
SALIDA = RAIZ / "evidencias" / "auditoria_flota.csv"

filas = []  # equipo, condicion, resultado, evidencia, detalle


def leer(host, archivo):
    return (EVID / host / archivo).read_text()


def registrar(host, condicion, archivo, difs):
    filas.append([host, condicion, "CUMPLE" if not difs else "NO CUMPLE",
                  f"evidencias/ansible/{host}/{archivo}", "; ".join(difs)])


def ips_gestion(nodo, salida):
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if isinstance(valor, dict) and "ansible_host" in valor:
                salida[clave] = valor["ansible_host"]
            else:
                ips_gestion(valor, salida)


def leer_ip_brief(texto):
    datos = {}
    for linea in texto.splitlines():
        p = linea.split()
        if len(p) >= 6 and p[0] != "Interface":
            datos[p[0]] = (p[1], " ".join(p[4:-1]), p[-1])
    return datos


def leer_trunk(texto):
    datos, seccion = {}, None
    for linea in texto.splitlines():
        if linea.startswith("Port"):
            if "Mode" in linea:
                seccion = "modo"
            elif "allowed on trunk" in linea:
                seccion = "permitidas"
            else:
                seccion = None
            continue
        p = linea.split()
        if not p or seccion is None:
            continue
        d = datos.setdefault(p[0], {})
        if seccion == "modo":
            d["estado"], d["nativa"] = p[3], int(p[4])
        else:
            d["permitidas"] = base.expandir_vlans(p[1])
    return datos


def chequear_version(host):
    texto = leer(host, "show-version.txt")
    difs = []
    if not re.search(rf"^{re.escape(host)} uptime is", texto, re.M):
        difs.append(f"show version no identifica al equipo {host}")
    registrar(host, "show version corresponde al equipo", "show-version.txt", difs)


def chequear_ip(host, interfaz, ip_esperada, condicion):
    dato = leer_ip_brief(leer(host, "ip-interface-brief.txt")).get(interfaz)
    difs = []
    if dato is None:
        difs.append(f"{interfaz} no aparece en show ip interface brief")
    else:
        ip, estado, protocolo = dato
        if ip != ip_esperada:
            difs.append(f"IP esperada {ip_esperada}, encontrada {ip}")
        if estado != "up" or protocolo != "up":
            difs.append(f"estado esperado up/up, encontrado {estado}/{protocolo}")
    registrar(host, condicion, "ip-interface-brief.txt", difs)


def auditar_router(host, router, ip_gestion):
    chequear_version(host)
    ib = leer_ip_brief(leer(host, "ip-interface-brief.txt"))
    hallada = next((n for n, v in ib.items() if v[0] == ip_gestion), None)
    difs = []
    if hallada is None:
        difs.append(f"ninguna interfaz tiene la IP {ip_gestion}")
    elif ib[hallada][1] != "up" or ib[hallada][2] != "up":
        difs.append(f"{hallada} no esta up/up")
    registrar(host, f"Gestion {ip_gestion} presente y up/up", "ip-interface-brief.txt", difs)
    config = leer(host, "running-config.txt")
    for s in router["subinterfaces"]:
        nombre = f"{router['trunk_interface']}.{s['vlan']}"
        chequear_ip(host, nombre, s["ip"], f"Subinterfaz VLAN {s['vlan']} IP {s['ip']} up/up")
        esperado = f"encapsulation dot1Q {s['vlan']}" + (" native" if s.get("native") else "")
        bloque = re.search(rf"^interface {re.escape(nombre)}\n(.*?)^!", config, re.M | re.S)
        difs = []
        if not bloque or esperado not in bloque.group(1):
            difs.append(f"falta '{esperado}' en {nombre}")
        registrar(host, f"Encapsulacion dot1Q VLAN {s['vlan']} (subinterfaz)", "running-config.txt", difs)


def auditar_switch(host, datos, vlans_diseno):
    chequear_version(host)
    chequear_ip(host, "Vlan99", datos["mgmt_ip"], f"Gestion Vlan99 {datos['mgmt_ip']} up/up")
    vlans = base.leer_vlan_brief(EVID / host / "vlan-brief.txt")
    for v in vlans_diseno:
        difs = []
        real = vlans.get(v["id"])
        if real is None:
            difs.append(f"la VLAN {v['id']} no existe")
        else:
            if real["name"] != v["name"]:
                difs.append(f"nombre esperado '{v['name']}', encontrado '{real['name']}'")
            if real["status"] != "active":
                difs.append(f"estado esperado 'active', encontrado '{real['status']}'")
        registrar(host, f"VLAN {v['id']} {v['name']} existe y activa", "vlan-brief.txt", difs)
    troncales = leer_trunk(leer(host, "interfaces-trunk.txt"))
    for t in datos["trunks"]:
        puerto = base.corto(t["interface"])
        x = troncales.get(puerto)
        difs = []
        if x is None:
            difs.append(f"{puerto} no aparece en show interfaces trunk")
        else:
            if x.get("estado") != "trunking":
                difs.append(f"estado esperado 'trunking', encontrado '{x.get('estado')}'")
            if x.get("nativa") != t["native_vlan"]:
                difs.append(f"nativa esperada {t['native_vlan']}, encontrada {x.get('nativa')}")
            esperadas = set(t["allowed_vlans"])
            if x.get("permitidas") != esperadas:
                difs.append(f"permitidas esperadas {sorted(esperadas)}, encontradas {sorted(x.get('permitidas') or [])}")
        permitidas = ",".join(str(n) for n in t["allowed_vlans"])
        registrar(host, f"Troncal {puerto}: nativa {t['native_vlan']}, permitidas {permitidas}",
                  "interfaces-trunk.txt", difs)
    interfaces = base.leer_interfaces(EVID / host / "running-config.txt")
    difs = []
    for p in datos["access_ports"]:
        i = interfaces.get(p["interface"])
        if i is None:
            difs.append(f"{p['interface']} no aparece en la configuracion")
            continue
        if i["mode"] != "access":
            difs.append(f"{p['interface']}: modo esperado 'access', encontrado '{i['mode']}'")
        if i["access_vlan"] != p["vlan"]:
            difs.append(f"{p['interface']}: VLAN esperada {p['vlan']}, encontrada {i['access_vlan']}")
        if i["description"] != p["description"]:
            difs.append(f"{p['interface']}: descripcion esperada '{p['description']}', encontrada '{i['description']}'")
    registrar(host, f"{len(datos['access_ports'])} puertos de acceso segun diseno", "running-config.txt", difs)


def main():
    diseno = yaml.safe_load(DISENO.read_text())
    ips = {}
    ips_gestion(yaml.safe_load(INVENTARIO.read_text()), ips)
    router = diseno["router"]
    print("=" * 70)
    print("PROTOTIPO 3 - AUDITORIA DE LA FLOTA")
    print("=" * 70)
    print("DATOS LEIDOS")
    print("  Diseno      : vars/diseno.yml")
    print("  Inventario  : inventory/hosts.yml")
    print("  Evidencias  : evidencias/ansible/<equipo>/ (show version, vlan brief,")
    print("                interfaces trunk, ip interface brief, running-config)")
    print("CONDICION EVALUADA")
    print("  Cada equipo cumple si su evidencia coincide con el diseno y con el")
    print("  inventario; si no, se indica la diferencia encontrada.")
    equipos = [router["hostname"]] + list(diseno["switches"])
    for host in equipos:
        try:
            if host == router["hostname"]:
                auditar_router(host, router, ips[host])
            else:
                auditar_switch(host, diseno["switches"][host], diseno["vlans"])
        except FileNotFoundError as e:
            nombre = Path(e.filename).name
            registrar(host, "Evidencia disponible", nombre, [f"falta el archivo {nombre}"])
    SALIDA.parent.mkdir(exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["equipo", "condicion", "resultado", "evidencia", "detalle"])
        w.writerows(filas)
    print("RESULTADO")
    print(f"  {'EQUIPO':<15} {'CONDICION':<42} {'RESULTADO':<10} EVIDENCIA")
    for e, c, r, ev, _ in filas:
        print(f"  {e:<15} {c:<42} {r:<10} {Path(ev).name}")
    fallos = [f for f in filas if f[2] != "CUMPLE"]
    if fallos:
        print("DIFERENCIAS DETECTADAS")
        for e, c, _, _, d in fallos:
            print(f"  {e} | {c}\n      {d}")
    ok = len(filas) - len(fallos)
    print("=" * 70)
    print(f"  {ok} de {len(filas)} condiciones cumplen en {len(equipos)} equipos")
    print("  Registro guardado en: evidencias/auditoria_flota.csv")
    sys.exit(0 if not fallos else 1)


if __name__ == "__main__":
    main()

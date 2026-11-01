#!/usr/bin/env python3
"""Prototipo 4 - Relacion de fuentes de informacion.

Cruza vars/diseno.yml, inventory/hosts.yml, datos/ipam_sucursal_01.json (simula
una API de IPAM) y las evidencias que Ansible dejo en evidencias/ansible/.
No abre sesiones SSH ni configura equipos.
Uso: python3 python/validar_inventario.py [ruta_json_alternativo]
"""
import csv
import ipaddress
import json
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(RAIZ / "audit"))
import auditoria as base  # lector de 'show vlan brief' de la Actividad 1

DISENO = RAIZ / "vars" / "diseno.yml"
INVENTARIO = RAIZ / "inventory" / "hosts.yml"
IPAM = RAIZ / "datos" / "ipam_sucursal_01.json"
EVID = RAIZ / "evidencias" / "ansible"

resultados = []  # principal, atributo, estado, fuentes, detalle


def comparar(principal, atributo, fuentes):
    presentes = {k: v for k, v in fuentes.items() if v is not None}
    ausentes = [k for k, v in fuentes.items() if v is None]
    if len(set(presentes.values())) > 1:
        estado = "DIFERENCIA"
        detalle = " | ".join(f"{k}: {v}" for k, v in presentes.items())
        if ausentes:
            detalle += " | sin dato en: " + ", ".join(ausentes)
    elif ausentes:
        estado = "FALTANTE"
        detalle = "sin dato en: " + ", ".join(ausentes)
    else:
        estado = "COINCIDE"
        detalle = ""
    resultados.append((principal, atributo, estado, ", ".join(fuentes), detalle))


def leer_texto(host, archivo):
    ruta = EVID / host / archivo
    return ruta.read_text() if ruta.exists() else None


def recorrer(nodo, grupo, salida):
    for host, datos in (nodo.get("hosts") or {}).items():
        salida[host] = {"ip": datos.get("ansible_host"), "grupo": grupo}
    for nombre, sub in (nodo.get("children") or {}).items():
        recorrer(sub, nombre, salida)


def ips_config(texto):
    datos, actual = {}, None
    for linea in (texto or "").splitlines():
        if linea.startswith("interface "):
            actual = linea.split(None, 1)[1].strip()
        elif actual and linea.strip().startswith("ip address "):
            p = linea.split()
            try:
                datos[actual] = ipaddress.ip_interface(f"{p[2]}/{p[3]}")
            except (IndexError, ValueError):
                pass
    return datos


def ip_brief(texto):
    datos = {}
    for linea in (texto or "").splitlines():
        p = linea.split()
        if len(p) >= 6 and p[0] != "Interface":
            datos[p[0]] = p[1]
    return datos


def ruta_defecto(texto):
    m = re.search(r"^ip route 0\.0\.0\.0 0\.0\.0\.0 (\S+)", texto or "", re.M)
    return m.group(1) if m else None


def rel(ruta):
    try:
        return str(ruta.relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def main():
    ruta_ipam = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else IPAM
    salida_csv = RAIZ / "evidencias" / (
        "validacion_inventario.csv" if ruta_ipam == IPAM else "validacion_inventario_prueba.csv")
    diseno = yaml.safe_load(DISENO.read_text())
    inv = {}
    recorrer(yaml.safe_load(INVENTARIO.read_text())["all"], "all", inv)
    ipam = json.loads(ruta_ipam.read_text())
    router = diseno["router"]
    rhost = router["hostname"]
    switches = diseno["switches"]
    cfg_router = ips_config(leer_texto(rhost, "running-config.txt"))
    vlans_yaml = {v["id"]: v for v in diseno["vlans"]}
    vlans_ipam = {v["id"]: v for v in ipam.get("vlans", [])}
    briefs = {}
    for h in switches:
        ruta = EVID / h / "vlan-brief.txt"
        briefs[h] = base.leer_vlan_brief(ruta) if ruta.exists() else {}

    for vid in sorted(set(vlans_yaml) | set(vlans_ipam)):
        y, i = vlans_yaml.get(vid, {}), vlans_ipam.get(vid, {})
        s = cfg_router.get(f"{router['trunk_interface']}.{vid}")
        nombre = {"YAML": y.get("name"), "IPAM": i.get("nombre")}
        for h in switches:
            nombre[f"vlan-brief {h.split('-')[-1]}"] = briefs[h].get(vid, {}).get("name")
        comparar(f"VLAN {vid}", "nombre", nombre)
        comparar(f"VLAN {vid}", "red", {
            "YAML": y.get("network"), "IPAM": i.get("red"),
            "config router": str(s.network) if s else None})
        comparar(f"VLAN {vid}", "gateway", {
            "YAML": y.get("gateway"), "IPAM": i.get("gateway"),
            "config router": str(s.ip) if s else None})

    ipam_eq = {e.get("nombre"): e for e in ipam.get("equipos", [])}
    orden = [rhost] + list(switches)
    for n in list(ipam_eq) + list(inv):
        if n not in orden:
            orden.append(n)
    for n in orden:
        txt = leer_texto(n, "show-version.txt")
        en_version = n if txt and re.search(rf"^{re.escape(n)} uptime is", txt, re.M) else None
        comparar(n, "nombre", {
            "IPAM": n if n in ipam_eq else None,
            "inventario": n if n in inv else None,
            "YAML": n if n == rhost or n in switches else None,
            "show version": en_version})
        f = ipam_eq.get(n, {}).get("funcion")
        g_ipam = None if f is None else ("routers" if f == "router" else
                                          "switches" if f.startswith("switch") else f)
        g_yaml = "routers" if n == rhost else ("switches" if n in switches else None)
        g_ver = None if not txt else ("switches" if "vios_l2" in txt else "routers")
        comparar(n, "funcion", {
            "IPAM": g_ipam, "inventario": inv.get(n, {}).get("grupo"),
            "YAML": g_yaml, "show version": g_ver})
        ip_inv = inv.get(n, {}).get("ip")
        ev = ip_brief(leer_texto(n, "ip-interface-brief.txt"))
        fuentes = {"IPAM": ipam_eq.get(n, {}).get("ip_gestion"), "inventario": ip_inv}
        if n in switches:
            fuentes["YAML"] = switches[n]["mgmt_ip"]
            fuentes["ip interface brief"] = ev.get("Vlan99")
        else:
            fuentes["ip interface brief"] = ip_inv if ip_inv in ev.values() else None
        comparar(n, "ip de gestion", fuentes)
        if n in switches:
            comparar(n, "gateway de gestion", {
                "YAML": switches[n]["mgmt_gateway"],
                "IPAM gateway VLAN 99": vlans_ipam.get(99, {}).get("gateway"),
                "config switch": ruta_defecto(leer_texto(n, "running-config.txt"))})

    with open(salida_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["elemento", "atributo", "estado", "fuentes_comparadas", "detalle"])
        w.writerows(resultados)

    print("=" * 70)
    print("PROTOTIPO 4 - RELACION DE FUENTES DE INFORMACION")
    print("=" * 70)
    print("DATOS LEIDOS")
    print("  Diseno      : vars/diseno.yml")
    print("  Inventario  : inventory/hosts.yml")
    print(f"  IPAM (JSON) : {rel(ruta_ipam)}")
    print("  Evidencias  : evidencias/ansible/<equipo>/ (show version, vlan brief,")
    print("                ip interface brief, running-config)")
    print("CONDICION EVALUADA")
    print("  Cada VLAN (nombre, red, gateway) y cada equipo (nombre, funcion, IP de")
    print("  gestion) debe ser igual en todas las fuentes donde aparece.")
    grupos = {"COINCIDE": [], "FALTANTE": [], "DIFERENCIA": []}
    for r in resultados:
        grupos[r[2]].append(r)
    print("RESULTADO")
    agrupado = {}
    for p, a, *_ in grupos["COINCIDE"]:
        agrupado.setdefault(p, []).append(a)
    print(f"  COINCIDENCIAS ({len(grupos['COINCIDE'])})")
    for p, atributos in agrupado.items():
        print(f"    {p:<16}: {', '.join(atributos)}")
    for titulo, clave in (("FALTANTES", "FALTANTE"), ("DIFERENCIAS", "DIFERENCIA")):
        print(f"  {titulo} ({len(grupos[clave])})")
        for p, a, _, _, d in grupos[clave]:
            print(f"    {p} / {a}\n        {d}")
    print("=" * 70)
    print(f"  {len(resultados)} comparaciones: {len(grupos['COINCIDE'])} coinciden, "
          f"{len(grupos['FALTANTE'])} faltantes, {len(grupos['DIFERENCIA'])} diferencias")
    print(f"  Registro guardado en: {rel(salida_csv)}")
    sys.exit(0 if len(grupos["COINCIDE"]) == len(resultados) else 1)


if __name__ == "__main__":
    main()

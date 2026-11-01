#!/usr/bin/env python3
"""Auditoria de la Sucursal 01.

Lee el diseno esperado (vars/diseno.yml) y la evidencia obtenida con Ansible
(backups/<equipo>/). No abre sesiones SSH ni configura equipos.
"""
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
DISENO = RAIZ / "vars" / "diseno.yml"
BACKUPS = RAIZ / "backups"

resultados = []  # (elemento, cumple, [diferencias])


def corto(nombre):
    """GigabitEthernet0/1 -> Gi0/1"""
    return nombre.replace("GigabitEthernet", "Gi")


def expandir_vlans(texto):
    vlans = set()
    for parte in texto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            a, b = parte.split("-")
            vlans.update(range(int(a), int(b) + 1))
        else:
            vlans.add(int(parte))
    return vlans


def leer_vlan_brief(ruta):
    vlans, actual = {}, None
    for linea in ruta.read_text().splitlines():
        m = re.match(r"^(\d+)\s+(\S+)\s+(\S+)\s*(.*)$", linea)
        if m:
            actual = int(m.group(1))
            puertos = {p.strip() for p in m.group(4).split(",") if p.strip()}
            vlans[actual] = {"name": m.group(2), "status": m.group(3), "ports": puertos}
        elif actual is not None and linea.startswith(" ") and linea.strip():
            vlans[actual]["ports"].update(p.strip() for p in linea.split(",") if p.strip())
    return vlans


def leer_interfaces(ruta):
    interfaces, actual = {}, None
    for linea in ruta.read_text().splitlines():
        if linea.startswith("interface "):
            actual = linea.split(None, 1)[1].strip()
            interfaces[actual] = {"description": None, "mode": None,
                                  "access_vlan": 1, "native": 1, "allowed": None}
        elif linea.startswith(" ") and actual:
            t = linea.strip()
            i = interfaces[actual]
            if t.startswith("description "):
                i["description"] = t[len("description "):].strip()
            elif t.startswith("switchport mode "):
                i["mode"] = t.split()[-1]
            elif t.startswith("switchport access vlan "):
                i["access_vlan"] = int(t.split()[-1])
            elif t.startswith("switchport trunk native vlan "):
                i["native"] = int(t.split()[-1])
            elif t.startswith("switchport trunk allowed vlan add "):
                i["allowed"] = (i["allowed"] or set()) | expandir_vlans(t.split()[-1])
            elif t.startswith("switchport trunk allowed vlan "):
                i["allowed"] = expandir_vlans(t.split()[-1])
        elif linea.startswith("!"):
            actual = None
    return interfaces


def registrar(elemento, difs):
    resultados.append((elemento, not difs, difs))
    estado = "CUMPLE" if not difs else "NO CUMPLE"
    print(f"  [{estado}] {elemento}")
    for d in difs:
        print(f"      - {d}")


def auditar_vlans(host, esperadas, reales):
    print(f"\n  VLAN")
    for v in esperadas:
        difs = []
        r = reales.get(v["id"])
        if r is None:
            difs.append(f"la VLAN {v['id']} no existe")
        else:
            if r["name"] != v["name"]:
                difs.append(f"nombre esperado '{v['name']}', encontrado '{r['name']}'")
            if r["status"] != "active":
                difs.append(f"estado esperado 'active', encontrado '{r['status']}'")
        registrar(f"{host} VLAN {v['id']} ({v['name']})", difs)


def auditar_acceso(host, puertos, interfaces, vlans):
    print(f"\n  Puertos de acceso")
    for p in puertos:
        difs = []
        i = interfaces.get(p["interface"])
        if i is None:
            difs.append("la interfaz no aparece en la running-config")
        else:
            if i["mode"] != "access":
                difs.append(f"modo esperado 'access', encontrado '{i['mode']}'")
            if i["access_vlan"] != p["vlan"]:
                difs.append(f"VLAN (config) esperada {p['vlan']}, encontrada {i['access_vlan']}")
            if i["description"] != p["description"]:
                difs.append(f"descripcion esperada '{p['description']}', encontrada '{i['description']}'")
        en_vlan = vlans.get(p["vlan"], {}).get("ports", set())
        if corto(p["interface"]) not in en_vlan:
            difs.append(f"{corto(p['interface'])} no aparece en la VLAN {p['vlan']} de 'show vlan brief'")
        registrar(f"{host} {p['interface']} acceso VLAN {p['vlan']}", difs)


def auditar_troncales(host, troncales, interfaces):
    print(f"\n  Troncales")
    for t in troncales:
        difs = []
        i = interfaces.get(t["interface"])
        if i is None:
            difs.append("la interfaz no aparece en la running-config")
        else:
            if i["mode"] != "trunk":
                difs.append(f"modo esperado 'trunk', encontrado '{i['mode']}'")
            if i["native"] != t["native_vlan"]:
                difs.append(f"VLAN nativa esperada {t['native_vlan']}, encontrada {i['native']}")
            esp = set(t["allowed_vlans"])
            if i["allowed"] is not None and i["allowed"] != esp:
                difs.append(f"VLAN permitidas esperadas {sorted(esp)}, encontradas {sorted(i['allowed'])}")
            if i["allowed"] is None:
                difs.append(f"VLAN permitidas esperadas {sorted(esp)}, encontradas: todas (sin restriccion)")
            if i["description"] != t["description"]:
                difs.append(f"descripcion esperada '{t['description']}', encontrada '{i['description']}'")
        registrar(f"{host} {t['interface']} troncal", difs)


def main():
    diseno = yaml.safe_load(DISENO.read_text())
    print("AUDITORIA DE CUMPLIMIENTO - SUCURSAL 01")
    print("=" * 50)
    for host, datos in diseno["switches"].items():
        carpeta = BACKUPS / host
        try:
            vlans = leer_vlan_brief(carpeta / "vlan-brief.txt")
            interfaces = leer_interfaces(carpeta / "running-config.txt")
        except FileNotFoundError as e:
            print(f"\n{host}: falta evidencia ({e.filename})")
            registrar(f"{host} evidencia", ["faltan archivos de respaldo"])
            continue
        print(f"\n{host}")
        print("-" * 50)
        auditar_vlans(host, diseno["vlans"], vlans)
        auditar_acceso(host, datos["access_ports"], interfaces, vlans)
        auditar_troncales(host, datos["trunks"], interfaces)

    total = len(resultados)
    ok = sum(1 for _, c, _ in resultados if c)
    print("\n" + "=" * 50)
    print(f"RESUMEN: {ok} de {total} elementos cumplen, {total - ok} no cumplen")
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()

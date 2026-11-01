#!/usr/bin/env python3
"""Prototipo 2: genera datos de red para la Sucursal 02.

Lee datos/sucursal_02_entrada.yml, calcula las subredes sin solapamiento
y escribe variables/sucursal_02_generada.yml. No configura ningun equipo.
"""
import ipaddress
import math
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "datos" / "sucursal_02_entrada.yml"
SALIDA = RAIZ / "variables" / "sucursal_02_generada.yml"


def prefijo_para(dispositivos):
    # dispositivos + 1 gateway + direccion de red + broadcast
    total = dispositivos + 1 + 2
    return 32 - math.ceil(math.log2(total))


def main():
    if not ENTRADA.exists():
        print(f"ERROR: no existe {ENTRADA}")
        return 1

    with open(ENTRADA) as f:
        entrada = yaml.safe_load(f)

    bloque = ipaddress.ip_network(entrada["bloque_disponible"])
    vlans = entrada["vlans"]

    print("=" * 62)
    print("PROTOTIPO 2 - GENERACION DE DATOS PARA UNA NUEVA SEDE")
    print("=" * 62)
    print("DATOS LEIDOS")
    print(f"  Archivo : {ENTRADA.relative_to(RAIZ)}")
    print(f"  Sede    : {entrada['sucursal']}")
    print(f"  Bloque  : {bloque} ({bloque.num_addresses} direcciones)")
    for v in vlans:
        print(f"  VLAN {v['id']:<3} {v['nombre']:<15} {v['dispositivos']} dispositivos")
    print("CONDICION EVALUADA")
    print("  Cada subred soporta los dispositivos + gateway, queda dentro")
    print("  del bloque y no se solapa con otra.")

    # Se asigna de la subred mas grande a la mas pequena
    orden = sorted(vlans, key=lambda v: v["dispositivos"], reverse=True)
    cursor = int(bloque.network_address)
    plan = []
    for v in orden:
        prefijo = prefijo_para(v["dispositivos"])
        tamano = 2 ** (32 - prefijo)
        if cursor % tamano:
            cursor += tamano - (cursor % tamano)
        red = ipaddress.ip_network((cursor, prefijo))
        if not red.subnet_of(bloque):
            print(f"ERROR: la VLAN {v['id']} no cabe en {bloque}")
            return 1
        plan.append({
            "vlan": v["id"],
            "nombre": v["nombre"],
            "red": str(red),
            "mascara": str(red.netmask),
            "prefijo": prefijo,
            "gateway": str(red.network_address + 1),
            "hosts_previstos": v["dispositivos"],
            "hosts_utilizables": red.num_addresses - 2,
        })
        cursor += tamano

    redes = [ipaddress.ip_network(p["red"]) for p in plan]
    for i in range(len(redes)):
        for j in range(i + 1, len(redes)):
            if redes[i].overlaps(redes[j]):
                print(f"ERROR: {redes[i]} se solapa con {redes[j]}")
                return 1

    plan.sort(key=lambda p: p["vlan"])
    SALIDA.parent.mkdir(exist_ok=True)
    salida = {
        "sucursal": entrada["sucursal"],
        "bloque": str(bloque),
        "vlans": plan,
    }
    with open(SALIDA, "w") as f:
        yaml.safe_dump(salida, f, sort_keys=False, allow_unicode=True)

    usadas = sum(ipaddress.ip_network(p["red"]).num_addresses for p in plan)
    print("RESULTADO")
    print(f"  {'VLAN':<5}{'NOMBRE':<16}{'RED':<16}{'MASCARA':<18}{'GATEWAY':<12}{'HOSTS':<6}")
    for p in plan:
        print(f"  {p['vlan']:<5}{p['nombre']:<16}{p['red']:<16}{p['mascara']:<18}"
              f"{p['gateway']:<12}{p['hosts_previstos']:<6}")
    print(f"  Direcciones usadas: {usadas} de {bloque.num_addresses}"
          f" (libres: {bloque.num_addresses - usadas})")
    print("  Sin solapamiento: CUMPLE")
    print(f"  Archivo generado: {SALIDA.relative_to(RAIZ)}")
    print("  Nota: este prototipo no configura ninguna sede real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

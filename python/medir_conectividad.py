#!/usr/bin/env python3
"""Prototipo 5: medicion de conectividad de gestion.

Lee los destinos de inventory/hosts.yml, ejecuta 10 pruebas ICMP hacia cada
uno y guarda los resultados en evidencias/mediciones_conectividad.csv.
No se conecta por SSH ni configura ningun equipo.
"""
import csv
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
INVENTARIO = RAIZ / "inventory" / "hosts.yml"
SALIDA = RAIZ / "evidencias" / "mediciones_conectividad.csv"
PAQUETES = 10
UMBRAL_MS = 50.0
CAMPOS = ["fecha", "equipo", "destino", "enviados", "recibidos",
          "perdida_pct", "min_ms", "prom_ms", "max_ms", "resultado"]


def buscar_hosts(nodo, encontrados):
    """Recorre el inventario y recoge cada host con su ansible_host."""
    if isinstance(nodo, dict):
        for nombre, datos in (nodo.get("hosts") or {}).items():
            ip = (datos or {}).get("ansible_host")
            if ip:
                encontrados[nombre] = ip
        for valor in nodo.values():
            buscar_hosts(valor, encontrados)


def medir(ip):
    entorno = dict(os.environ, LC_ALL="C")
    proc = subprocess.run(
        ["ping", "-c", str(PAQUETES), "-W", "2", ip],
        capture_output=True, text=True, env=entorno)
    texto = proc.stdout
    enviados = recibidos = 0
    perdida = 100.0
    minimo = promedio = maximo = None
    m = re.search(r"(\d+) packets transmitted, (\d+) received.*?([\d.]+)% packet loss", texto)
    if m:
        enviados, recibidos, perdida = int(m.group(1)), int(m.group(2)), float(m.group(3))
    m = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)/", texto)
    if m:
        minimo, promedio, maximo = (float(m.group(i)) for i in (1, 2, 3))
    return enviados, recibidos, perdida, minimo, promedio, maximo


def main():
    if not INVENTARIO.exists():
        print(f"ERROR: no existe {INVENTARIO}")
        return 1
    with open(INVENTARIO) as f:
        hosts = {}
        buscar_hosts(yaml.safe_load(f), hosts)
    if not hosts:
        print("ERROR: no se encontraron hosts con ansible_host en el inventario")
        return 1

    print("=" * 66)
    print("PROTOTIPO 5 - MEDICION DE CONECTIVIDAD DE GESTION")
    print("=" * 66)
    print("DATOS LEIDOS")
    print(f"  Inventario : {INVENTARIO.relative_to(RAIZ)}")
    for nombre, ip in hosts.items():
        print(f"  Destino    : {nombre} ({ip})")
    print("CONDICION EVALUADA")
    print(f"  {PAQUETES} pruebas ICMP por destino. CUMPLE si no hay perdida y la")
    print(f"  latencia promedio es <= {UMBRAL_MS:.0f} ms; en otro caso, NO CUMPLE.")
    print("MEDICIONES (puede tardar unos segundos)")

    SALIDA.parent.mkdir(exist_ok=True)
    nuevo = not SALIDA.exists()
    filas = []
    for nombre, ip in hosts.items():
        enviados, recibidos, perdida, mn, pr, mx = medir(ip)
        cumple = perdida == 0 and pr is not None and pr <= UMBRAL_MS
        filas.append({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "equipo": nombre, "destino": ip,
            "enviados": enviados, "recibidos": recibidos,
            "perdida_pct": perdida,
            "min_ms": "" if mn is None else mn,
            "prom_ms": "" if pr is None else pr,
            "max_ms": "" if mx is None else mx,
            "resultado": "CUMPLE" if cumple else "NO CUMPLE",
        })

    with open(SALIDA, "a", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            escritor.writeheader()
        escritor.writerows(filas)

    print("RESULTADO")
    print(f"  {'EQUIPO':<17}{'DESTINO':<14}{'ENV':<5}{'REC':<5}{'PERD%':<7}"
          f"{'MIN':<8}{'PROM':<8}{'MAX':<8}{'RESULTADO'}")
    for r in filas:
        print(f"  {r['equipo']:<17}{r['destino']:<14}{r['enviados']:<5}"
              f"{r['recibidos']:<5}{r['perdida_pct']:<7}{str(r['min_ms']):<8}"
              f"{str(r['prom_ms']):<8}{str(r['max_ms']):<8}{r['resultado']}")
    ok = sum(1 for r in filas if r["resultado"] == "CUMPLE")
    print(f"  Destinos que cumplen: {ok} de {len(filas)}")
    print(f"  Registro guardado en: {SALIDA.relative_to(RAIZ)}")
    return 0 if ok == len(filas) else 1


if __name__ == "__main__":
    sys.exit(main())

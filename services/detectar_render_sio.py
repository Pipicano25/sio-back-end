#!/usr/bin/env python3
"""Comprueba servicios web SIO alojados en Render sin dependencias externas.

IMPORTANTE: Las URLs son candidatas derivadas de los nombres de servicio.
Confirma cada URL desde Render > servicio > URL pública.
Ejecutar el script envía peticiones que pueden despertar instancias gratuitas.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import csv
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Sustituye cada URL si la dirección pública real es diferente.
SERVICIOS = {
    "sio-product-catalog-dev": "https://sio-product-catalog-dev.onrender.com",
    "sio-purchase-dev": "https://sio-purchase-dev.onrender.com",
    "sio-product-inventory-query-dev": "https://sio-product-inventory-query-dev.onrender.com",
    "sio-inventory-dev": "https://sio-inventory-dev.onrender.com",
    "sio-commercial-relationship-dev": "https://sio-commercial-relationship-dev.onrender.com",
    "sio-geography-dev": "https://sio-geography-dev.onrender.com",
    "sio-business-reporting-dev": "https://sio-business-reporting-dev.onrender.com",
    "sio-payment-reference-dev": "https://sio-payment-reference-dev.onrender.com",
    "sio-party-identity-dev": "https://sio-party-identity-dev.onrender.com",
    "sio-sales-dev": "https://sio-sales-dev.onrender.com",
    "sio-audit-dev": "https://sio-audit-dev.onrender.com",
}

UMBRAL_DESPERTAR_SEGUNDOS = 10.0
TIMEOUT_PRIMERA = 95
TIMEOUT_SEGUNDA = 25

@dataclass
class Comprobacion:
    codigo: str
    segundos: float
    error: str = ""


def solicitar(url: str, timeout: int) -> Comprobacion:
    inicio = time.perf_counter()
    request = Request(url, headers={"User-Agent": "SIO-Render-Diagnostic/1.0", "Accept": "*/*"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return Comprobacion(str(response.status), time.perf_counter() - inicio)
    except HTTPError as error:
        # Un 401, 403, 404 o 405 también demuestra que hubo respuesta HTTP.
        return Comprobacion(str(error.code), time.perf_counter() - inicio)
    except (URLError, TimeoutError, OSError) as error:
        return Comprobacion("—", time.perf_counter() - inicio, str(error))


def evaluar(nombre: str, url: str) -> dict:
    primera = solicitar(url, TIMEOUT_PRIMERA)
    if primera.error:
        segunda = solicitar(url, TIMEOUT_SEGUNDA)
    elif primera.segundos >= UMBRAL_DESPERTAR_SEGUNDOS:
        segunda = solicitar(url, TIMEOUT_SEGUNDA)
    else:
        segunda = None

    if primera.error and (segunda is None or segunda.error):
        estado = "NO RESPONDE"
    elif primera.error and segunda and not segunda.error:
        estado = "POSIBLE DESPERTAR / FALLO TRANSITORIO"
    elif segunda and not segunda.error and primera.segundos >= UMBRAL_DESPERTAR_SEGUNDOS and segunda.segundos < primera.segundos / 2:
        estado = "POSIBLEMENTE DORMIDO (DESPERTÓ)"
    elif primera.segundos >= UMBRAL_DESPERTAR_SEGUNDOS:
        estado = "LENTO / REVISAR"
    elif primera.codigo.startswith("5"):
        estado = "ERROR HTTP DEL SERVICIO"
    else:
        estado = "RESPONDE"

    return {
        "servicio": nombre,
        "estado": estado,
        "http_1": primera.codigo,
        "tiempo_1_s": round(primera.segundos, 2),
        "http_2": segunda.codigo if segunda else "—",
        "tiempo_2_s": round(segunda.segundos, 2) if segunda else "—",
        "url": url,
        "error": primera.error or (segunda.error if segunda else ""),
    }


def main() -> None:
    print(f"Comprobando {len(SERVICIOS)} servicios SIO DEV en paralelo...", flush=True)
    print("NOTA: Estas peticiones pueden despertar servicios gratuitos de Render.\n")
    resultados = []
    with ThreadPoolExecutor(max_workers=len(SERVICIOS)) as executor:
        pendientes = {executor.submit(evaluar, nombre, url): nombre for nombre, url in SERVICIOS.items()}
        for tarea in as_completed(pendientes):
            resultado = tarea.result()
            resultados.append(resultado)
            print(f"[{len(resultados):02d}/{len(SERVICIOS)}] {resultado['servicio']}: {resultado['estado']}", flush=True)

    resultados.sort(key=lambda item: item["servicio"])
    print("\nRESULTADOS\n")
    print(f"{'SERVICIO':36} {'ESTADO':39} {'HTTP':>5} {'1a (s)':>8} {'2a (s)':>8}")
    print("-" * 103)
    for item in resultados:
        print(f"{item['servicio']:36} {item['estado']:39} {item['http_1']:>5} {str(item['tiempo_1_s']):>8} {str(item['tiempo_2_s']):>8}")
    with open("resultado_render_sio.csv", "w", newline="", encoding="utf-8-sig") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=list(resultados[0].keys()))
        writer.writeheader()
        writer.writerows(resultados)
    print("\nArchivo generado: resultado_render_sio.csv")
    print("Una respuesta HTTP (incluso 401/404) no demuestra que la API esté saludable.")
    print("Una respuesta lenta tampoco demuestra por sí sola que estuviera dormida.")


if __name__ == "__main__":
    main()

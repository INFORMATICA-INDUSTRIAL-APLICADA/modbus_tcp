"""
Solución Completa para el Profesor - SCADA Supervisión Planta Fotovoltaica con Batería
Asignatura: Informática Industrial Aplicada - Grado en Ingeniería Eléctrica
"""

import json
import os
import time
from pyModbusTCP.client import ModbusClient

STATE_MAP = {
    0: "PARADO (NOCHE)",
    1: "EN ESPERA (STANDBY - RED DISPONIBLE)",
    2: "GENERANDO (CONECTADO A RED)",
    99: "¡¡¡ ALARMA - PROTECCIÓN DISPARADA !!!"
}

ALARM_MAP = {
    0: "Sin alarmas",
    101: "Sobretensión en red AC (> 253 V)",
    102: "Sobretemperatura en puente inversor IGBTs (> 85 °C)"
}


def cargar_configuracion(ruta: str = "config.json") -> dict:
    """Lee y parsea el archivo de configuración local del SCADA."""
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def limpiar_pantalla():
    """Limpia el terminal según el sistema operativo."""
    os.system('cls' if os.name == 'nt' else 'clear')


def mostrar_menu() -> str:
    """Muestra las opciones del centro de control."""
    print("\n" + "=" * 55)
    print("      SCADA - CENTRO DE CONTROL PLANTA FOTOVOLTAICA")
    print("=" * 55)
    print("  [1] Conectar Inversor a Red (Dar Marcha)")
    print("  [2] Desconectar Inversor de Red (Paro a Espera)")
    print("  [3] Ajustar Consigna de Límite de Inyección (0 - 100%)")
    print("  [4] Resetear / Reconocer Alarmas")
    print("  [5] Monitorizar Planta en Tiempo Real")
    print("  [0] Salir")
    print("=" * 55)
    return input("Selecciona una opción [0-5]: ").strip()


def leer_y_mostrar_bateria(client: ModbusClient, config: dict):
    """
    FASE 2 (SOLUCIÓN): Lee el SoC y la potencia de la batería y los imprime.
    """
    tags = config["tags"]
    addr_soc = tags["bateria_soc"]
    addr_power = tags["bateria_potencia"]

    soc_regs = client.read_input_registers(addr_soc, 1)
    pot_regs = client.read_input_registers(addr_power, 1)

    if soc_regs is not None and pot_regs is not None:
        soc = soc_regs[0]
        pot_bat = pot_regs[0]
        print(f"  [BATERÍA BESS]       : Carga (SoC): {soc}% | Potencia: {pot_bat} W")


def monitorizar_planta(client: ModbusClient, config: dict):
    """Bucle de supervisión continua de las variables de planta."""
    tags = config["tags"]
    refresco = config.get("scada", {}).get("tiempo_refresco_segundos", 1.0)

    limpiar_pantalla()
    print("Iniciando monitorización en tiempo real... (Presiona Ctrl+C para volver al menú)")
    time.sleep(1)

    try:
        while True:
            limpiar_pantalla()

            # Lectura de los registros de estado y medidas
            regs_estado = client.read_input_registers(tags["estado_inversor"], 5)
            regs_holding = client.read_holding_registers(tags["limite_potencia"], 1)

            if regs_estado is None or regs_holding is None:
                print("\n[ERROR] No se pudo comunicar con el inversor. Reintentando...")
                time.sleep(2)
                continue

            estado = regs_estado[0]
            vdc = regs_estado[1]
            pac = regs_estado[2]
            frec_hz = regs_estado[3] / 10.0
            alarma = regs_estado[4]
            limite_pct = regs_holding[0]

            texto_estado = STATE_MAP.get(estado, f"Desconocido ({estado})")
            texto_alarma = ALARM_MAP.get(alarma, f"Código {alarma}")

            print("=" * 60)
            print("         PANEL DE TELEMETRÍA EN TIEMPO REAL")
            print("=" * 60)
            print(f"  ESTADO INVERSOR      : {texto_estado}")
            print(f"  ALARMA ACTIVA        : {texto_alarma}")
            print("-" * 60)
            print(f"  Tensión DC (Paneles) : {vdc:>5} V")
            print(f"  Potencia Activa AC   : {pac:>5} W ({pac / 1000.0:.2f} kW)")
            print(f"  Frecuencia de Red    : {frec_hz:>5.1f} Hz")
            print(f"  Límite de Inyección  : {limite_pct:>5} %")
            print("-" * 60)

            # FASE 2: Lectura de batería
            leer_y_mostrar_bateria(client, config)

            print("=" * 60)
            print("  (Presiona Ctrl+C para regresar al Menú Principal)")
            time.sleep(refresco)

    except KeyboardInterrupt:
        print("\nRegresando al menú...")
        time.sleep(1)


def main():
    config = cargar_configuracion()
    host = config["conexion_inversor"]["host"]
    port = config["conexion_inversor"]["puerto"]
    tags = config["tags"]

    print(f"Conectando con el inversor en {host}:{port}...")
    client = ModbusClient(host=host, port=port, auto_open=True, auto_close=True)

    if not client.open():
        print("[ERROR] No se pudo conectar al inversor.")
        print("¿Has iniciado primero 'servidor_inversor.py' en su terminal correspondiente?")
        return

    print("¡Conexión establecida con éxito!")
    time.sleep(1)

    try:
        while True:
            opcion = mostrar_menu()

            if opcion == "1":
                print("\nEnviando orden de CONEXIÓN a red (Marcha)...")
                if client.write_single_coil(tags["orden_marcha"], True):
                    print("-> Comando enviado con éxito: El inversor comenzará a generar.")
                else:
                    print("-> [ERROR] No se pudo enviar el comando.")
                input("\nPresiona Enter para continuar...")

            elif opcion == "2":
                print("\nEnviando orden de DESCONEXIÓN de red (Paro)...")
                if client.write_single_coil(tags["orden_marcha"], False):
                    print("-> Comando enviado con éxito: El inversor pasará a espera.")
                else:
                    print("-> [ERROR] No se pudo enviar el comando.")
                input("\nPresiona Enter para continuar...")

            elif opcion == "3":
                valor_str = input("\nIntroduce la nueva consigna de inyección (0 a 100 %): ")
                try:
                    valor = int(valor_str)
                    if 0 <= valor <= 100:
                        if client.write_single_register(tags["limite_potencia"], valor):
                            print(f"-> Consigna fijada correctamente en {valor} %.")
                        else:
                            print("-> [ERROR] Fallo al escribir en el registro.")
                    else:
                        print("-> [AVISO] El valor debe estar entre 0 y 100 %.")
                except ValueError:
                    print("-> [AVISO] Entrada no válida. Debe ser un número entero.")
                input("\nPresiona Enter para continuar...")

            elif opcion == "4":
                print("\nEnviando orden de REARME de alarmas...")
                if client.write_single_coil(tags["reset_alarma"], True):
                    print("-> Comando de reset enviado.")
                else:
                    print("-> [ERROR] Fallo al enviar la orden de reset.")
                input("\nPresiona Enter para continuar...")

            elif opcion == "5":
                monitorizar_planta(client, config)

            elif opcion == "0":
                print("\nCerrando sesión del centro de control...")
                break

            else:
                print("\nOpción no válida.")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nPrograma terminado por el usuario.")
    finally:
        client.close()
        print("Conexión cerrada.")


if __name__ == "__main__":
    main()

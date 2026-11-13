"""
Panel SCADA / HMI para Supervisión y Control de Planta Fotovoltaica (Cliente Modbus TCP)
Asignatura: Informática Industrial Aplicada - Grado en Ingeniería Eléctrica

Este script simula la estación de operación (SCADA de sala de control).
En una instalación real, este código se ejecutaría en el PC del operador o servidor SCADA,
conectándose remotamente por red IP hacia la dirección del inversor en planta.
"""

import os
import time
from pyModbusTCP.client import ModbusClient

# --------------------------------------------------------------------------- #
# 1. PARÁMETROS DE RED Y TAGS MODBUS (INICIALMENTE HARDCODEADOS)
# --------------------------------------------------------------------------- #
# NOTA PARA EL ALUMNO (FASE 1):
# En la Fase 1 sustituirás estas variables hardcodeadas cargando 'config.json'.
INVERSOR_HOST = "localhost"
INVERSOR_PORT = 502

# Tags de control (Coils hacia el inversor)
TAG_ORDEN_MARCHA = 0       # True: Conectar y generar / False: Parar a espera
TAG_RESET_ALARMA = 1       # True: Resetear protecciones

# Tags de supervisión (Input Registers leídos del inversor)
TAG_ESTADO_INVERSOR = 100  # 0: Parado, 1: Standby, 2: Generando, 99: Alarma
TAG_TENSION_DC = 101       # Tensión continua campo solar (Voltios)
TAG_POTENCIA_ACTIVA = 102  # Potencia activa inyectada a la red (Vatios)
TAG_FRECUENCIA_RED = 103   # Frecuencia de red en décimas de Hz (500 = 50.0 Hz)
TAG_CODIGO_ALARMA = 104    # Código de alarma activa (0 = Sin alarma)

# Tags de consignas (Holding Registers escritos al inversor)
TAG_LIMITE_POTENCIA = 200  # Límite de potencia máxima de inyección (0 - 100 %)

# --------------------------------------------------------------------------- #
# 2. MAPAS DE ESTADOS Y TEXTOS PARA LA INTERFAZ
# --------------------------------------------------------------------------- #
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


# =========================================================================== #
# FASE 2: FUNCIÓN A COMPLETAR POR EL ALUMNO (SISTEMA DE BATERÍA BESS)
# =========================================================================== #
def leer_y_mostrar_bateria(client: ModbusClient, config: dict):
    """
    TODO (ALUMNO - FASE 2):
    1. Obtén las direcciones de 'bateria_soc' y 'bateria_potencia' desde config["tags"].
    2. Lee el registro de SoC usando: client.read_input_registers(DIRECCION_SOC, 1)
    3. Lee el registro de potencia de batería usando: client.read_input_registers(DIRECCION_POT, 1)
    4. Si ambas lecturas son válidas (distintas de None):
       Imprime por consola una línea con el formato:
       print(f"  [BATERÍA BESS]       : Carga (SoC): {soc}% | Potencia: {pot_bat} W")
    """
    # === ESCRIBE AQUÍ TU CÓDIGO (FASE 2) ===
    pass
    # =======================================


# --------------------------------------------------------------------------- #
# 3. FUNCIONES DE INTERFAZ SCADA
# --------------------------------------------------------------------------- #

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


def monitorizar_planta(client: ModbusClient, config: dict):
    """Bucle de supervisión continua de las variables de planta."""
    limpiar_pantalla()
    print("Iniciando monitorización en tiempo real... (Presiona Ctrl+C para volver al menú)")
    time.sleep(1)

    try:
        while True:
            limpiar_pantalla()

            # Lectura de los registros de estado y medidas
            regs_estado = client.read_input_registers(TAG_ESTADO_INVERSOR, 5)
            regs_holding = client.read_holding_registers(TAG_LIMITE_POTENCIA, 1)

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

            # FASE 2: Lectura de la batería si config está cargada
            if config:
                leer_y_mostrar_bateria(client, config)

            print("=" * 60)
            print("  (Presiona Ctrl+C para regresar al Menú Principal)")
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nRegresando al menú...")
        time.sleep(1)


# --------------------------------------------------------------------------- #
# 4. FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------- #

def main():
    # ----------------------------------------------------------------------- #
    # FASE 1 (ALUMNO): Al completar config.json, descomenta la carga:
    # import json
    # with open("config.json", "r", encoding="utf-8") as f:
    #     config = json.load(f)
    # host = config["conexion_inversor"]["host"]
    # port = config["conexion_inversor"]["puerto"]
    # ----------------------------------------------------------------------- #
    host = INVERSOR_HOST
    port = INVERSOR_PORT
    config = {}

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
                if client.write_single_coil(TAG_ORDEN_MARCHA, True):
                    print("-> Comando enviado con éxito: El inversor comenzará a generar.")
                else:
                    print("-> [ERROR] No se pudo enviar el comando.")
                input("\nPresiona Enter para continuar...")

            elif opcion == "2":
                print("\nEnviando orden de DESCONEXIÓN de red (Paro)...")
                if client.write_single_coil(TAG_ORDEN_MARCHA, False):
                    print("-> Comando enviado con éxito: El inversor pasará a espera.")
                else:
                    print("-> [ERROR] No se pudo enviar el comando.")
                input("\nPresiona Enter para continuar...")

            elif opcion == "3":
                valor_str = input("\nIntroduce la nueva consigna de inyección (0 a 100 %): ")
                try:
                    valor = int(valor_str)
                    if 0 <= valor <= 100:
                        if client.write_single_register(TAG_LIMITE_POTENCIA, valor):
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
                if client.write_single_coil(TAG_RESET_ALARMA, True):
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

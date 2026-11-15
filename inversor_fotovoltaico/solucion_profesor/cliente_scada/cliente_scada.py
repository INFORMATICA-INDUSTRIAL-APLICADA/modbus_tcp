"""
Solución Completa para el Profesor - SCADA Supervisión Planta Fotovoltaica con Batería
Asignatura: Informática Industrial Aplicada - Grado en Ingeniería Eléctrica
"""

import json
import os
import time
from pyModbusTCP.client import ModbusClient


def cargar_configuracion(ruta: str = "config.json") -> dict:
    """Lee y parsea el archivo de configuración local del SCADA."""
    ruta_absoluta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
    with open(ruta_absoluta, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# 1. PARÁMETROS DE RED Y TAGS CARGADOS DESDE config.json (FASE 1 RESUELTA)
# --------------------------------------------------------------------------- #
CONFIG = cargar_configuracion()

# Parámetros de conexión al inversor remoto
INVERSOR_HOST = CONFIG["conexion_inversor"]["host"]
INVERSOR_PORT = CONFIG["conexion_inversor"]["puerto"]

# Parámetros de adquisición del SCADA
TIEMPO_REFRESCO_SEGUNDOS = CONFIG["scada"]["tiempo_refresco_segundos"]

# Tags de control (Coils hacia el inversor)
TAG_ORDEN_MARCHA = CONFIG["tags"]["orden_marcha"]
TAG_RESET_ALARMA = CONFIG["tags"]["reset_alarma"]

# Tags de supervisión (Input Registers leídos del inversor)
TAG_ESTADO_INVERSOR = CONFIG["tags"]["estado_inversor"]
TAG_TENSION_DC = CONFIG["tags"]["tension_dc"]
TAG_POTENCIA_ACTIVA = CONFIG["tags"]["potencia_activa"]
TAG_FRECUENCIA_RED = CONFIG["tags"]["frecuencia_red"]
TAG_CODIGO_ALARMA = CONFIG["tags"]["codigo_alarma"]

# Tags de consignas (Holding Registers escritos al inversor)
TAG_LIMITE_POTENCIA = CONFIG["tags"]["limite_potencia"]

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
# FASE 2 RESUELTA: FUNCIÓN DE LECTURA Y VISUALIZACIÓN DE LA BATERÍA BESS
# =========================================================================== #
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
    try:
        while True:
            # Lectura individual de cada Tag de supervisión (Input Registers)
            reg_estado = client.read_input_registers(TAG_ESTADO_INVERSOR, 1)
            reg_vdc = client.read_input_registers(TAG_TENSION_DC, 1)
            reg_pac = client.read_input_registers(TAG_POTENCIA_ACTIVA, 1)
            reg_frec = client.read_input_registers(TAG_FRECUENCIA_RED, 1)
            reg_alarma = client.read_input_registers(TAG_CODIGO_ALARMA, 1)

            # Lectura del Tag de consigna (Holding Register)
            reg_limite = client.read_holding_registers(TAG_LIMITE_POTENCIA, 1)

            if None in (reg_estado, reg_vdc, reg_pac, reg_frec, reg_alarma, reg_limite):
                print("\n[ERROR] No se pudo comunicar con el inversor. Reintentando...")
                time.sleep(2)
                continue

            estado = reg_estado[0]
            vdc = reg_vdc[0]
            pac = reg_pac[0]
            frec_hz = reg_frec[0] / 10.0
            alarma = reg_alarma[0]
            limite_pct = reg_limite[0]

            texto_estado = STATE_MAP.get(estado, f"Desconocido ({estado})")
            texto_alarma = ALARM_MAP.get(alarma, f"Código {alarma}")

            limpiar_pantalla()
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

            # FASE 2: Lectura de la batería si CONFIG está cargada
            if config:
                leer_y_mostrar_bateria(client, config)

            print("=" * 60)
            print("  (Presiona Ctrl+C para regresar al Menú Principal)")
            time.sleep(TIEMPO_REFRESCO_SEGUNDOS)

    except KeyboardInterrupt:
        print("\nRegresando al menú...")
        time.sleep(1)


# --------------------------------------------------------------------------- #
# 4. FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------- #

def main():
    print(f"Conectando con el inversor en {INVERSOR_HOST}:{INVERSOR_PORT}...")
    client = ModbusClient(host=INVERSOR_HOST, port=INVERSOR_PORT, auto_open=True, auto_close=False)

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

            elif opcion == "2":
                print("\nEnviando orden de DESCONEXIÓN de red (Paro)...")
                if client.write_single_coil(TAG_ORDEN_MARCHA, False):
                    print("-> Comando enviado con éxito: El inversor pasará a espera.")
                else:
                    print("-> [ERROR] No se pudo enviar el comando.")

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

            elif opcion == "4":
                print("\nEnviando orden de REARME de alarmas...")
                if client.write_single_coil(TAG_RESET_ALARMA, True):
                    print("-> Comando de reset enviado.")
                else:
                    print("-> [ERROR] Fallo al enviar la orden de reset.")

            elif opcion == "5":
                monitorizar_planta(client, CONFIG)

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

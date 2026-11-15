"""
Simulador de Inversor Solar Fotovoltaico con Modbus TCP (Servidor / PLC de Campo)
Asignatura: Informática Industrial Aplicada - Grado en Ingeniería Eléctrica

Este script simula el equipo físico (el Inversor de la planta solar).
En una instalación real, este código se ejecutaría en el propio controlador
o pasarela de comunicaciones del inversor situado en el campo solar.
"""

import json
import os
import random
import time
from pyModbusTCP.server import ModbusServer


def cargar_configuracion(ruta: str = "config.json") -> dict:
    """Lee y parsea el archivo de configuración local del inversor."""
    ruta_absoluta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
    with open(ruta_absoluta, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# 1. PARÁMETROS DE RED Y REGISTROS (INICIALMENTE HARDCODEADOS)
# --------------------------------------------------------------------------- #
# TODO (ALUMNO - FASE 1):
# 1. Crea tu archivo 'config.json' a partir de 'config_plantilla_incompleta.json'.
# 2. Cambia 'CONFIG = {}' por 'CONFIG = cargar_configuracion()'.
# 3. Sustituye todos los valores fijos (hardcodeados) de abajo por consultas al
#    diccionario CONFIG, como se indica en el comentario de cada línea.
CONFIG = {}

# Parámetros de red donde escucha el servidor Modbus
SERVER_HOST = "localhost"          # -> CONFIG["servidor"]["host"]
SERVER_PORT = 502                  # -> CONFIG["servidor"]["puerto"]

# Parámetros eléctricos nominales de la planta
POTENCIA_NOMINAL_W = 32000         # -> CONFIG["parametros_planta"]["potencia_nominal_w"]
TENSION_PANELES_VDC = 680          # -> CONFIG["parametros_planta"]["tension_paneles_vdc"]

# Coils (Mandos binarios de control recibidos del SCADA)
ADDR_ORDEN_MARCHA = 0              # -> CONFIG["registros"]["orden_marcha"]
ADDR_RESET_ALARMA = 1              # -> CONFIG["registros"]["reset_alarma"]

# Input Registers (Medidas y estados internos expuestos al SCADA - Solo Lectura)
ADDR_ESTADO_INVERSOR = 100         # -> CONFIG["registros"]["estado_inversor"]
ADDR_TENSION_DC = 101              # -> CONFIG["registros"]["tension_dc"]
ADDR_POTENCIA_ACTIVA = 102         # -> CONFIG["registros"]["potencia_activa"]
ADDR_FRECUENCIA_RED = 103          # -> CONFIG["registros"]["frecuencia_red"]
ADDR_CODIGO_ALARMA = 104           # -> CONFIG["registros"]["codigo_alarma"]

# Holding Registers (Consignas y parámetros ajustables recibidos del SCADA)
ADDR_LIMITE_POTENCIA = 200         # -> CONFIG["registros"]["limite_potencia"]

# --------------------------------------------------------------------------- #
# 2. DEFINICIÓN DE ESTADOS Y CÓDIGOS DE ALARMA
# --------------------------------------------------------------------------- #
STATE_STOPPED = 0
STATE_STANDBY = 1
STATE_RUNNING = 2
STATE_ALARM = 99

STATE_NAMES = {
    STATE_STOPPED: "PARADO",
    STATE_STANDBY: "EN ESPERA (STANDBY)",
    STATE_RUNNING: "GENERANDO",
    STATE_ALARM: "ALARMA (PROTECCIÓN DISPARADA)"
}

ALARM_NONE = 0
ALARM_GRID_VOLTAGE = 101
ALARM_OVERTEMP = 102


# --------------------------------------------------------------------------- #
# 3. FUNCIONES DE SIMULACIÓN Y CONTROL DEL INVERSOR
# --------------------------------------------------------------------------- #

def inicializar_registros(server: ModbusServer):
    """Establece los valores iniciales de los registros al arrancar el inversor."""
    print("[INIT] Inicializando banco de registros Modbus del inversor...")
    server.data_bank.set_coils(ADDR_ORDEN_MARCHA, [False])
    server.data_bank.set_coils(ADDR_RESET_ALARMA, [False])
    server.data_bank.set_input_registers(ADDR_ESTADO_INVERSOR, [STATE_STANDBY])
    server.data_bank.set_input_registers(ADDR_TENSION_DC, [0])
    server.data_bank.set_input_registers(ADDR_POTENCIA_ACTIVA, [0])
    server.data_bank.set_input_registers(ADDR_FRECUENCIA_RED, [500])  # 50.0 Hz
    server.data_bank.set_input_registers(ADDR_CODIGO_ALARMA, [ALARM_NONE])
    server.data_bank.set_holding_registers(ADDR_LIMITE_POTENCIA, [100])  # 100% por defecto


# =========================================================================== #
# FASE 2: FUNCIÓN A COMPLETAR POR EL ALUMNO (SISTEMA DE BATERÍA BESS)
# =========================================================================== #
def simular_y_actualizar_bateria(server: ModbusServer, config: dict, potencia_solar_w: int):
    """
    TODO (ALUMNO - FASE 2):
    1. Obtén las direcciones de 'bateria_soc' y 'bateria_potencia' desde config["registros"].
    2. Determina el estado de la batería:
       - Si potencia_solar_w es mayor de 15000 W (hay excedente solar), la batería se carga:
         fija potencia_bateria = 4000 (W) y soc_bateria = 85 (%).
       - Si no, la batería está en reposo:
         fija potencia_bateria = 0 (W) y soc_bateria = 60 (%).
    3. Escribe ambos valores en los Input Registers del servidor usando:
       server.data_bank.set_input_registers(DIRECCION, [VALOR])
    """
    # === ESCRIBE AQUÍ TU CÓDIGO (Aprox. 6-8 líneas) ===
    pass
    # ==================================================


# --------------------------------------------------------------------------- #
# 4. BUCLE PRINCIPAL DEL SERVIDOR
# --------------------------------------------------------------------------- #

def main():
    print("=" * 65)
    print("  SIMULADOR DE INVERSOR SOLAR INDUSTRIAL (EQUIPO DE CAMPO)")
    print(f"  Servicio Modbus TCP escuchando en: {SERVER_HOST}:{SERVER_PORT}")
    print("=" * 65)

    server = ModbusServer(host=SERVER_HOST, port=SERVER_PORT, no_block=True)

    try:
        server.start()
        print("[SISTEMA] Inversor encendido y listo para recibir conexiones SCADA.")
        inicializar_registros(server)

        estado_actual = STATE_STANDBY
        segundos_generando = 0
        tiempo_proxima_alarma = random.randint(15, 25)  # Perturbación aleatoria cada 20 ± 5 s

        while True:
            # 1. Comprobar mandos enviados por el SCADA (Coils)
            coils_run = server.data_bank.get_coils(ADDR_ORDEN_MARCHA, 1)
            coils_reset = server.data_bank.get_coils(ADDR_RESET_ALARMA, 1)

            orden_marcha = coils_run[0] if coils_run else False
            orden_reset = coils_reset[0] if coils_reset else False

            # Gestión del rearme de alarma (pulsador de rearme en Coil 1)
            if orden_reset:
                server.data_bank.set_coils(ADDR_RESET_ALARMA, [False])
                if estado_actual == STATE_ALARM:
                    print("\n[EVENTO] Orden de reset recibida del SCADA. Rearmando protecciones...")
                    server.data_bank.set_input_registers(ADDR_CODIGO_ALARMA, [ALARM_NONE])
                    segundos_generando = 0
                    tiempo_proxima_alarma = random.randint(15, 25)
                    estado_actual = STATE_STANDBY

            # Gestión de transiciones de marcha/paro
            if estado_actual == STATE_STANDBY and orden_marcha:
                print("\n[EVENTO] Orden de marcha recibida. Sincronizando con la red eléctrica...")
                segundos_generando = 0
                tiempo_proxima_alarma = random.randint(15, 25)
                estado_actual = STATE_RUNNING
            elif estado_actual == STATE_RUNNING and not orden_marcha:
                print("\n[EVENTO] Orden de paro recibida. Desconectando de red...")
                segundos_generando = 0
                estado_actual = STATE_STANDBY
            elif estado_actual == STATE_ALARM and orden_marcha:
                # Enclavamiento de seguridad: no permite arrancar sin rearmar antes la alarma
                print("\n[AVISO] Orden de marcha rechazada: protección disparada. Rearme primero la alarma.")
                server.data_bank.set_coils(ADDR_ORDEN_MARCHA, [False])

            # 2. Simulación física según el estado
            if estado_actual == STATE_RUNNING:
                # Lectura de la consigna de limitación de potencia (capada en firmware a 0 - 100%)
                limite_regs = server.data_bank.get_holding_registers(ADDR_LIMITE_POTENCIA, 1)
                limite_pct = limite_regs[0] if limite_regs else 100
                limite_pct = max(0, min(100, limite_pct))

                segundos_generando += 1

                # Simulación de perturbación fortuita externa cada 20 ± 5 segundos de generación
                if segundos_generando >= tiempo_proxima_alarma:
                    codigo_disparo = random.choice([ALARM_GRID_VOLTAGE, ALARM_OVERTEMP])
                    print(f"\n[ALARMA] ¡Perturbación detectada! Disparo de protección (Código {codigo_disparo}).")
                    print("         Inversor desconectado de la red. Esperando orden de rearme desde el SCADA...")
                    estado_actual = STATE_ALARM
                    segundos_generando = 0
                    server.data_bank.set_coils(ADDR_ORDEN_MARCHA, [False])
                    server.data_bank.set_input_registers(ADDR_CODIGO_ALARMA, [codigo_disparo])
                    vdc = 400
                    potencia_activa = 0
                    frecuencia_x10 = 500
                else:
                    # Tensión continua de paneles en torno al valor nominal (~680 V)
                    vdc = int(TENSION_PANELES_VDC + random.uniform(-5, 5))

                    # Potencia solar disponible en torno a la nominal (~32.000 W)
                    potencia_nominal_disp = POTENCIA_NOMINAL_W + random.randint(-500, 500)
                    potencia_activa = int(potencia_nominal_disp * (limite_pct / 100.0))

                    # Frecuencia de red: ~50.0 Hz (500 décimas de Hz)
                    frecuencia_x10 = 500 + random.choice([-1, 0, 1])

            else:
                # En espera, parado o en alarma
                vdc = 400 if estado_actual in (STATE_STANDBY, STATE_ALARM) else 0
                potencia_activa = 0
                frecuencia_x10 = 500
                limite_regs = server.data_bank.get_holding_registers(ADDR_LIMITE_POTENCIA, 1)
                limite_pct = limite_regs[0] if limite_regs else 100

            # 3. Publicar valores en los registros Modbus locales
            server.data_bank.set_input_registers(ADDR_ESTADO_INVERSOR, [estado_actual])
            server.data_bank.set_input_registers(ADDR_TENSION_DC, [vdc])
            server.data_bank.set_input_registers(ADDR_POTENCIA_ACTIVA, [potencia_activa])
            server.data_bank.set_input_registers(ADDR_FRECUENCIA_RED, [frecuencia_x10])

            # 4. FASE 2: Llamada a la simulación de la batería si CONFIG está cargada
            if CONFIG:
                simular_y_actualizar_bateria(server, CONFIG, potencia_activa)

            # 5. Log por consola local del inversor
            nombre_estado = STATE_NAMES.get(estado_actual, "DESCONOCIDO")
            frec_hz = frecuencia_x10 / 10.0
            print(f"[INVERSOR] Estado: {nombre_estado:<22} | Vdc: {vdc:>3} V | "
                  f"Pac: {potencia_activa:>5} W (Límite: {limite_pct:>3}%) | Frec: {frec_hz:.1f} Hz")

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[SISTEMA] Deteniendo el servidor Modbus por teclado...")
    except Exception as e:
        print(f"\n[ERROR FATAL] Ocurrió una excepción: {e}")
    finally:
        server.stop()
        print("[SISTEMA] Servidor detenido y puerto liberado.")


if __name__ == "__main__":
    main()

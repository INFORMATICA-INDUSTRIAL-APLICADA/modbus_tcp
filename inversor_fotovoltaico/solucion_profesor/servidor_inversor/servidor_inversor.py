"""
Solución Completa para el Profesor - Servidor Inversor Solar Fotovoltaico con Batería
Asignatura: Informática Industrial Aplicada - Grado en Ingeniería Eléctrica
"""

import json
import random
import time
from pyModbusTCP.server import ModbusServer

# --------------------------------------------------------------------------- #
# DEFINICIÓN DE ESTADOS Y CÓDIGOS DE ALARMA
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


def cargar_configuracion(ruta: str = "config.json") -> dict:
    """Lee y parsea el archivo de configuración local del inversor."""
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def inicializar_registros(server: ModbusServer, regs: dict):
    """Establece los valores iniciales de los registros al arrancar el inversor."""
    print("[INIT] Inicializando banco de registros Modbus según config.json...")
    server.data_bank.set_coils(regs["orden_marcha"], [False])
    server.data_bank.set_coils(regs["reset_alarma"], [False])
    server.data_bank.set_input_registers(regs["estado_inversor"], [STATE_STANDBY])
    server.data_bank.set_input_registers(regs["tension_dc"], [0])
    server.data_bank.set_input_registers(regs["potencia_activa"], [0])
    server.data_bank.set_input_registers(regs["frecuencia_red"], [500])  # 50.0 Hz
    server.data_bank.set_input_registers(regs["codigo_alarma"], [ALARM_NONE])
    server.data_bank.set_holding_registers(regs["limite_potencia"], [100])

    # Inicializar registros de batería (Fase 2) si existen
    if "bateria_soc" in regs and "bateria_potencia" in regs:
        server.data_bank.set_input_registers(regs["bateria_soc"], [50])
        server.data_bank.set_input_registers(regs["bateria_potencia"], [0])


def simular_y_actualizar_bateria(server: ModbusServer, config: dict, potencia_solar_w: int):
    """
    FASE 2 (SOLUCIÓN): Simulación del estado de carga y potencia de la batería.
    """
    regs = config["registros"]
    addr_soc = regs["bateria_soc"]
    addr_power = regs["bateria_potencia"]

    # Si hay excedente solar (> 15 kW), cargamos la batería
    if potencia_solar_w > 15000:
        potencia_bateria = 4000  # Cargando a 4 kW
        soc_bateria = 85         # 85% de carga
    else:
        potencia_bateria = 0     # Reposo
        soc_bateria = 60         # 60% de carga

    server.data_bank.set_input_registers(addr_soc, [soc_bateria])
    server.data_bank.set_input_registers(addr_power, [potencia_bateria])


def main():
    config = cargar_configuracion()
    host = config["servidor"]["host"]
    port = config["servidor"]["puerto"]
    regs = config["registros"]

    print("=" * 65)
    print("  SIMULADOR DE INVERSOR SOLAR INDUSTRIAL (SOLUCIÓN COMPLETA)")
    print(f"  Servicio Modbus escuchando en: {host}:{port}")
    print("=" * 65)

    server = ModbusServer(host=host, port=port, no_block=True)

    try:
        server.start()
        print("[SISTEMA] Inversor encendido y listo para recibir conexiones SCADA.")
        inicializar_registros(server, regs)

        estado_actual = STATE_STANDBY

        while True:
            # 1. Comprobar mandos enviados por el SCADA (Coils)
            coils_run = server.data_bank.get_coils(regs["orden_marcha"], 1)
            coils_reset = server.data_bank.get_coils(regs["reset_alarma"], 1)

            orden_marcha = coils_run[0] if coils_run else False
            orden_reset = coils_reset[0] if coils_reset else False

            # Gestión del rearme de alarma
            if orden_reset and estado_actual == STATE_ALARM:
                print("\n[EVENTO] Orden de reset recibida del SCADA. Rearmando protecciones...")
                server.data_bank.set_coils(regs["reset_alarma"], [False])
                server.data_bank.set_input_registers(regs["codigo_alarma"], [ALARM_NONE])
                estado_actual = STATE_STANDBY

            # Gestión de transiciones de marcha/paro
            if estado_actual == STATE_STANDBY and orden_marcha:
                print("\n[EVENTO] Orden de marcha recibida. Sincronizando con la red eléctrica...")
                estado_actual = STATE_RUNNING
            elif estado_actual == STATE_RUNNING and not orden_marcha:
                print("\n[EVENTO] Orden de paro recibida. Desconectando de red...")
                estado_actual = STATE_STANDBY

            # 2. Simulación física según el estado
            if estado_actual == STATE_RUNNING:
                vdc = int(680 + random.uniform(-5, 5))

                limite_regs = server.data_bank.get_holding_registers(regs["limite_potencia"], 1)
                limite_pct = limite_regs[0] if limite_regs else 100
                limite_pct = max(0, min(100, limite_pct))

                potencia_nominal_disp = 32000 + random.randint(-500, 500)
                potencia_activa = int(potencia_nominal_disp * (limite_pct / 100.0))
                frecuencia_x10 = 500 + random.choice([-1, 0, 1])

            else:
                vdc = 400 if estado_actual == STATE_STANDBY else 0
                potencia_activa = 0
                frecuencia_x10 = 500
                limite_pct = 100

            # 3. Publicar valores en los registros Modbus
            server.data_bank.set_input_registers(regs["estado_inversor"], [estado_actual])
            server.data_bank.set_input_registers(regs["tension_dc"], [vdc])
            server.data_bank.set_input_registers(regs["potencia_activa"], [potencia_activa])
            server.data_bank.set_input_registers(regs["frecuencia_red"], [frecuencia_x10])

            # 4. FASE 2: Actualización de la batería
            simular_y_actualizar_bateria(server, config, potencia_activa)

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

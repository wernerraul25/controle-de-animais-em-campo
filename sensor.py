import RPi.GPIO as GPIO
import time
import requests

# --- Configurações
GPIO.setmode(GPIO.BCM)
PIN_TRIG_A = 18 # Ponto A
PIN_ECHO_A = 24 
PIN_TRIG_B = 17 # Ponto B
PIN_ECHO_B = 27 

PIN_LED_A = 22  # LED para o Ponto A
PIN_LED_B = 23  # LED para o Ponto B
BLINK_DURATION_SEC = 0.3 # Duração do "pisca"


FLASK_SERVER_IP = "127.0.0.1" # rodando na própria Pi por enquanto
FLASK_URL = f"http://{FLASK_SERVER_IP}:5000/api/evento"

DISTANCIA_LIMITE_CM = 10 # Distância para contar como "passagem"

# --- Setup dos Pinos
print("Configurando pinos...")
GPIO.setup([PIN_TRIG_A, PIN_TRIG_B], GPIO.OUT)
GPIO.setup([PIN_ECHO_A, PIN_ECHO_B], GPIO.IN)
GPIO.setup([PIN_LED_A, PIN_LED_B], GPIO.OUT)
GPIO.output([PIN_LED_A, PIN_LED_B], GPIO.LOW) 

# --- Funções Auxiliares
def medir_distancia(pin_trigger, pin_echo):
    """Mede a distância de um sensor HC-SR04."""
    GPIO.output(pin_trigger, True)
    time.sleep(0.00001)
    GPIO.output(pin_trigger, False)

    start_time = time.time()
    stop_time = time.time()
    
    # Timeout para não travar se o pino não responder
    timeout_start = time.time()
    while GPIO.input(pin_echo) == 0 and time.time() - timeout_start < 0.1:
        start_time = time.time()
    
    timeout_stop = time.time()
    while GPIO.input(pin_echo) == 1 and time.time() - timeout_stop < 0.1:
        stop_time = time.time()

    duracao_pulso = stop_time - start_time
    distancia = (duracao_pulso * 34300) / 2
    
    # Retorna uma distância válida ou 999 (muito longe)
    return distancia if 0 < distancia < 400 else 999

def enviar_evento_api(sensor_id):
    """Envia o evento (A ou B) para a API Flask."""
    try:
        payload = {"sensor": sensor_id}
        requests.post(FLASK_URL, json=payload, timeout=3)
        print(f"EVENTO: Passagem detectada no Sensor {sensor_id}. API notificada.")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar com a API: {e}")

# --- Loop Principal (Lógica de Borda)
print("Sistema de contagem de eventos (A e B) iniciado.")

# Estados dos sensores
sensor_A_ativo = False
sensor_B_ativo = False


led_A_blink_start_time = None
led_B_blink_start_time = None


try:
    while True:
        # 1. Mede a distância nos dois sensores
        dist_A = medir_distancia(PIN_TRIG_A, PIN_ECHO_A)
        time.sleep(0.05) # Pausa pequena entre medições
        dist_B = medir_distancia(PIN_TRIG_B, PIN_ECHO_B)

        # --- Lógica do Sensor A
        if dist_A < DISTANCIA_LIMITE_CM:
            # Sensor está disparado (algo está na frente)
            if not sensor_A_ativo:
                # O animal ACABOU DE CHEGAR.
                sensor_A_ativo = True
                enviar_evento_api("A") # Envia o evento de contagem
                led_A_blink_start_time = time.time()
        else:
            # Sensor está livre
            if sensor_A_ativo:
                # O animal ACABOU DE SAIR.
                # reseta o sensor para permitir a próxima contagem.
                sensor_A_ativo = False

        # --- Lógica do Sensor B
        if dist_B < DISTANCIA_LIMITE_CM:
            # Sensor está disparado
            if not sensor_B_ativo:
                # O animal ACABOU DE CHEGAR no sensor B.
                sensor_B_ativo = True
                enviar_evento_api("B") # Envia o evento de contagem
                led_B_blink_start_time = time.time()
        else:
            # Sensor está livre
            if sensor_B_ativo:
                # O animal ACABOU DE SAIR do sensor B
                # "Reseta" o sensor
                sensor_B_ativo = False

        # --- Gerenciamento dos LEDs
        # LED pisca sem travar o loop principal
        
        # Gerencia o LED A
        if led_A_blink_start_time:
            if time.time() - led_A_blink_start_time < BLINK_DURATION_SEC:
                GPIO.output(PIN_LED_A, GPIO.HIGH) # Mantém aceso
            else:
                GPIO.output(PIN_LED_A, GPIO.LOW)  # Apaga
                led_A_blink_start_time = None  # Reseta o blink
        
        # Gerencia o LED B
        if led_B_blink_start_time:
            if time.time() - led_B_blink_start_time < BLINK_DURATION_SEC:
                GPIO.output(PIN_LED_B, GPIO.HIGH) # Mantém aceso
            else:
                GPIO.output(PIN_LED_B, GPIO.LOW)  # Apaga
                led_B_blink_start_time = None      # Reseta o blink

        time.sleep(0.1) # Intervalo do loop principal

except KeyboardInterrupt:
    print("Programa finalizado.")
finally:
    GPIO.cleanup()
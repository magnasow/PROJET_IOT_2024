from tb_device_mqtt import TBDeviceMqttClient
import time
import serial
from random import randint

# Paramètres USB série
SENSOR_DATA_SOURCE = "file"  # Peut être "serial", "file", ou "random"
SERIAL_PORT = "COM9"
SERIAL_BAUDRATE = 9600
ser = None

# Configuration du client ThingsBoard
TB_SERVER = "thingsboard.cloud"
TB_PORT = 1883
DEVICE_TOKEN = "AyNL4OqIQiBefMfW59qH"

def config_serial(serial_port, baud_rate=9600):
    return serial.Serial(serial_port, baudrate=baud_rate)

def read_serial(ser):
    return ser.readline().strip().decode()

def get_sensor_data(ser):
    raw_sensor = read_serial(ser)
    print(raw_sensor)
    if raw_sensor.startswith("#"):
        sensors_data = raw_sensor.strip().split("#")[1]
        humidity, temperature, distance = sensors_data.split(",")
        return float(humidity), float(temperature), float(distance)
    else:
        print('ERROR: Obtention des valeurs du capteur Arduino via le port série')
        return None, None, None

def read_file():
    file_path = "C:/Users/Mariéta/Documents/Projet_IOT_2024/Station_meteo_gw/device_data.txt"
    try:
        with open(file_path, "r") as fd:
            sensor_data = fd.readlines()
            return sensor_data
    except FileNotFoundError:
        print(f"Le fichier '{file_path}' n'a pas été trouvé.")
        return None

def get_sensor_data_from_file(line):
    if line.startswith("#"):
        sensors_data = line.strip().split("#")[1]
        values = sensors_data.split(",")
        if len(values) == 3:
            humidity, temperature, distance = values
            return float(humidity), float(temperature), float(distance)
        else:
            print('ERROR: Données du capteur non valides, nombre de valeurs incorrect.')
            return None, None, None
    else:
        print('ERROR: Données du capteur non valides')
        return None, None, None

def tb_connect(addr, port, device_token):
    return TBDeviceMqttClient(addr, port, device_token)

def send_sensor_data(client, timestamp, humidity, temperature, distance, alert):

    telemetry_with_ts = {"ts": timestamp, "values": {"humidity": humidity, "temperature": temperature, "distance": distance, "alert": alert}}
    print(f"Envoi des télémesures {telemetry_with_ts}")
    result = client.send_telemetry(telemetry_with_ts)
    if result.get() == 0:
        print("OK")
    else:
        print(f"ERREUR --> {result.get()}")

def get_latest_telemetry(client):
    response = client.get_telemetry()
    data = response.get()
    if response.get() == 0 and data:
        return data
    else:
        print("Erreur de récupération des télémesures")
        return None

def evaluate_flood_risk(humidity, temperature, water_level):
    NULL, LOW, MODERATE, HIGH = 0, 1, 2, 3
    flood_risk = NULL

    will_rain = humidity > 80  # Critère simplifié pour la pluie

    if will_rain:
        if water_level == 1:  # EMPTY
            flood_risk = LOW
        elif water_level == 2:  # HALF_FULL
            flood_risk = MODERATE
        elif water_level == 3:  # FULL
            flood_risk = HIGH
    else:
        if water_level == 3:  # FULL
            flood_risk = LOW
        else:
            flood_risk = NULL

    return flood_risk

def send_alert(flood_risk):
    alert = " "
    if flood_risk == 3:  # HIGH
        print("ALERTE : Risque élevé d'inondation!")
        alert =  "Risque élevé d'inondation"
    elif flood_risk == 2:  # MODERATE
        print("ALERTE : Risque modéré d'inondation.")
        alert = "Risque modéré d'inondation"
    elif flood_risk == 1:  # LOW
        print("ALERTE : Risque faible d'inondation.")
        alert = "Risque faible d'inondation"
    else:
        print("Pas de risque d'inondation.")
        alert = "Pas de risque d'inondation"
    return alert

def main():
    global ser
    if SENSOR_DATA_SOURCE == "serial":
        ser = config_serial(SERIAL_PORT, SERIAL_BAUDRATE)
    elif SENSOR_DATA_SOURCE == "file":
        sensor_data_from_file = read_file()
        if sensor_data_from_file is None:
            print("Aucune donnée de capteur disponible.")
            return
        number = 0

    print(f"Connexion à {TB_SERVER}...")
    tb_client = tb_connect(TB_SERVER, TB_PORT, DEVICE_TOKEN)
    tb_client.max_inflight_messages_set(100)
    tb_client.connect()
    time.sleep(5)

    while True:
        timestamp = int(round(time.time() * 1000))
        humidity, temperature, distance = None, None, None

        if SENSOR_DATA_SOURCE == "serial":
            humidity, temperature, distance = get_sensor_data(ser)
        elif SENSOR_DATA_SOURCE == "file":
            if number < len(sensor_data_from_file):
                humidity, temperature, distance = get_sensor_data_from_file(sensor_data_from_file[number])
                print(f"Données du fichier : Humidité={humidity}, Température={temperature}, Distance={distance}")
                number += 1
                if number >= len(sensor_data_from_file):
                    number = 0
            else:
                print("Fichier de données terminé. Redémarrage de la lecture des données.")
                number = 0
        elif SENSOR_DATA_SOURCE == "random":
            humidity = 75.00 + randint(0, 5)
            temperature = 25.00 + randint(0, 3)
            distance = 1 + randint(0, 1)
        
        if humidity is not None and temperature is not None and distance is not None:
            # Évaluation des risques d’inondation
            flood_risk = evaluate_flood_risk(humidity, temperature, distance)
            alert = send_alert(flood_risk)
            
            send_sensor_data(tb_client, timestamp, humidity, temperature, distance, alert)


        time.sleep(5)

if __name__ == "__main__":
    main()

import uasyncio as asyncio
import usocket as socket
from machine import Pin, I2C, Timer, reset, WDT
import ujson
import network
import os
import time
import gc

# Налаштування пінів для підключення компонентів
pins = {
    "SCL": {"number": 22, "direction": "input", "default_state": 0},
    "SDA": {"number": 21, "direction": "input", "default_state": 0},
    "I2C_POWER": {"number": 23, "direction": "output", "default_state": 0}, 
    "WIFI_BUTTON": {"number": 14, "direction": "input", "default_state": 1}, 
    "FREE_MODE_BUTTON": {"number": 32, "direction": "input", "default_state": 1}, 
    "FREE_MODE_CONTACT": {"number": 33, "direction": "output", "default_state": 0},  
    "R0": {"number": 5, "direction": "output", "default_state": 0},  
    "R1": {"number": 17, "direction": "output", "default_state": 0},  
    "R2": {"number": 16, "direction": "output", "default_state": 0},  
    "R3": {"number": 4, "direction": "output", "default_state": 0},  
    "C0": {"number": 25, "direction": "output", "default_state": 0},  
    "C1": {"number": 26, "direction": "output", "default_state": 0},  
    "C2": {"number": 27, "direction": "output", "default_state": 0},  
    "ENTER": {"number": 15, "direction": "output", "default_state": 0},  
    "ESC": {"number": 2, "direction": "output", "default_state": 0},  
    "LEFT_SUGAR": {"number": 13, "direction": "output", "default_state": 0},  
    "RIGHT_SUGAR": {"number": 12, "direction": "output", "default_state": 0}
}

# Налаштування клавіатури, де комбінації рядків і стовпців представляють кнопки
button_combinations = {
    "1": ("R0", "C0"),
    "2": ("R0", "C1"),
    "3": ("R0", "C2"),
    "4": ("R1", "C0"),
    "5": ("R1", "C1"),
    "6": ("R1", "C2"),
    "7": ("R2", "C0"),
    "8": ("R2", "C1"),
    "9": ("R2", "C2"),
    "0": ("R3", "C0"),
    "E": ("R3", "C1"),
    "C": ("R3", "C2")
}

# Налаштування сенсорів з адресами і пін-кодами
sensors = {
    "Sensor1": {"address": 35, "pin": 0, "settings": ["None", "None"]},
    "Sensor2": {"address": 35, "pin": 1, "settings": ["None", "None"]},
    "Sensor3": {"address": 35, "pin": 2, "settings": ["None", "None"]},
    "Sensor4": {"address": 35, "pin": 3, "settings": ["None", "None"]},
    "Sensor5": {"address": 35, "pin": 4, "settings": ["None", "None"]},
    "Sensor6": {"address": 35, "pin": 5, "settings": ["None", "None"]},
    "Sensor7": {"address": 35, "pin": 6, "settings": ["None", "None"]},
    "Sensor8": {"address": 35, "pin": 7, "settings": ["None", "None"]},
    "Sensor9": {"address": 36, "pin": 0, "settings": ["None", "None"]},
    "Sensor10": {"address": 36, "pin": 1, "settings": ["None", "None"]},
    "Sensor11": {"address": 36, "pin": 2, "settings": ["None", "None"]},
    "Sensor12": {"address": 36, "pin": 3, "settings": ["None", "None"]},
    "Sensor13": {"address": 36, "pin": 4, "settings": ["None", "None"]},
    "Sensor14": {"address": 36, "pin": 5, "settings": ["None", "None"]},
    "Sensor15": {"address": 36, "pin": 6, "settings": ["None", "None"]},
    "Sensor16": {"address": 36, "pin": 7, "settings": ["None", "None"]},
    "Sensor17": {"address": 34, "pin": 0, "settings": ["None", "None"]},
    "Sensor18": {"address": 34, "pin": 1, "settings": ["None", "None"]},
    "Sensor19": {"address": 34, "pin": 2, "settings": ["None", "None"]},
    "Sensor20": {"address": 34, "pin": 3, "settings": ["None", "None"]},
    "Sensor21": {"address": 34, "pin": 4, "settings": ["None", "None"]},
    "Sensor22": {"address": 34, "pin": 5, "settings": ["None", "None"]},
    "Sensor23": {"address": 34, "pin": 6, "settings": ["None", "None"]},
    "Sensor24": {"address": 34, "pin": 7, "settings": ["None", "None"]},
    "Sensor25": {"address": 33, "pin": 0, "settings": ["None", "None"]},
    "Sensor26": {"address": 33, "pin": 1, "settings": ["None", "None"]},
    "Sensor27": {"address": 33, "pin": 2, "settings": ["None", "None"]},
    "Sensor28": {"address": 33, "pin": 3, "settings": ["None", "None"]},
    "Sensor29": {"address": 33, "pin": 4, "settings": ["None", "None"]},
    "Sensor30": {"address": 33, "pin": 5, "settings": ["None", "None"]},
    "Sensor31": {"address": 33, "pin": 6, "settings": ["None", "None"]},
    "Sensor32": {"address": 33, "pin": 7, "settings": ["None", "None"]}
}

# Налаштування загальної системи
settings = {
    "delay_between_clicks": 200,  # Затримка між натисканнями (мс)
    "sensor_activation_delay": 200,  # Затримка активації сенсора (мс)
    "clamp_C_before_combination": True,  # Затискати "C" перед комбінацією
    "calibration_interval": True,  # Інтервал калібрування сенсорів
    "free_mode_timeout": 3,  # Таймаут безкоштовного режиму (хвилини)
    "access_point_deactivation_time": 30,  # Час деактивації точки доступу (хвилини)
    "sensors": sensors  # Налаштування сенсорів
}

# Функція для отримання поточного часу у вигляді рядка
def get_timestamp():
    t = time.localtime()
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(t[0], t[1], t[2], t[3], t[4], t[5])

# Функція для логування з додаванням часу
def log(message):
    timestamp = get_timestamp()
    print(f"[{timestamp}] {message}")
    
# Змінні для відстеження стану пристроїв і часу останнього логування
prev_devices = set()
last_log_time = time.time()    

# Збереження налаштувань у файл
def save_settings():
    log("Saving settings to file")
    with open('settings.json', 'w') as f:
        ujson.dump(settings, f)
    log("Settings saved")

# Функція для відкладеного перезавантаження системи
async def delayed_reset(delay):
    log(f"Delaying system reset for {delay} seconds")
    await asyncio.sleep(delay)
    log("System reset")
    reset()

# Завантаження налаштувань з файлу
try:
    log("Loading settings from file")
    with open('settings.json', 'r') as f:
        settings = ujson.load(f)
        sensors = settings["sensors"]
    log("Settings loaded successfully")
except OSError:
    log("Settings file not found, saving default settings")
    save_settings()

# Ініціалізація I2C інтерфейсу для сенсорів
log("Initializing I2C interface for sensors")
i2c = I2C(0, scl=Pin(pins["SCL"]["number"], Pin.IN, Pin.PULL_UP), sda=Pin(pins["SDA"]["number"], Pin.IN, Pin.PULL_UP), freq=100000)
devices = i2c.scan()
log(f"I2C devices found: {devices}")

# Блокування для запобігання обробці інших сигналів під час виконання комбінації
execution_lock = asyncio.Lock()


# Функція для обробки дій при натисканні сенсора
async def handle_sensor_action(sensor):
    async with execution_lock:
        log(f"Handling action for sensor: {sensor}")
        delay_between_clicks = settings["delay_between_clicks"] / 1000.0  # Перетворюємо мілісекунди в секунди
        sensor_activation_delay = settings["sensor_activation_delay"] / 1000.0  # Перетворюємо мілісекунди в секунди
        clamp_C_before_combination = settings["clamp_C_before_combination"]
        start_time = time.ticks_ms()  # Записуємо час початку натискання

        address = sensors[sensor]["address"]
        pin = sensors[sensor]["pin"]

        # Оновлення списку пристроїв перед обробкою сигналу
        global devices
        devices = i2c.scan()
        log(f"Updated I2C devices: {devices}")

        # Перевірка фізичної присутності сенсора
        if address not in devices:
            log(f"Sensor {sensor} not physically present, skipping")
            return

        # Перевірка стану сенсора
        try:
            state = i2c.readfrom(address, 1)[0]
            log(f"Sensor {sensor} state: {state}")
        except OSError:
            log(f"Sensor {sensor} not responding, skipping")
            return  # Якщо сенсор не відповідає, виходимо з функції

        # Надсилаємо інформацію про активний сенсор на клієнт
        global last_active_sensor
        last_active_sensor = {"name": sensor, "active": True}
        log(f"Sending sensor event: {last_active_sensor}")  # Додаємо журналювання
        await send_sensor_event(last_active_sensor)

        while True:
            elapsed_time = time.ticks_diff(time.ticks_ms(), start_time)
            if (state & (1 << pin)) == 0:
                log(f"Sensor {sensor} released before activation delay")
                return  # Якщо сенсор не натиснутий, виходимо з функції
            if elapsed_time >= sensor_activation_delay * 1000:
                break  # Виходимо з циклу, коли досягнута затримка активації
            await asyncio.sleep(0.01)  # Чекаємо 10 мс перед наступною перевіркою

        # Перевіряємо, чи сенсор все ще натиснутий після затримки
        try:
            state = i2c.readfrom(address, 1)[0]
            log(f"Sensor {sensor} state after delay: {state}")
        except OSError:
            log(f"Sensor {sensor} not responding, skipping")
            return  # Якщо сенсор не відповідає, виходимо з функції
        if (state & (1 << pin)) == 0:
            log(f"Sensor {sensor} released after activation delay")
            return

        sensor_settings = sensors[sensor]["settings"]

        if clamp_C_before_combination:
            # Затискаємо "C" перед комбінацією
            execute_action("C")
            await asyncio.sleep(0.3)  # Затримка 300мс
            # Відпускаємо "C" після затримки
            row, col = button_combinations["C"]
            Pin(pins[row]["number"], Pin.OUT).value(0)
            Pin(pins[col]["number"], Pin.OUT).value(0)
            await asyncio.sleep(delay_between_clicks)  # Пауза між "C" та комбінацією

        if sensor_settings[0] == "None":
            log("No action for setting 0")
        else:
            log(f"Executing action for setting 0: {sensor_settings[0]}")
            execute_action(sensor_settings[0])
        await asyncio.sleep(0.3)  # Затримка 300мс
        if sensor_settings[0] in button_combinations:
            row, col = button_combinations[sensor_settings[0]]
            Pin(pins[row]["number"], Pin.OUT).value(0)
            Pin(pins[col]["number"], Pin.OUT).value(0)
        await asyncio.sleep(delay_between_clicks)  # Використовуємо затримку між кліками з налаштувань
        if sensor_settings[1] == "None":
            log("No action for setting 1")
        else:
            log(f"Executing action for setting 1: {sensor_settings[1]}")
            execute_action(sensor_settings[1])
        await asyncio.sleep(0.3)  # Затримка 300мс
        if sensor_settings[1] in button_combinations:
            row, col = button_combinations[sensor_settings[1]]
            Pin(pins[row]["number"], Pin.OUT).value(0)
            Pin(pins[col]["number"], Pin.OUT).value(0)



# Функція для виконання дії, яка відповідає заданому налаштуванню
def execute_action(action):
    log(f"Executing action: {action}")
    if action != "None" and action in button_combinations:
        row, col = button_combinations[action]
        try:
            log(f"Setting high: {row} (Pin {pins[row]['number']}) and {col} (Pin {pins[col]['number']})")
            Pin(pins[row]["number"], Pin.OUT).value(1)
            Pin(pins[col]["number"], Pin.OUT).value(1)
        except ValueError as e:
            log(f"Error setting pin: {e}, row: {row}, col: {col}")
    else:
        log(f"Invalid or None action: {action}")

# Функція для постійного сканування I2C пристроїв
import time

# Змінні для відстеження стану пристроїв і часу останнього логування
prev_devices = set()
last_log_time = time.time()

# Функція для постійного сканування I2C пристроїв
async def scan_i2c():
    global devices, prev_devices, last_log_time
    while True:
        devices = set(i2c.scan())
        current_time = time.time()

        # Логувати, якщо відбулися зміни в пристроях
        if devices != prev_devices:
            print(f"[{get_timestamp()}] I2C scan complete. Devices found: {sorted(devices)}")
            prev_devices = devices
            last_log_time = current_time
        # Логувати раз на 3 секунди, якщо змін не було
        elif (current_time - last_log_time) >= 3:
            print(f"[{get_timestamp()}] I2C scan: No changes. Devices found: {sorted(devices)}")
            last_log_time = current_time

        await asyncio.sleep(1)

# Запуск сканування I2C
asyncio.create_task(scan_i2c())


# Змінні для відстеження стану сенсорів
prev_state = {}
pressed_sensors = {}
last_active_sensor = None

# Функція для скидання watchdog таймера
def reset_wdt(timer):
    log("Feeding watchdog timer")
    wdt.feed()

# Функція для калібрування сенсорів
def calibrate_sensors(timer):
    if settings.get("calibration_interval", False):
        log("Calibrating sensors")
        Pin(pins["I2C_POWER"]["number"], Pin.OUT).value(1)
        time.sleep(0.3)  # Затримка 300мс
        Pin(pins["I2C_POWER"]["number"], Pin.OUT).value(0)

# Таймер для калібрування сенсорів кожні 2 години
calibration_timer = Timer(-1)
calibration_timer.init(period=7200000, mode=Timer.PERIODIC, callback=calibrate_sensors)
log("Calibration timer initialized")

# Обробник таймера для таймауту безкоштовного режиму
def free_mode_timeout_handler(timer):
    log("Free mode timeout handler triggered")
    Pin(pins["FREE_MODE_CONTACT"]["number"], Pin.OUT).value(0)
    log("FREE_MODE_CONTACT deactivated")

clients = []

# Функція для надсилання подій сенсорів клієнту
async def send_sensor_event(event):
    name = event["name"]
    active = event["active"]

    log(f"Sending sensor event: {event}")

    for client in clients:
        try:
            data = f"data: {ujson.dumps({'name': name, 'active': active})}\n\n"
            await client.awrite(data)
        except Exception as e:
            log(f"Failed to send event: {e}")
            if client in clients:
                clients.remove(client)

# Обробник підключень SSE (Server-Sent Events)
async def sse_handler(reader, writer):
    global clients
    clients.append(writer)
    log("New SSE connection established")
    try:
        await writer.awrite("HTTP/1.1 200 OK\r\n")
        await writer.awrite("Content-Type: text/event-stream\r\n\r\n")
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        log("SSE connection closed")
        if writer in clients:
            clients.remove(writer)
        await writer.aclose()

# Функція для запуску точки доступу WiFi та HTTP-сервера
async def start_wifi_ap_and_server():
    global ap, server

    log("Starting WiFi AP and HTTP server")
    # Очищуємо пам'ять перед запуском точки доступу
    gc.collect()
    log("Memory collected before starting WiFi AP")

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="Necta Astro", authmode=network.AUTH_OPEN)
    ap.ifconfig(('192.168.1.1', '255.255.255.0', '192.168.1.1', '8.8.8.8'))
    log("WiFi Access Point 'Necta Astro' started")

    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    server = await asyncio.start_server(http_handler, addr[0], addr[1])
    log("HTTP server started")

    timeout = min(settings.get("access_point_deactivation_time", 10), 30) * 60000
    wifi_button_timer.init(period=timeout, mode=Timer.ONE_SHOT, callback=stop_wifi_ap_and_server)

    while True:
        await asyncio.sleep(3600)


# Функція для зупинки точки доступу WiFi та HTTP-сервера
def stop_wifi_ap_and_server(timer):
    global ap, server, wifi_active
    log("Stopping WiFi Access Point and server")
    ap.active(False)
    server.close()
    wifi_active = False
    log("WiFi Access Point and server stopped")

# Функція для активації піну
async def activate_pin(pin_name):
    log(f"Activating pin: {pin_name}")
    if pin_name in button_combinations:
        row, col = button_combinations[pin_name]
        try:
            log(f"Activating pin combination - row: {row}, col: {col}")
            Pin(pins[row]["number"], Pin.OUT).value(1)
            Pin(pins[col]["number"], Pin.OUT).value(1)
            log(f"Pin {pin_name} activated")
        except ValueError as e:
            log(f"Error activating pin: {e}")
    elif pin_name in pins:
        pin_number = pins[pin_name]["number"]
        try:
            log(f"Activating pin {pin_name} with pin number {pin_number}")
            pin = Pin(pin_number, Pin.OUT)
            pin.value(1)
            log(f"Pin {pin_name} state after activation: {pin.value()}")
        except ValueError as e:
            log(f"Error activating pin: {e}")
    else:
        log(f"Invalid pin name: {pin_name}")

# Функція для деактивації піну
async def deactivate_pin(pin_name):
    log(f"Deactivating pin: {pin_name}")
    if pin_name in button_combinations:
        row, col = button_combinations[pin_name]
        try:
            log(f"Deactivating pin combination - row: {row}, col: {col}")
            Pin(pins[row]["number"], Pin.OUT).value(0)
            Pin(pins[col]["number"], Pin.OUT).value(0)
            log(f"Pin {pin_name} deactivated")
        except ValueError as e:
            log(f"Error deactivating pin: {e}")
    elif pin_name in pins:
        pin_number = pins[pin_name]["number"]
        try:
            log(f"Deactivating pin {pin_name} with pin number {pin_number}")
            pin = Pin(pin_number, Pin.OUT)
            pin.value(0)
            log(f"Pin {pin_name} state after deactivation: {pin.value()}")
        except ValueError as e:
            log(f"Error deactivating pin: {e}")
    else:
        log(f"Invalid pin name: {pin_name}")

# Обробник HTTP запитів
async def http_handler(reader, writer):
    try:
        request_line = await reader.readline()
        request_line = request_line.decode()
        if request_line == '':
            return
        method, path, _ = request_line.split()
        log(f"HTTP request received: {method} {path}")

        while True:
            header = await reader.readline()
            if header == b'\r\n':
                break
            if header.startswith(b'Content-Length:'):
                content_length = int(header.split(b' ')[1].strip())

        if path == '/activate_pin' and method == 'POST':
            post_data = await reader.read(content_length)
            data = ujson.loads(post_data)
            log(f"Data received for activation: {data}")
            pin_name = data.get('pin')
            await activate_pin(pin_name)
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nPin activated"
            await writer.awrite(response)
        elif path == '/deactivate_pin' and method == 'POST':
            post_data = await reader.read(content_length)
            data = ujson.loads(post_data)
            log(f"Data received for deactivation: {data}")
            pin_name = data.get('pin')
            await deactivate_pin(pin_name)
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nPin deactivated"
            await writer.awrite(response)
        elif path == '/':
            await serve_file(writer, 'www/index.html', 'text/html')
        elif path == '/script.js':
            await serve_file(writer, 'www/script.js', 'application/javascript')
        elif path == '/styles.css':
            await serve_file(writer, 'www/styles.css', 'text/css')
        elif path == '/save_settings' and method == 'POST':
            post_data = await reader.read(content_length)
            new_settings = ujson.loads(post_data)
            
            # Перетворюємо відповідні значення з рядків на числа
            new_settings["delay_between_clicks"] = int(new_settings["delay_between_clicks"])
            new_settings["sensor_activation_delay"] = int(new_settings["sensor_activation_delay"])
            new_settings["free_mode_timeout"] = int(new_settings["free_mode_timeout"])
            new_settings["access_point_deactivation_time"] = int(new_settings["access_point_deactivation_time"])

            # Додаємо відсутні ключі pin і address
            for sensor in new_settings["sensors"]:
                new_settings["sensors"][sensor]["pin"] = sensors[sensor]["pin"]
                new_settings["sensors"][sensor]["address"] = sensors[sensor]["address"]

            settings.update(new_settings)
            save_settings()  # Зберігаємо налаштування у файл
            log(f"Settings updated: {new_settings}")
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\": \"success\"}"
            await writer.awrite(response)
            
            # Запускаємо перезавантаження контролера з затримкою
            asyncio.create_task(delayed_reset(1))  # Затримка 1 секунда перед перезавантаженням
        elif path == '/get_sensors':
            sensor_data = {
                "sensors": [{"name": name, "settings": sensor["settings"]} for name, sensor in sorted(sensors.items(), key=lambda x: int(x[0].replace('Sensor', '')))],
                "settings": {
                    "delay_between_clicks": settings["delay_between_clicks"],
                    "sensor_activation_delay": settings["sensor_activation_delay"],
                    "free_mode_timeout": settings["free_mode_timeout"],
                    "access_point_deactivation_time": settings["access_point_deactivation_time"],
                    "clamp_C_before_combination": settings["clamp_C_before_combination"],
                    "calibration_interval": settings["calibration_interval"]
                }
            }
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + ujson.dumps(sensor_data)
            await writer.awrite(response)
        elif path == '/sse':
            await sse_handler(reader, writer)
        else:
            response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found"
            await writer.awrite(response)
    except Exception as e:
        log(f"Exception in http_handler: {e}")
    finally:
        await writer.aclose()

# Функція для обслуговування файлів з веб-інтерфейсу
async def serve_file(writer, filepath, content_type):
    try:
        log(f"Serving file: {filepath}")
        with open(filepath, 'r') as f:
            content = f.read()
        response = "HTTP/1.1 200 OK\r\nContent-Type: {}\r\n\r\n{}".format(content_type, content)
        await writer.awrite(response)
    except OSError:
        log(f"File not found: {filepath}")
        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found"
        await writer.awrite(response)
    except Exception as e:
        log(f"Exception in serve_file: {e}")
    finally:
        await writer.aclose()

# Основний цикл програми
async def main_loop():
    global wdt, wifi_button_timer, wifi_active
    wdt = WDT(timeout=15000)
    free_mode_timer = Timer(-1)
    wifi_button_timer = Timer(-1)
    wifi_button_pressed_time = None
    wifi_active = False
    sensor_pressed_times = {}

    log("Entering main loop")

    while True:
        devices = i2c.scan()
        current_addresses = set(devices)
        log(f"Main loop I2C scan. Devices found: {current_addresses}")

        for address in list(prev_state.keys()):
            if address not in current_addresses:
                log(f"Device removed: {address}")
                del prev_state[address]

        for address in devices:
            try:
                state = i2c.readfrom(address, 1)[0]
                if address not in prev_state:
                    prev_state[address] = 0xFF
                for pin in range(8):
                    if (state & (1 << pin)) != 0 and (prev_state[address] & (1 << pin)) == 0:
                        sensor_name = None
                        for sensor, details in sensors.items():
                            if details["address"] == address and details["pin"] == pin:
                                sensor_name = sensor
                                break
                        if sensor_name:
                            log(f"Sensor pressed - Address: {address}, Pin: {pin}, Sensor: {sensor_name}")
                            if sensor_name not in pressed_sensors:
                                pressed_sensors[sensor_name] = True
                                sensor_pressed_times[sensor_name] = time.ticks_ms()
                                asyncio.create_task(handle_sensor_action(sensor_name))
                    elif (state & (1 << pin)) == 0 and (prev_state[address] & (1 << pin)) != 0:
                        log(f"Sensor released - Address: {address}, Pin: {pin}")
                        for sensor, details in sensors.items():
                            if details["address"] == address and details["pin"] == pin:
                                if sensor in pressed_sensors:
                                    del pressed_sensors[sensor]
                                if sensor in sensor_pressed_times:
                                    del sensor_pressed_times[sensor]
                prev_state[address] = state
            except OSError as e:
                log(f"Error reading from address {address}: {e}")
                if address in prev_state:
                    del prev_state[address]

        # Перевірка тривалості натискання сенсорів
        for sensor_name, press_time in sensor_pressed_times.items():
            if time.ticks_diff(time.ticks_ms(), press_time) >= 5000:  # 5000 мс = 5 секунд
                log(f"Sensor {sensor_name} pressed for 5 seconds, calibrating sensors")
                calibrate_sensors(None)
                del sensor_pressed_times[sensor_name]  # Уникнення повторної калібрування

        if Pin(pins["FREE_MODE_BUTTON"]["number"], Pin.IN, Pin.PULL_UP).value() == 0:
            log("Free mode button pressed")
            Pin(pins["FREE_MODE_CONTACT"]["number"], Pin.OUT).value(1)
            log("FREE_MODE_CONTACT activated")
            timeout = settings.get("free_mode_timeout", 1) * 60000
            free_mode_timer.init(period=timeout, mode=Timer.ONE_SHOT, callback=free_mode_timeout_handler)

        if Pin(pins["WIFI_BUTTON"]["number"], Pin.IN, Pin.PULL_UP).value() == 0:
            if wifi_button_pressed_time is None:
                wifi_button_pressed_time = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), wifi_button_pressed_time) >= 10000:
                log("WIFI_BUTTON held for 10 seconds, resetting settings")
                try:
                    os.remove('settings.json')
                except OSError:
                    pass
                reset()
        else:
            if wifi_button_pressed_time is not None:
                if time.ticks_diff(time.ticks_ms(), wifi_button_pressed_time) < 10000:
                    log("WIFI_BUTTON pressed")
                    if not wifi_active:
                        log("Activating WiFi Access Point")
                        asyncio.create_task(start_wifi_ap_and_server())
                        wifi_active = True
                wifi_button_pressed_time = None

        wdt.feed()
        await asyncio.sleep(0.1)

    log("Exiting main loop")

# Головна функція для запуску програми
async def main():
    log("Starting main function")
    await asyncio.gather(main_loop())

log("Starting asyncio event loop")
asyncio.run(main())
log("Event loop finished")



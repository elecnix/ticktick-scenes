from ticktick.oauth2 import OAuth2        # OAuth2 Manager
from ticktick.api import TickTickClient   # Main Interface
from urllib.parse import urlencode
import threading
import websocket
import requests
import syslog
import json
import os

def validate_config(config):
    if not config["homeassistant"]["token"]:
        msg = "Missing Home Assistant TOKEN"
        syslog.syslog(syslog.LOG_ERR, msg)
        raise Exception(msg)
    if not config["homeassistant"]["url"]:
        msg = "Missing Home Assistant URL"
        syslog.syslog(syslog.LOG_ERR, msg)
        raise Exception(msg)
    if not config["ticktick"]["oauth"]["id"]:
        msg = "Missing TickTick OAuth ID"
        syslog.syslog(syslog.LOG_ERR, msg)
        raise Exception(msg)
    if not config["ticktick"]["oauth"]["secret"]:
        msg = "Missing TickTick OAuth Secret"
        syslog.syslog(syslog.LOG_ERR, msg)
        raise Exception(msg)

with open(os.path.expanduser("~/.PomodoroHomeAssistant")) as f:
    config = json.load(f)
    validate_config(config)

    homeassistant_token = config["homeassistant"]["token"]
    homeassistant_url = config["homeassistant"]["url"]

    auth_client = OAuth2(config["ticktick"]["oauth"]["id"],
                        client_secret=config["ticktick"]["oauth"]["secret"],
                        redirect_uri="https://echo.free.beeceptor.com/")
    client = TickTickClient(config["ticktick"]["username"], config["ticktick"]["password"], auth_client)

# Define a mapping of TickTick 'op' events to Home Assistant entity_id values
ticktick_scenes = {
    "start": "scene.pomodoro_enabled",
    "pause": "scene.pomodoro_suspended",
    "continue": "scene.pomodoro_enabled",
    "startBreak": "scene.pomodoro_short_break",
    "endBreak": "scene.pomodoro_suspended",
    "drop": "scene.normal",
    "exit": "scene.normal",
}

homeassistant_scene_url = f"{homeassistant_url}/api/services/scene/turn_on"
homeassistant_headers = {
    "Authorization": f"Bearer {homeassistant_token}",
    "content-type": "application/json",
}

def set_scene(ticktick_op):
    if ticktick_op not in ticktick_scenes:
        msg = f"Unknown TickTick op: {ticktick_op}"
        print(msg)
        syslog.syslog(syslog.LOG_WARNING, msg)
        return

    data = {}
    data["entity_id"] = ticktick_scenes[ticktick_op]

    syslog.syslog(syslog.LOG_INFO, f"{ticktick_op} --> {data}\n")

    response = requests.post(homeassistant_scene_url, headers=homeassistant_headers, json=data)
    print(response.text)

def on_message(ws, message):
    print(f"Received message: {message}")
    parsed_message = json.loads(message)
    if 'data' in parsed_message:
        data = parsed_message['data']
        op = data['op']
        try:
            set_scene(op)
        except Exception as e:
            msg = f"Error setting scene: {e}"
            print(msg)
            syslog.syslog(syslog.LOG_ERR, msg)

def on_error(ws, error):
    print(f"An error occurred: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed.")

def on_open(ws):
    print("Connection opened.")
    send_ping()

params = {
    'x-device': TickTickClient.X_DEVICE_,
    'hl': 'en_US'
}
ws = websocket.WebSocketApp("wss://wssp.ticktick.com/web?" + urlencode(params),
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close,
                            on_open=on_open,
                            cookie='t=' + client.cookies['t'])

def send_ping():
    print("ping")
    ping = {
        "type": "ping"
    }
    ws.send(json.dumps(ping))
    threading.Timer(60, send_ping).start()

# Run the WebSocket
ws.run_forever()
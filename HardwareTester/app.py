"""Local Windows hardware tester. No hardware opens until requested in the panel."""
import argparse
import collections
import json
import math
import os
import queue
from pathlib import Path
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
EXTERNAL = Path(sys.executable).parent if getattr(sys, 'frozen', False) else ROOT
sys.path.insert(0, str(ROOT.parent / 'libraries/phidgets_lib'))
if os.name == 'nt' and (Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Phidgets/Phidget22').exists():
    DLL_DIR = os.add_dll_directory(str(Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Phidgets/Phidget22'))


class Hardware:
    def __init__(self, demo=False):
        self.config = json.loads((EXTERNAL / 'config.json' if (EXTERNAL / 'config.json').exists() else ROOT / 'config.json').read_text())
        self.lock = threading.RLock()
        self.demo = demo
        self.connected = False
        self.armed = False
        self.channels = {}
        self.values = {}
        self.logs = collections.deque(maxlen=150)
        self.events = queue.SimpleQueue()
        self.ports = []
        self.sample_time = time.monotonic()
        self.serial = None
        self.serial_port = ''
        self.server_added = False
        self.running = True
        self.started = time.monotonic()
        self.log('Ready. Hardware has not been opened.')
        threading.Thread(target=self.poll, daemon=True).start()
        threading.Thread(target=self.scan_ports, daemon=True).start()

    def log(self, message):
        self.logs.append(time.strftime('%H:%M:%S') + '  ' + str(message))

    def connect(self, settings):
        self.disconnect()
        self.demo = bool(settings.get('demo', False))
        serial_number = int(settings.get('serial_number', self.config['serial_number']))
        if serial_number < -1:
            raise ValueError('Serial number must be -1 or a positive number.')
        self.config['serial_number'] = serial_number
        if not self.demo:
            from Phidget22.Net import Net
            if settings.get('mode') == 'server':
                Net.addServer('NEAQ_Tester', settings.get('host', '127.0.0.1'), int(settings.get('port', 5661)), settings.get('password', ''), 0)
                self.server_added = True
        self.connected = True
        self.started = time.monotonic()
        for row in self.config['devices']:
            if row['enabled'] and row['type'] != 'DigitalOutput':
                self.open_channel(row)
        self.log('Demo connected.' if self.demo else 'Input channels opening. Waiting may indicate absent hardware or another app using it.')

    def open_channel(self, row):
        name = row['name']
        self.values[name] = dict(row, state='waiting', value=None, raw=None, detail='', model='')
        if self.demo:
            self.values[name]['state'] = 'demo'
            return
        try:
            import importlib
            cls = getattr(importlib.import_module('Phidget22.Devices.' + row['type']), row['type'])
            dev = cls()
            self.channels[name] = {'device': dev, 'row': row, 'ready': False, 'zero': 0}
            dev.setDeviceSerialNumber(self.config['serial_number'])
            dev.setHubPort(row['port'])
            dev.setChannel(row['channel'])
            dev.setIsHubPortDevice(row['hub_device'])
            dev.setIsRemote(self.server_added)
            if not self.server_added:
                dev.setIsLocal(True)
            dev.setOnErrorHandler(lambda d, code, message, n=name: self.events.put((n, f'{code}: {message}')))
            dev.open()
        except Exception as exc:
            self.channel_error(name, exc)

    def channel_error(self, name, error):
        with self.lock:
            if name in self.values:
                self.values[name].update(state='error', detail=str(error))
            self.log(f'{name}: {error}')

    def arm(self, enabled):
        if enabled and not self.connected:
            raise ValueError('Connect inputs first.')
        if not enabled:
            self.all_off()
            for name in list(self.channels):
                item = self.channels[name]
                if item['row']['type'] == 'DigitalOutput':
                    item['device'].close()
                    del self.channels[name]
            for row in self.config['devices']:
                if row['type'] == 'DigitalOutput':
                    self.values.pop(row['name'], None)
        elif not self.armed:
            for row in self.config['devices']:
                if row['enabled'] and row['type'] == 'DigitalOutput':
                    self.open_channel(row)
        self.armed = enabled
        self.log('Output testing enabled.' if enabled else 'Output testing disabled.')

    def output(self, name, value):
        if not self.armed:
            raise ValueError('Enable output testing first.')
        row = next((r for r in self.config['devices'] if r['name'] == name and r['type'] == 'DigitalOutput'), None)
        if not row or name not in self.values:
            raise ValueError('Unknown or disabled output.')
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Output must be between 0 and 1.')
        duty = 1 - value if row.get('invert') else value
        if not self.demo:
            item = self.channels[name]
            if not item['ready'] or not item['device'].getAttached():
                raise ValueError('Output not attached yet.')
            item['device'].setDutyCycle(duty)
        self.values[name].update(value=value, raw=duty)
        self.log(f'{name}: {value:.0%} (electrical duty {duty:.0%})')

    def all_off(self):
        for row in self.config['devices']:
            if row['type'] == 'DigitalOutput' and row['name'] in self.values and self.armed:
                try:
                    self.output(row['name'], 0)
                except Exception as exc:
                    self.log('Could not turn off ' + row['name'] + ': ' + str(exc))

    def disconnect(self):
        self.all_off()
        for item in self.channels.values():
            try:
                item['device'].close()
            except Exception as exc:
                self.log(exc)
        self.channels.clear()
        self.values.clear()
        self.connected = self.armed = False
        if self.server_added:
            from Phidget22.Net import Net
            Net.removeServer('NEAQ_Tester')
            self.server_added = False
        self.log('Phidgets disconnected.')

    def serial_connect(self, port):
        self.serial_close()
        if self.demo:
            self.serial_port = 'DEMO'
        else:
            import serial
            self.serial = serial.Serial(port=port, baudrate=115200, bytesize=8, parity='N', stopbits=2, timeout=0, write_timeout=1, rtscts=False, dsrdtr=False)
            self.serial.dtr = True
            self.serial.rts = False
            self.serial_port = port
        self.log('Teensy serial opened: ' + self.serial_port + '. Board/driver health is not yet verified.')

    def serial_close(self):
        if self.serial:
            self.serial.close()
        self.serial = None
        self.serial_port = ''

    def disconnect_all(self):
        self.disconnect()
        self.serial_close()

    def set_demo(self, enabled):
        self.disconnect_all()
        self.demo = bool(enabled)
        self.log('Demo mode selected.' if self.demo else 'Real hardware mode selected. Click Connect inputs when ready.')

    def buzz(self, effect):
        effect = int(effect)
        if not 1 <= effect <= 123:
            raise ValueError('Effect must be 1–123.')
        if not self.serial_port:
            raise ValueError('Open the Teensy port first.')
        if self.serial:
            self.serial.write(f'{effect}\n'.encode('ascii'))
        self.log(f'Teensy TX: {effect}\\n' + (' (demo)' if self.demo else ' — sent, physical response unverified'))

    def zero(self):
        for item in self.channels.values():
            if item['row']['type'] == 'Encoder' and item['ready']:
                item['zero'] = item['device'].getPosition()
        self.started = time.monotonic()
        self.log('Encoder zero set for this tester session.')

    def poll(self):
        while self.running:
            with self.lock:
                while not self.events.empty():
                    name, error = self.events.get_nowait()
                    self.channel_error(name, error)
                if self.connected and self.demo:
                    elapsed = time.monotonic() - self.started
                    for name, v in self.values.items():
                        if v['type'] == 'Encoder':
                            v.update(raw=int(elapsed * 100), value=int(elapsed * 15) % 360)
                        elif v['type'] == 'VoltageRatioInput':
                            raw = (math.sin(elapsed + v['channel']) + 1) / 2
                            v.update(raw=round(raw, 4), value=int(raw > v.get('threshold', .5)))
                        elif v['type'] == 'DigitalInput':
                            v['value'] = int(elapsed / (2 + v['channel'])) % 2
                        else:
                            v.setdefault('value', 0)
                            if v['value'] is None:
                                v.update(value=0, raw=0)
                for name, item in list(self.channels.items()):
                    d, row = item['device'], item['row']
                    try:
                        if not d.getAttached():
                            item['ready'] = False
                            self.values[name].update(state='waiting', value=None, raw=None)
                            continue
                        if not item['ready']:
                            if row['type'] == 'Encoder':
                                d.setEnabled(True)
                                d.setDataInterval(20)
                                item['zero'] = d.getPosition()
                            if row['type'] == 'VoltageRatioInput':
                                d.setDataInterval(20)
                            if row['type'] == 'DigitalOutput':
                                d.setDutyCycle(1 if row.get('invert') else 0)
                                self.values[name].update(value=0)
                            item['ready'] = True
                            self.log(name + ' attached: ' + d.getDeviceName())
                        v = self.values[name]
                        v.update(state='attached', detail='', model=d.getDeviceName(), serial=d.getDeviceSerialNumber())
                        if row['type'] == 'Encoder':
                            raw = d.getPosition() - item['zero']
                            v.update(raw=raw, value=math.floor(raw * 360 / self.config['ticks_per_revolution']) % 360)
                        elif row['type'] == 'VoltageRatioInput':
                            raw = d.getVoltageRatio()
                            v.update(raw=round(raw, 5), value=int(raw > row.get('threshold', .5)))
                        elif row['type'] == 'DigitalInput':
                            v['value'] = int(d.getState())
                        else:
                            v['raw'] = d.getDutyCycle()
                    except Exception as exc:
                        self.values[name].update(state='error', detail=str(exc), value=None, raw=None)
                if self.serial:
                    try:
                        if self.serial.in_waiting:
                            self.log('Teensy RX: ' + self.serial.read(min(self.serial.in_waiting, 4096)).decode('utf-8', 'replace'))
                    except Exception as exc:
                        self.log('Teensy disconnected: ' + str(exc))
                        self.serial_close()
                self.sample_time = time.monotonic()
            time.sleep(.02)

    def scan_ports(self):
        import serial.tools.list_ports
        while self.running:
            try:
                ports = [{'port': p.device, 'description': p.description} for p in serial.tools.list_ports.comports()]
                with self.lock:
                    self.ports = ports
            except Exception as exc:
                self.log('Serial port scan: ' + str(exc))
            for _ in range(30):
                if not self.running:
                    return
                time.sleep(.1)

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps({'demo': self.demo, 'connected': self.connected, 'armed': self.armed, 'values': self.values, 'config': self.config, 'serial_port': self.serial_port, 'ports': self.ports, 'sample_age_ms': round((time.monotonic() - self.sample_time) * 1000, 1), 'logs': list(self.logs)}))


def serve(demo=False, browser=True, port=0, url_file=None):
    hw = Hardware(demo)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        disable_nagle_algorithm = True
        def log_message(self, *args):
            pass

        def respond(self, value, status=200):
            data = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            return secrets.compare_digest(self.headers.get('X-Tester-Token', ''), token)

        def do_GET(self):
            if self.path == '/':
                data = (ROOT / 'panel.html').read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(data)
            elif self.path == '/api/state' and self.authorized():
                self.respond(hw.snapshot())
            else:
                self.respond({'error': 'Not found or unauthorized'}, 403)

        def do_POST(self):
            if not self.authorized():
                self.respond({'error': 'Unauthorized'}, 403)
                return
            try:
                size = int(self.headers.get('Content-Length', 0))
                if size > 10000:
                    raise ValueError('Request too large')
                body = json.loads(self.rfile.read(size))
                with hw.lock:
                    if self.path == '/api/connect': hw.connect(body)
                    elif self.path == '/api/disconnect': hw.disconnect_all()
                    elif self.path == '/api/mode': hw.set_demo(body['demo'])
                    elif self.path == '/api/arm': hw.arm(bool(body['enabled']))
                    elif self.path == '/api/output': hw.output(body['name'], body['value'])
                    elif self.path == '/api/off': hw.all_off()
                    elif self.path == '/api/zero': hw.zero()
                    elif self.path == '/api/serial':
                        if not hw.connected:
                            hw.demo = bool(body.get('demo', hw.demo))
                        hw.serial_connect(body['port'])
                    elif self.path == '/api/serial-close': hw.serial_close()
                    elif self.path == '/api/buzz': hw.buzz(body['effect'])
                    elif self.path == '/api/quit':
                        hw.disconnect()
                        hw.serial_close()
                        threading.Thread(target=server.shutdown, daemon=True).start()
                    else: raise ValueError('Unknown action')
                self.respond({'ok': True})
            except Exception as exc:
                hw.log('Action failed: ' + str(exc))
                self.respond({'error': str(exc)}, 400)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    url = f'http://127.0.0.1:{server.server_port}/#{token}'
    if url_file:
        Path(url_file).write_text(url)
    if browser:
        webbrowser.open(url)
    elif not getattr(sys, 'frozen', False):
        print(url, flush=True)
    try:
        server.serve_forever()
    finally:
        with hw.lock:
            hw.running = False
            hw.disconnect()
            hw.serial_close()
        server.server_close()


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--demo', action='store_true')
    args.add_argument('--no-browser', action='store_true')
    args.add_argument('--port', type=int, default=0)
    args.add_argument('--url-file')
    options = args.parse_args()
    serve(options.demo, not options.no_browser, options.port, options.url_file)

NEAQ HARDWARE TESTER

Launch NEAQ Hardware Tester.exe. It opens a local panel in your default browser.
The executable contains the runtime; Python, Node and Electron are not needed.
Install the official Phidget22 x64 Windows driver on the installation computer.
No hardware is opened or driven at launch. No TouchDesigner file is changed.

QUICK TEST
1. Release hardware in TouchDesigner / Node-RED / other controllers before
   direct testing. This tester never changes their configuration.
2. Check hub serial and select Direct USB or Phidget Network Server.
3. Connect inputs. Turn the encoder and press/touch each sensor.
4. Use the Box and VU light switches. The first switch opens output testing.
5. Open the Teensy COM port and press Play effect (default 70).
6. Save report to export connection states, live values and activity.
7. Use Exit tester when finished. Closing only the browser tab leaves the
   tester running. Exit attempts to turn lights off before closing channels.
   Unplugged hardware cannot be commanded off; check the physical installation.

DEMO
Expand Connection settings & mapping and select Demo mode before connecting inputs. Everything is simulated, including
light commands and Teensy serial. The badge clearly identifies demo mode.

CONFIGURATION
config.json next to the executable overrides the embedded defaults. Restart
after changes. Serial -1 matches any hub; explicit serial is preferable.
Default installation touch mapping: left 4/0, right 4/1, center 4/2.
All three use the TD left sensor's VoltageRatioInput / hub-port mode by default.
The physical module must support the requested channel numbers; otherwise
they remain waiting. If the right/center sensors use a VINT module, set its
actual port/channel and hub_device false. Confirm the wiring/module models.
Console 2 language channel 2/2 is included as a testable input, although it was
disabled in the scanned TD project. Disable its row if not installed.
VU output defaults to port 3 from the active project; older notes said port 5.
Output invert false follows the actual TD configuration. Set invert true for
active-low light wiring; the panel shows logical brightness and electrical duty.

TEENSY
COM3 default, 115200 baud, 8 data bits, no parity, 2 stop bits; DTR on, RTS off.
Commands are ASCII effect numbers followed by LF, matching TouchDesigner.
Effects 1–123 are selectable from the embedded DRV2605 reference list.
There is no verified firmware acknowledgement/stop protocol. Port open and
command sent do not prove the board, I2C driver or actuator is functional.
An installer must confirm physical vibration. Firmware/model remains needed
to implement deeper automated haptic diagnostics.

SOURCE / BUILD
app.py provides the local hardware service; panel.html is the JavaScript UI.
Install pyserial, pyinstaller and Phidget22 to build from source.
The supplied Windows binary bundles Phidget22 Python bindings. The official
native driver remains a prerequisite. The bindings' license is included.
Local service binds only 127.0.0.1 on an automatically chosen port and requires
a per-launch token for API requests. Nothing is sent to an external service.

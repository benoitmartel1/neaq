"""Hardware safety and demo behavior without opening physical devices."""
import unittest
from app import Hardware


class TesterTests(unittest.TestCase):
    def setUp(self):
        self.hw = Hardware(True)
        self.hw.running = False

    def tearDown(self):
        self.hw.disconnect()
        self.hw.serial_close()

    def test_startup_opens_no_hardware(self):
        self.assertFalse(self.hw.connected)
        self.assertFalse(self.hw.armed)
        self.assertEqual(self.hw.channels, {})
        with self.assertRaises(ValueError):
            self.hw.output('box', 1)

    def test_mapping(self):
        rows = {r['name']: r for r in self.hw.config['devices']}
        self.assertEqual([(rows[n]['port'], rows[n]['channel']) for n in ['left', 'right', 'center']], [(4, 0), (4, 1), (4, 2)])

    def test_output_enable_off_and_disconnect(self):
        self.hw.connect({'demo': True})
        self.assertNotIn('box', self.hw.values)
        self.hw.arm(True)
        self.hw.output('box', 1)
        self.hw.output('vu', .5)
        self.assertEqual(self.hw.values['box']['value'], 1)
        self.hw.all_off()
        self.assertEqual(self.hw.values['box']['value'], 0)
        self.assertEqual(self.hw.values['vu']['value'], 0)
        self.hw.arm(False)
        with self.assertRaises(ValueError):
            self.hw.output('box', 1)
        self.hw.disconnect()
        self.assertFalse(self.hw.armed)

    def test_active_low_and_invalid_duty(self):
        self.hw.connect({'demo': True})
        next(r for r in self.hw.config['devices'] if r['name'] == 'box')['invert'] = True
        self.hw.arm(True)
        self.hw.output('box', 0)
        self.assertEqual(self.hw.values['box']['raw'], 1)
        for v in [-1, 2, float('nan')]:
            with self.assertRaises(ValueError):
                self.hw.output('box', v)

    def test_haptic_protocol_and_bounds(self):
        class SerialStub:
            sent = None
            def write(self, value): self.sent = value
            def close(self): pass
        stub = SerialStub()
        self.hw.serial = stub
        self.hw.serial_port = 'TEST'
        self.hw.buzz(70)
        self.assertEqual(stub.sent, b'70\n')
        for effect in [0, 124]:
            with self.assertRaises(ValueError): self.hw.buzz(effect)

    def test_mode_switch_releases_both_connections(self):
        self.hw.connect({'demo': True})
        self.hw.arm(True)
        self.hw.serial_connect('DEMO')
        self.hw.set_demo(False)
        self.assertFalse(self.hw.demo)
        self.assertFalse(self.hw.connected)
        self.assertFalse(self.hw.armed)
        self.assertEqual(self.hw.serial_port, '')
        self.assertEqual(self.hw.channels, {})


if __name__ == '__main__':
    unittest.main()

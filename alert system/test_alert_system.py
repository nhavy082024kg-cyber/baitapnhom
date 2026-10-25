import unittest
from alert_system import AlertEngine

class AlertTests(unittest.TestCase):
    def test_deduplicate_and_resolve(self):
        engine = AlertEngine()
        data = {'tenant_id':'a','machine_id':'m','slots':[{'slot_id':1,'remaining_percent':9}]}
        engine.process_telemetry(data)
        engine.process_telemetry(data)
        alerts = engine.list_alerts('a')
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['occurrences'], 2)
        engine.update_status('a','m','LOW_STOCK','1','RESOLVED','operator')
        self.assertEqual(engine.list_alerts('a')[0]['status'], 'RESOLVED')

    def test_tenant_isolation(self):
        engine = AlertEngine()
        engine.process_telemetry({'tenant_id':'a','machine_id':'m','online':False})
        self.assertEqual(engine.list_alerts('b'), [])

    def test_sensor_and_empty(self):
        engine = AlertEngine()
        engine.process_telemetry({'tenant_id':'a','machine_id':'m','slots':[
            {'slot_id':1,'remaining_percent':0,'sensor_error':True}]})
        self.assertEqual({a['code'] for a in engine.list_alerts('a')}, {'EMPTY_SLOT','SENSOR_FAILURE'})

if __name__ == '__main__':
    unittest.main()

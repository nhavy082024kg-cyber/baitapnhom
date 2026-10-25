"""ScentStation TP3 P5: alert engine independent of MQTT transport.
Call process_telemetry for validated device payloads from TP3 P1/P2.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json

SEVERITY = {'OFFLINE':'critical','LOW_STOCK':'warning','EMPTY_SLOT':'critical',
            'DOOR_OPEN':'warning','LEAK_SUSPECTED':'critical',
            'SENSOR_FAILURE':'critical','ACTUATOR_FAILURE':'critical',
            'DISPENSE_FAILURE':'warning'}

@dataclass
class Alert:
    tenant_id: str
    machine_id: str
    code: str
    slot_id: str | None
    severity: str
    status: str = 'OPEN'
    occurrences: int = 1
    first_seen: str = ''
    last_seen: str = ''
    acknowledged_by: str | None = None
    resolved_by: str | None = None

class AlertEngine:
    def __init__(self, low_stock_threshold=15):
        self.alerts = {}  # prototype memory store; replace with tenant-scoped DB
        self.low_stock_threshold = low_stock_threshold

    def _key(self, tenant_id, machine_id, code, slot_id):
        return (tenant_id, machine_id, code, slot_id)

    def raise_alert(self, tenant_id, machine_id, code, slot_id=None):
        if code not in SEVERITY:
            raise ValueError('Unknown alert code')
        now = datetime.now(timezone.utc).isoformat()
        key = self._key(tenant_id, machine_id, code, slot_id)
        existing = self.alerts.get(key)
        if existing and existing.status != 'RESOLVED':
            existing.occurrences += 1
            existing.last_seen = now
            return existing
        alert = Alert(tenant_id, machine_id, code, slot_id, SEVERITY[code],
                      first_seen=now, last_seen=now)
        self.alerts[key] = alert
        return alert

    def process_telemetry(self, payload):
        """Expected tenant_id, machine_id, slots[]; source must authenticate device.
        A heartbeat timeout is determined externally and passed as online=False.
        """
        tenant = payload['tenant_id']
        machine = payload['machine_id']
        if not tenant or not machine:
            raise ValueError('Missing device identity')
        raised = []
        def add(code, slot=None):
            raised.append(self.raise_alert(tenant, machine, code, slot))
        if payload.get('online') is False:
            add('OFFLINE')
        if payload.get('door_open') is True:
            add('DOOR_OPEN')
        if payload.get('leak_suspected') is True:
            add('LEAK_SUSPECTED')
        for slot in payload.get('slots', []):
            sid = str(slot['slot_id'])
            remaining = slot.get('remaining_percent')
            if remaining is not None:
                if not isinstance(remaining, (int, float)) or not 0 <= remaining <= 100:
                    raise ValueError('Invalid remaining_percent')
                if remaining == 0:
                    add('EMPTY_SLOT', sid)
                elif remaining < self.low_stock_threshold:
                    add('LOW_STOCK', sid)
            if slot.get('sensor_error') is True:
                add('SENSOR_FAILURE', sid)
            if slot.get('actuator_error') is True:
                add('ACTUATOR_FAILURE', sid)
            if slot.get('dispense_failed') is True:
                add('DISPENSE_FAILURE', sid)
        return raised

    def update_status(self, tenant_id, machine_id, code, slot_id, status, actor):
        if status not in ('ACKNOWLEDGED', 'RESOLVED', 'OPEN'):
            raise ValueError('Invalid status')
        if not actor:
            raise ValueError('Actor required')
        key = self._key(tenant_id, machine_id, code, slot_id)
        alert = self.alerts[key]
        if status == 'ACKNOWLEDGED':
            alert.acknowledged_by = actor
        if status == 'RESOLVED':
            alert.resolved_by = actor
        alert.status = status
        return alert

    def list_alerts(self, tenant_id):
        return [asdict(a) for a in self.alerts.values() if a.tenant_id == tenant_id]

if __name__ == '__main__':
    engine = AlertEngine()
    sample = {'tenant_id':'brand_a','machine_id':'kiosk_01','online':True,
              'door_open':False,'slots':[{'slot_id':1,'remaining_percent':10},
                                         {'slot_id':2,'remaining_percent':0},
                                         {'slot_id':3,'sensor_error':True},
                                         {'slot_id':4,'remaining_percent':75}]}
    engine.process_telemetry(sample)
    print(json.dumps(engine.list_alerts('brand_a'), ensure_ascii=False, indent=2))

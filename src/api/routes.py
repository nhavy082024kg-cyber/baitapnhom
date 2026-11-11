from api.controllers.auth_controller import auth_bp
from api.controllers.catalog_controller import location_bp, product_bp
from api.controllers.device_controller import device_bp
from api.controllers.inventory_controller import inventory_bp
from api.controllers.kiosk_controller import kiosk_bp
from api.controllers.machine_controller import machine_bp, slot_bp
from api.controllers.order_controller import order_bp
from api.controllers.payment_webhook_controller import webhook_bp
from api.controllers.system_controller import system_bp
from api.controllers.tenant_controller import tenant_bp, user_bp


def register_routes(app):
    """Every new controller = one more line here."""
    for blueprint in (auth_bp, tenant_bp, user_bp, product_bp, location_bp, machine_bp, slot_bp,
                      inventory_bp, order_bp, kiosk_bp, device_bp, webhook_bp, system_bp):
        app.register_blueprint(blueprint)

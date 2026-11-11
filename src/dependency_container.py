# Dependency Injection container: the ONLY place that knows which concrete class implements which interface.
# Controllers ask the container for a service:  container.order_service().create_order(...)
# To swap MySQL for another DB or the mock payment provider for a real one, change it here.

from dependency_injector import containers, providers

from config import FactoryConfig
from infrastructure.databases import get_database
from infrastructure.databases.unit_of_work import SqlAlchemyUnitOfWork
from infrastructure.repositories.alert_audit_repository import AlertRepository, AuditRepository
from infrastructure.repositories.catalog_repository import LocationRepository, ProductRepository
from infrastructure.repositories.dispense_repository import DeviceDataRepository, DispenseCommandRepository
from infrastructure.repositories.inventory_repository import InventoryRepository
from infrastructure.repositories.machine_repository import MachineRepository, SlotRepository
from infrastructure.repositories.order_repository import (OrderRepository, PaymentRepository, RefundRepository,
                                                          WebhookEventRepository)
from infrastructure.repositories.user_repository import SessionRepository, TenantRepository, UserRepository
from infrastructure.services.payment_provider_service import MockPaymentProvider
from infrastructure.services.security_service import DeviceSecurity, PasswordHasher, TokenService
from services.alert_service import AlertService
from services.audit_service import AuditService
from services.auth_service import AuthService
from services.catalog_service import LocationService, ProductService
from services.dispensing_service import DispensingService
from services.inventory_service import InventoryService
from services.machine_service import MachineService
from services.order_service import OrderService
from services.order_workflow import OrderWorkflow
from services.payment_service import PaymentService
from services.tenant_service import TenantService
from services.user_service import UserService

_cfg = FactoryConfig.get_config()


def _session_of(database):
    return database.session            # scoped_session: one per request/thread


class Container(containers.DeclarativeContainer):
    settings = providers.Object(_cfg.service_settings())

    # ---- infrastructure -----------------------------------------------------------------------
    database = providers.Singleton(get_database)
    session = providers.Callable(_session_of, database)
    uow = providers.Factory(SqlAlchemyUnitOfWork, session=session)

    hasher = providers.Singleton(PasswordHasher)
    tokens = providers.Singleton(TokenService, secret_key=_cfg.SECRET_KEY)
    devices = providers.Singleton(DeviceSecurity, master_key=_cfg.DEVICE_MASTER_KEY)
    payment_provider = providers.Singleton(MockPaymentProvider, webhook_secret=_cfg.PAYMENT_WEBHOOK_SECRET)

    # ---- repositories (all share the request's session) ----------------------------------------
    tenant_repository = providers.Factory(TenantRepository, session=session)
    user_repository = providers.Factory(UserRepository, session=session)
    session_repository = providers.Factory(SessionRepository, session=session)
    product_repository = providers.Factory(ProductRepository, session=session)
    location_repository = providers.Factory(LocationRepository, session=session)
    machine_repository = providers.Factory(MachineRepository, session=session)
    slot_repository = providers.Factory(SlotRepository, session=session)
    inventory_repository = providers.Factory(InventoryRepository, session=session)
    order_repository = providers.Factory(OrderRepository, session=session)
    payment_repository = providers.Factory(PaymentRepository, session=session)
    webhook_repository = providers.Factory(WebhookEventRepository, session=session)
    refund_repository = providers.Factory(RefundRepository, session=session)
    command_repository = providers.Factory(DispenseCommandRepository, session=session)
    device_data_repository = providers.Factory(DeviceDataRepository, session=session)
    alert_repository = providers.Factory(AlertRepository, session=session)
    audit_repository = providers.Factory(AuditRepository, session=session)

    # ---- services ------------------------------------------------------------------------------
    audit_service = providers.Factory(AuditService, repository=audit_repository)
    alert_service = providers.Factory(AlertService, alerts=alert_repository, machines=machine_repository, uow=uow)
    order_workflow = providers.Factory(OrderWorkflow, orders=order_repository)

    auth_service = providers.Factory(
        AuthService, users=user_repository, sessions=session_repository, tenants=tenant_repository,
        hasher=hasher, tokens=tokens, audit=audit_service, uow=uow, settings=settings)
    tenant_service = providers.Factory(
        TenantService, tenants=tenant_repository, users=user_repository, sessions=session_repository,
        audit=audit_service, uow=uow)
    user_service = providers.Factory(
        UserService, users=user_repository, sessions=session_repository, tenants=tenant_repository,
        hasher=hasher, audit=audit_service, uow=uow)
    product_service = providers.Factory(ProductService, products=product_repository, audit=audit_service, uow=uow)
    location_service = providers.Factory(LocationService, locations=location_repository, audit=audit_service, uow=uow)
    machine_service = providers.Factory(
        MachineService, machines=machine_repository, slots=slot_repository, products=product_repository,
        locations=location_repository, device_data=device_data_repository, devices=devices, alerts=alert_service,
        audit=audit_service, uow=uow, settings=settings)
    inventory_service = providers.Factory(
        InventoryService, inventory=inventory_repository, slots=slot_repository, products=product_repository,
        alerts=alert_service, audit=audit_service, uow=uow)
    dispensing_service = providers.Factory(
        DispensingService, commands=command_repository, orders=order_repository, slots=slot_repository,
        machines=machine_repository, devices=devices, inventory=inventory_service, alerts=alert_service,
        workflow=order_workflow, audit=audit_service, uow=uow, settings=settings)
    order_service = providers.Factory(
        OrderService, orders=order_repository, payments=payment_repository, slots=slot_repository,
        products=product_repository, machines=machine_repository, refunds=refund_repository,
        commands=command_repository, provider=payment_provider, workflow=order_workflow, audit=audit_service,
        uow=uow, settings=settings)
    payment_service = providers.Factory(
        PaymentService, payments=payment_repository, orders=order_repository, webhooks=webhook_repository,
        provider=payment_provider, workflow=order_workflow, dispensing=dispensing_service, audit=audit_service,
        uow=uow)


container = Container()

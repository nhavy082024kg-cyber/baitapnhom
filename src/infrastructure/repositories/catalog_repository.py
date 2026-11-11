from domain.models.catalog import Location, Product
from domain.models.irepositories import ILocationRepository, IProductRepository
from infrastructure.models.catalog_models import LocationModel, ProductModel
from infrastructure.repositories.base_repository import SqlRepository


class ProductRepository(SqlRepository, IProductRepository):
    model, entity = ProductModel, Product

    def add(self, product): return self._add(product)
    def get(self, tenant_id, product_id): return self._first(tenant_id=tenant_id, id=product_id)   # tenant filter!
    def list(self, tenant_id): return self._all(tenant_id=tenant_id)
    def update(self, product): return self._save(product)


class LocationRepository(SqlRepository, ILocationRepository):
    model, entity = LocationModel, Location

    def add(self, location): return self._add(location)
    def get(self, tenant_id, location_id): return self._first(tenant_id=tenant_id, id=location_id)
    def list(self, tenant_id): return self._all(tenant_id=tenant_id)

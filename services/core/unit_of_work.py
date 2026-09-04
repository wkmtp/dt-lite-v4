"""Unit of Work - Transaction boundary management.

Controls commit/rollback at service layer. Repositories only flush.
"""
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from services.core.repositories.asset_repository import AssetRepository
from services.core.repositories.entity_repository import EntityRepository
from services.core.repositories.property_repository import PropertyRepository
from services.core.repositories.relationship_repository import RelationshipRepository
from services.identity.repositories.permission_repository import PermissionRepository
from services.iota.repositories.binding_repository import DeviceEntityBindingRepository
from services.iota.repositories.connection_repository import ConnectionRepository
from services.iota.repositories.data_point_repository import DataPointRepository
from services.iota.repositories.data_source_repository import DataSourceRepository
from services.iota.repositories.device_repository import DeviceRepository


class UnitOfWork:
    """Manages database transactions for a single business operation."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._entities: Optional[EntityRepository] = None
        self._assets: Optional[AssetRepository] = None
        self._properties: Optional[PropertyRepository] = None
        self._relationships: Optional[RelationshipRepository] = None
        self._permissions: Optional[PermissionRepository] = None
        self._data_sources: Optional[DataSourceRepository] = None
        self._connections: Optional[ConnectionRepository] = None
        self._devices: Optional[DeviceRepository] = None
        self._data_points: Optional[DataPointRepository] = None
        self._bindings: Optional[DeviceEntityBindingRepository] = None
        self._committed = False
        self._rolled_back = False

    @property
    def entities(self) -> EntityRepository:
        if self._entities is None:
            self._entities = EntityRepository(self._session)
        return self._entities

    @property
    def assets(self) -> AssetRepository:
        if self._assets is None:
            self._assets = AssetRepository(self._session)
        return self._assets

    @property
    def properties(self) -> PropertyRepository:
        if self._properties is None:
            self._properties = PropertyRepository(self._session)
        return self._properties

    @property
    def relationships(self) -> RelationshipRepository:
        if self._relationships is None:
            self._relationships = RelationshipRepository(self._session)
        return self._relationships

    @property
    def permissions(self) -> PermissionRepository:
        if self._permissions is None:
            self._permissions = PermissionRepository(self._session)
        return self._permissions

    @property
    def data_sources(self) -> DataSourceRepository:
        if self._data_sources is None:
            self._data_sources = DataSourceRepository(self._session)
        return self._data_sources

    @property
    def connections(self) -> ConnectionRepository:
        if self._connections is None:
            self._connections = ConnectionRepository(self._session)
        return self._connections

    @property
    def devices(self) -> DeviceRepository:
        if self._devices is None:
            self._devices = DeviceRepository(self._session)
        return self._devices

    @property
    def data_points(self) -> DataPointRepository:
        if self._data_points is None:
            self._data_points = DataPointRepository(self._session)
        return self._data_points

    @property
    def bindings(self) -> DeviceEntityBindingRepository:
        if self._bindings is None:
            self._bindings = DeviceEntityBindingRepository(self._session)
        return self._bindings

    @property
    def session(self):
        """Expose session for services that need direct access."""
        return self._session

    async def commit(self) -> None:
        """Commit the transaction."""
        if not self._committed and not self._rolled_back:
            await self._session.commit()
            self._committed = True

    async def rollback(self) -> None:
        """Rollback the transaction."""
        if not self._committed and not self._rolled_back:
            await self._session.rollback()
            self._rolled_back = True

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

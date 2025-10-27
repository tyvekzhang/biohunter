from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Generic, Optional, TypeVar

T = TypeVar("T")


class BaseStorage(ABC, Generic[T]):
    """Abstract storage interface supporting generic data types"""

    @abstractmethod
    async def store(self, entity_id: str, entity: T) -> str:
        """Store an entity"""
        pass

    @abstractmethod
    async def get(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        pass

    @abstractmethod
    async def update(self, entity_id: str, **updated) -> Optional[T]:
        """Update entity"""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity"""
        pass

    @abstractmethod
    async def list(self) -> list[T]:
        """List all entities"""
        pass


class MemoryStorage(BaseStorage[T]):
    """In-memory storage implementation"""

    def __init__(self):
        self._data: Dict[str, T] = {}

    async def store(self, entity_id: str, entity: T) -> str:
        self.store_sync(entity_id, entity)
        return entity_id

    def store_sync(self, entity_id: str, entity: T) -> str:
        self._data[entity_id] = entity
        return entity_id

    async def get(self, entity_id: str) -> Optional[T]:
        return self._data.get(entity_id)

    def get_sync(self, entity_id: str) -> Optional[T]:
        return self._data.get(entity_id)

    async def update(self, entity_id: str, **updated) -> Optional[T]:
        if entity_id not in self._data:
            return None

        entity = self._data[entity_id]
        for key, value in updated.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        return entity

    async def delete(self, entity_id: str) -> bool:
        if entity_id in self._data:
            del self._data[entity_id]
            return True
        return False

    async def list(self) -> list[T]:
        return list(self._data.values())
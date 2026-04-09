"""Base repository with common CRUD operations using SQLAlchemy 2.0 async."""
from typing import TypeVar, Type, Optional, List, Generic, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


# Generic type for model classes
ModelType = TypeVar('ModelType', bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing common CRUD operations.

    This class implements the Repository pattern for data access,
    using SQLAlchemy 2.0 async sessions and typed models.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        """
        Initialize repository with session and model.

        Args:
            session: SQLAlchemy async session
            model: SQLAlchemy ORM model class
        """
        self.session: AsyncSession = session
        self.model: Type[ModelType] = model

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        Get all records with pagination.

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return
            order_by: Column name to order by (e.g., 'created_at DESC')

        Returns:
            List of model instances
        """
        stmt = select(self.model)

        # Apply ordering if specified
        if order_by:
            # Parse order_by string (e.g., 'created_at DESC')
            parts = order_by.split()
            column_name = parts[0]
            desc = len(parts) > 1 and parts[1].upper() == 'DESC'

            if hasattr(self.model, column_name):
                column = getattr(self.model, column_name)
                stmt = stmt.order_by(column.desc() if desc else column.asc())

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        # Set created_at if model has it
        if hasattr(self.model, 'created_at') and 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.now(timezone.utc)

        # Set updated_at if model has it
        if hasattr(self.model, 'updated_at') and 'updated_at' not in kwargs:
            kwargs['updated_at'] = datetime.now(timezone.utc)

        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """
        Update a record by ID.

        Args:
            id: Primary key value
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        # Update the updated_at timestamp if model has it
        if hasattr(self.model, 'updated_at'):
            kwargs['updated_at'] = datetime.now(timezone.utc)

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, id: Any) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        List records with optional filtering.

        Args:
            filters: Dictionary of field:value pairs to filter by
            offset: Number of records to skip
            limit: Maximum number of records to return
            order_by: Column name to order by

        Returns:
            List of model instances matching filters
        """
        stmt = select(self.model)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)

        # Apply ordering
        if order_by:
            parts = order_by.split()
            column_name = parts[0]
            desc = len(parts) > 1 and parts[1].upper() == 'DESC'

            if hasattr(self.model, column_name):
                column = getattr(self.model, column_name)
                stmt = stmt.order_by(column.desc() if desc else column.asc())

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters.

        Args:
            filters: Dictionary of field:value pairs to filter by

        Returns:
            Number of matching records
        """
        stmt = select(func.count()).select_from(self.model)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, id: Any) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if exists, False otherwise
        """
        stmt = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """
        Get a single record by a specific field value.

        Args:
            field_name: Name of the field to query
            value: Value to match

        Returns:
            Model instance or None if not found
        """
        if not hasattr(self.model, field_name):
            raise ValueError(f"Model {self.model.__name__} has no field '{field_name}'")

        stmt = select(self.model).where(getattr(self.model, field_name) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, filters: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> tuple[ModelType, bool]:
        """
        Get a record matching filters, or create it if it doesn't exist.

        Args:
            filters: Fields to match
            defaults: Default values for creation if not found

        Returns:
            Tuple of (model instance, created: bool)
        """
        # Try to find existing record
        instance = await self.get_by_field(list(filters.keys())[0], list(filters.values())[0])

        if instance:
            return instance, False

        # Create new record
        create_data = {**filters, **(defaults or {})}
        instance = await self.create(**create_data)
        return instance, True

    async def bulk_create(self, items_data: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk.

        Args:
            items_data: List of dictionaries with field values

        Returns:
            List of created model instances
        """
        instances = []

        # Set timestamps if model has them
        now = datetime.now(timezone.utc)
        for data in items_data:
            if hasattr(self.model, 'created_at') and 'created_at' not in data:
                data['created_at'] = now
            if hasattr(self.model, 'updated_at') and 'updated_at' not in data:
                data['updated_at'] = now

            instances.append(self.model(**data))

        self.session.add_all(instances)
        await self.session.flush()

        return instances

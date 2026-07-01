from uuid import UUID

from sqlalchemy import select

from src.domain.entities.state_metadata.models import StateMetadataModel
from src.infrastructure.dbs.postgres.engine import get_db_session
from src.infrastructure.dbs.postgres.state_metadata.dbes import StateMetadataDBE


class StateMetadataDAO:
    def _map_dbe_to_model(self, dbe: StateMetadataDBE) -> StateMetadataModel:
        return StateMetadataModel(
            execution_id=UUID(str(dbe.execution_id)),  # type: ignore
            compression_algorithm=dbe.compression_algorithm,  # type: ignore
            original_size_bytes=dbe.original_size_bytes,  # type: ignore
            compressed_size_bytes=dbe.compressed_size_bytes,  # type: ignore
            schema_version=dbe.schema_version or 1,  # type: ignore
            created_at=dbe.created_at,  # type: ignore
        )

    async def upsert(self, model: StateMetadataModel) -> StateMetadataModel:
        async with get_db_session() as session:
            dbe = StateMetadataDBE(
                execution_id=model.execution_id,
                compression_algorithm=model.compression_algorithm,
                original_size_bytes=model.original_size_bytes,
                compressed_size_bytes=model.compressed_size_bytes,
                schema_version=model.schema_version,
            )
            session.add(dbe)
            await session.commit()
            state_metadata_model = self._map_dbe_to_model(dbe)
            return state_metadata_model

    async def get(self, execution_id: UUID) -> StateMetadataModel | None:
        async with get_db_session() as session:
            result = await session.execute(
                select(StateMetadataDBE).where(
                    StateMetadataDBE.execution_id == execution_id
                )
            )
            dbe = result.scalar_one_or_none()
            if not dbe:
                return None

            state_metadata_model = self._map_dbe_to_model(dbe)
            return state_metadata_model

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any
from uuid import UUID


class CompressionAlgorithm(StrEnum):
    NONE = "none"
    ZSTD = "zstd"
    S3 = "s3"


class StateSerializer:
    _ZSTD_THRESHOLD = 1_000_000
    _S3_THRESHOLD = 50_000_000

    @staticmethod
    def select_algorithm(size_bytes: int) -> CompressionAlgorithm:
        if size_bytes < StateSerializer._ZSTD_THRESHOLD:
            return CompressionAlgorithm.NONE
        if size_bytes < StateSerializer._S3_THRESHOLD:
            return CompressionAlgorithm.ZSTD
        return CompressionAlgorithm.S3

    @staticmethod
    async def serialize(
        state: dict[str, Any],
        execution_id: UUID,
    ) -> tuple[bytes, CompressionAlgorithm, int, int]:
        """
        Returns (payload, algorithm, original_size, compressed_size).
        """

        raw = json.dumps(state, default=str).encode()
        original_size = len(raw)
        algorithm = StateSerializer.select_algorithm(original_size)

        if algorithm == CompressionAlgorithm.NONE:
            return raw, algorithm, original_size, original_size

        if algorithm == CompressionAlgorithm.ZSTD:
            import zstandard as zstd

            compressed = zstd.ZstdCompressor(level=10).compress(raw)
            return compressed, algorithm, original_size, len(compressed)

        # S3 path: compress then stream up; store only the reference in the DB.
        import zstandard as zstd
        from src.infrastructure.storage.s3_client import s3_client

        compressed = zstd.ZstdCompressor(level=10).compress(raw)
        s3_key = f"waypoint/{str(execution_id)}/state.json.zst"
        await s3_client.put_object(
            Bucket="waypoint-states",
            Key=s3_key,
            Body=compressed,
        )
        reference = json.dumps({"s3_location": s3_key}).encode()
        return reference, algorithm, original_size, len(compressed)

    @staticmethod
    async def deserialize(
        payload: bytes,
        algorithm: CompressionAlgorithm,
    ) -> dict[str, Any]:
        if algorithm == CompressionAlgorithm.NONE:
            return json.loads(payload.decode())

        if algorithm == CompressionAlgorithm.ZSTD:
            import zstandard as zstd

            return json.loads(zstd.ZstdDecompressor().decompress(payload).decode())

        # S3 path: fetch then decompress.
        import zstandard as zstd
        from src.infrastructure.storage.s3_client import s3_client

        ref = json.loads(payload.decode())
        response = await s3_client.get_object(
            Bucket="waypoint-states", Key=ref["s3_location"]
        )
        raw = await response["Body"].read()
        return json.loads(zstd.ZstdDecompressor().decompress(raw).decode())

"""
Session service for HITL workflow.

Manages trip generation sessions including:
- Session CRUD operations
- LangGraph state persistence (checkpointer)
- Session cleanup (24h TTL)
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.schemas.session import (
    TripSession, 
    SessionStatus, 
    SessionPreview,
    HumanDecision
)
from app.schemas.trip import Itinerary, CostBreakdown


# Session TTL - 24 hours
SESSION_TTL_HOURS = 24


class SessionService:
    """Service for managing trip generation sessions"""
    
    @staticmethod
    def create_session(db, preferences: dict) -> TripSession:
        """
        Create a new trip generation session.
        
        Args:
            db: MongoDB database instance
            preferences: User preferences dict
            
        Returns:
            New TripSession object
        """
        now = datetime.utcnow()
        session = TripSession(
            session_id=str(uuid.uuid4()),
            status=SessionStatus.PROCESSING,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
            preferences=preferences,
            preview=None,
            final_itinerary=None,
            final_cost=None,
            final_breakdown=None,
            error_message=None
        )
        
        # Save to MongoDB
        db.sessions.insert_one(session.model_dump())
        print(f"[Session] Created session {session.session_id}")
        
        return session
    
    @staticmethod
    def get_session(db, session_id: str) -> TripSession | None:
        """Get a session by ID"""
        doc = db.sessions.find_one({"session_id": session_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return TripSession(**doc)
    
    @staticmethod
    def update_session_status(
        db, 
        session_id: str, 
        status: SessionStatus,
        preview: SessionPreview | None = None,
        error_message: str | None = None
    ) -> bool:
        """
        Update session status and optional preview data.
        
        Args:
            db: MongoDB database instance
            session_id: Session ID
            status: New status
            preview: Preview data (for awaiting_approval status)
            error_message: Error message (for failed status)
            
        Returns:
            True if updated, False if session not found
        """
        update = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }
        
        if preview:
            update["preview"] = preview.model_dump()
        
        if error_message:
            update["error_message"] = error_message
        
        result = db.sessions.update_one(
            {"session_id": session_id},
            {"$set": update}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def update_session_preferences(db, session_id: str, new_budget: float) -> bool:
        """
        Update session preferences with new budget.
        
        Args:
            db: MongoDB database instance
            session_id: Session ID
            new_budget: New budget limit
            
        Returns:
            True if updated, False if session not found
        """
        result = db.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "preferences.budget_limit": new_budget,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def complete_session(
        db,
        session_id: str,
        itinerary: Itinerary,
        total_cost: float,
        cost_breakdown: CostBreakdown
    ) -> bool:
        """
        Mark session as complete with final itinerary.
        
        Args:
            db: MongoDB database instance
            session_id: Session ID
            itinerary: Final approved itinerary
            total_cost: Total cost
            cost_breakdown: Cost breakdown by category
            
        Returns:
            True if updated, False if session not found
        """
        result = db.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": SessionStatus.COMPLETE.value,
                    "updated_at": datetime.utcnow(),
                    "final_itinerary": itinerary.model_dump(),
                    "final_cost": total_cost,
                    "final_breakdown": cost_breakdown.model_dump()
                }
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def cleanup_expired_sessions(db) -> int:
        """
        Delete sessions that have expired (older than 24h).
        
        Returns:
            Number of sessions deleted
        """
        now = datetime.utcnow()
        result = db.sessions.delete_many({
            "expires_at": {"$lt": now}
        })
        
        if result.deleted_count > 0:
            print(f"[Session] Cleaned up {result.deleted_count} expired sessions")
        
        return result.deleted_count
    
    @staticmethod
    def list_active_sessions(db, limit: int = 50) -> list[TripSession]:
        """List active (non-expired) sessions"""
        now = datetime.utcnow()
        docs = db.sessions.find({
            "expires_at": {"$gte": now}
        }).sort("created_at", -1).limit(limit)
        
        sessions = []
        for doc in docs:
            doc.pop("_id", None)
            sessions.append(TripSession(**doc))
        
        return sessions


# ============================================================================
# LANGGRAPH MONGODB CHECKPOINTER
# ============================================================================

class MongoDBCheckpointer(BaseCheckpointSaver):
    """
    MongoDB-based checkpointer for LangGraph.
    
    Persists agent state to MongoDB so we can interrupt and resume
    across HTTP request boundaries.
    """
    
    serde = JsonPlusSerializer()
    
    def __init__(self, db):
        """
        Initialize checkpointer with MongoDB database.
        
        Args:
            db: MongoDB database instance (from get_db())
        """
        super().__init__()
        self.collection = db.agent_checkpoints
    
    def get_tuple(self, config: dict) -> CheckpointTuple | None:
        """Sync version - Load checkpoint from MongoDB."""
        return self._get_tuple_impl(config)
    
    async def aget_tuple(self, config: dict) -> CheckpointTuple | None:
        """Async version - Load checkpoint from MongoDB."""
        # MongoDB driver is sync, so just call sync version
        return self._get_tuple_impl(config)
    
    def _get_tuple_impl(self, config: dict) -> CheckpointTuple | None:
        """
        Load checkpoint from MongoDB.
        
        Args:
            config: Config dict with thread_id in configurable
            
        Returns:
            CheckpointTuple or None if not found
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        
        # Find the latest checkpoint for this thread
        query = {"thread_id": thread_id}
        if checkpoint_ns:
            query["checkpoint_ns"] = checkpoint_ns
        
        doc = self.collection.find_one(
            query,
            sort=[("checkpoint_id", -1)]  # Latest first
        )
        
        if not doc:
            return None
        
        # Deserialize checkpoint data
        checkpoint = self.serde.loads_typed((doc["type"], doc["checkpoint"]))
        metadata = self.serde.loads_typed((doc["metadata_type"], doc["metadata"])) if doc.get("metadata") else {}
        
        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=doc.get("parent_config")
        )
    
    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any]
    ) -> dict:
        """Sync version - Save checkpoint to MongoDB."""
        return self._put_impl(config, checkpoint, metadata, new_versions)
    
    async def aput(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any]
    ) -> dict:
        """Async version - Save checkpoint to MongoDB."""
        return self._put_impl(config, checkpoint, metadata, new_versions)
    
    def _put_impl(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any]
    ) -> dict:
        """
        Save checkpoint to MongoDB.
        
        Args:
            config: Config dict with thread_id
            checkpoint: Checkpoint data to save
            metadata: Checkpoint metadata
            new_versions: Channel versions (not used for MongoDB)
            
        Returns:
            Updated config dict
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        
        # Serialize checkpoint and metadata
        type_str, checkpoint_bytes = self.serde.dumps_typed(checkpoint)
        metadata_type, metadata_bytes = self.serde.dumps_typed(metadata)
        
        doc = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint_id,
            "type": type_str,
            "checkpoint": checkpoint_bytes,
            "metadata_type": metadata_type,
            "metadata": metadata_bytes,
            "parent_config": config.get("configurable", {}).get("checkpoint_id"),
            "updated_at": datetime.utcnow()
        }
        
        # Upsert based on thread_id + checkpoint_id
        self.collection.update_one(
            {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "checkpoint_ns": checkpoint_ns
            },
            {"$set": doc},
            upsert=True
        )
        
        # Return updated config with checkpoint_id
        return {
            "configurable": {
                **config.get("configurable", {}),
                "checkpoint_id": checkpoint_id
            }
        }
    
    def list(self, config: dict, *, filter: dict | None = None, before: dict | None = None, limit: int | None = None):
        """Sync version - List checkpoints for a thread."""
        return self._list_impl(config, filter=filter, before=before, limit=limit)
    
    async def alist(self, config: dict, *, filter: dict | None = None, before: dict | None = None, limit: int | None = None):
        """Async version - List checkpoints for a thread."""
        for item in self._list_impl(config, filter=filter, before=before, limit=limit):
            yield item
    
    def _list_impl(self, config: dict, *, filter: dict | None = None, before: dict | None = None, limit: int | None = None):
        """
        List checkpoints for a thread.
        
        Args:
            config: Config with thread_id
            filter: Optional filter dict
            before: Optional checkpoint to list before
            limit: Max number of checkpoints to return
            
        Yields:
            CheckpointTuple objects
        """
        thread_id = config["configurable"]["thread_id"]
        
        query = {"thread_id": thread_id}
        if filter:
            query.update(filter)
        
        cursor = self.collection.find(query).sort("checkpoint_id", -1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        for doc in cursor:
            checkpoint = self.serde.loads_typed((doc["type"], doc["checkpoint"]))
            metadata = self.serde.loads_typed((doc["metadata_type"], doc["metadata"])) if doc.get("metadata") else {}
            
            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": doc["checkpoint_id"],
                        "checkpoint_ns": doc.get("checkpoint_ns", "")
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=doc.get("parent_config")
            )
    
    def put_writes(
        self,
        config: dict,
        writes: list,
        task_id: str
    ) -> None:
        """Sync version - Store intermediate writes."""
        self._put_writes_impl(config, writes, task_id)
    
    async def aput_writes(
        self,
        config: dict,
        writes: list,
        task_id: str
    ) -> None:
        """Async version - Store intermediate writes."""
        self._put_writes_impl(config, writes, task_id)
    
    def _put_writes_impl(
        self,
        config: dict,
        writes: list,
        task_id: str
    ) -> None:
        """
        Store intermediate writes for a task.
        
        This is used for pending writes during interrupts.
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id", "")
        
        # Serialize writes
        serialized_writes = []
        for write in writes:
            channel, value = write
            type_str, value_bytes = self.serde.dumps_typed(value)
            serialized_writes.append({
                "channel": channel,
                "type": type_str,
                "value": value_bytes
            })
        
        doc = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "writes": serialized_writes,
            "updated_at": datetime.utcnow()
        }
        
        # Upsert based on thread_id + checkpoint_id + task_id
        self.collection.database.agent_writes.update_one(
            {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id
            },
            {"$set": doc},
            upsert=True
        )
    
    def delete_thread(self, thread_id: str) -> int:
        """
        Delete all checkpoints for a thread.
        
        Args:
            thread_id: Thread ID to delete
            
        Returns:
            Number of checkpoints deleted
        """
        result = self.collection.delete_many({"thread_id": thread_id})
        # Also delete writes
        self.collection.database.agent_writes.delete_many({"thread_id": thread_id})
        return result.deleted_count


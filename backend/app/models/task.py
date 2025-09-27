"""
Task models for managing background tasks and tool calling actions.

This module defines models for storing and tracking tasks that the AI assistant
performs, including tool calls, scheduled actions, and ongoing instructions.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Task(Base):
    """
    Task model for storing and tracking AI assistant tasks.
    
    This model represents individual tasks that the AI assistant performs,
    including tool calls, scheduled actions, and follow-up tasks.
    """
    
    __tablename__ = "tasks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Task information
    task_type = Column(String(50), nullable=False, index=True)  # 'tool_call', 'scheduled', 'follow_up', etc.
    status = Column(String(20), nullable=False, default="pending", index=True)  # 'pending', 'in_progress', 'completed', 'failed', 'cancelled'
    
    # Task data
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=True)
    
    # Tool calling information
    tool_name = Column(String(100), nullable=True)
    tool_parameters = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    
    # Task dependencies and relationships
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    
    # Scheduling information
    scheduled_for = Column(DateTime, nullable=True, index=True)
    priority = Column(Integer, default=0, nullable=False)  # Higher number = higher priority
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0, nullable=False)
    current_step = Column(String(100), nullable=True)
    total_steps = Column(Integer, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id], foreign_keys=[parent_task_id], backref="subtasks")
    depends_on_task = relationship("Task", remote_side=[id], foreign_keys=[depends_on_task_id], backref="dependent_tasks")
    ongoing_instructions = relationship("OngoingInstruction", back_populates="task")
    
    # Indexes
    __table_args__ = (
        Index("idx_tasks_user_status", "user_id", "status"),
        Index("idx_tasks_scheduled", "scheduled_for"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_type_status", "task_type", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, type={self.task_type}, status={self.status})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if the task is pending."""
        return self.status == "pending"
    
    @property
    def is_in_progress(self) -> bool:
        """Check if the task is in progress."""
        return self.status == "in_progress"
    
    @property
    def is_completed(self) -> bool:
        """Check if the task is completed."""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if the task failed."""
        return self.status == "failed"
    
    @property
    def is_cancelled(self) -> bool:
        """Check if the task is cancelled."""
        return self.status == "cancelled"
    
    @property
    def can_retry(self) -> bool:
        """Check if the task can be retried."""
        return self.is_failed and self.retry_count < self.max_retries
    
    @property
    def is_scheduled(self) -> bool:
        """Check if the task is scheduled for future execution."""
        return self.scheduled_for is not None and self.scheduled_for > datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert task to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "task_type": self.task_type,
            "status": self.status,
            "title": self.title,
            "description": self.description,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "tool_name": self.tool_name,
            "tool_parameters": self.tool_parameters,
            "tool_result": self.tool_result,
            "parent_task_id": str(self.parent_task_id) if self.parent_task_id else None,
            "depends_on_task_id": str(self.depends_on_task_id) if self.depends_on_task_id else None,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "priority": self.priority,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class OngoingInstruction(Base):
    """
    Ongoing instruction model for storing persistent user instructions.
    
    This model represents instructions that the AI assistant should remember
    and apply to future interactions and events.
    """
    
    __tablename__ = "ongoing_instructions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    
    # Instruction information
    instruction_type = Column(String(50), nullable=False, index=True)  # 'email_rule', 'calendar_rule', 'hubspot_rule', etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Instruction data
    trigger_conditions = Column(JSON, nullable=False, default=dict)  # When to apply this instruction
    action_template = Column(JSON, nullable=False, default=dict)  # What to do when triggered
    
    # Instruction status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)  # Higher number = higher priority
    
    # Usage tracking
    trigger_count = Column(Integer, default=0, nullable=False)
    last_triggered_at = Column(DateTime, nullable=True)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="ongoing_instructions")
    task = relationship("Task", back_populates="ongoing_instructions")
    
    # Indexes
    __table_args__ = (
        Index("idx_ongoing_instructions_user_active", "user_id", "is_active"),
        Index("idx_ongoing_instructions_type", "instruction_type"),
        Index("idx_ongoing_instructions_priority", "priority"),
        Index("idx_ongoing_instructions_expires", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<OngoingInstruction(id={self.id}, type={self.instruction_type}, title={self.title})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the instruction is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of this instruction."""
        total_attempts = self.success_count + self.failure_count
        if total_attempts == 0:
            return 0.0
        return self.success_count / total_attempts
    
    @property
    def should_trigger(self) -> bool:
        """Check if this instruction should be considered for triggering."""
        return self.is_active and not self.is_expired
    
    def to_dict(self) -> dict:
        """Convert instruction to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "instruction_type": self.instruction_type,
            "title": self.title,
            "description": self.description,
            "trigger_conditions": self.trigger_conditions,
            "action_template": self.action_template,
            "is_active": self.is_active,
            "priority": self.priority,
            "trigger_count": self.trigger_count,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "is_expired": self.is_expired,
            "should_trigger": self.should_trigger,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class TaskExecutionLog(Base):
    """
    Task execution log model for tracking task execution history.
    
    This model provides detailed logging of task executions, including
    inputs, outputs, errors, and performance metrics.
    """
    
    __tablename__ = "task_execution_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to task
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    
    # Execution information
    execution_type = Column(String(50), nullable=False)  # 'start', 'step', 'complete', 'error', 'retry'
    step_name = Column(String(100), nullable=True)
    
    # Execution data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_data = Column(JSON, nullable=True)
    
    # Performance metrics
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task")
    
    # Indexes
    __table_args__ = (
        Index("idx_task_logs_task_execution", "task_id", "execution_type"),
        Index("idx_task_logs_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<TaskExecutionLog(id={self.id}, task_id={self.task_id}, type={self.execution_type})>"
    
    def to_dict(self) -> dict:
        """Convert log entry to dictionary representation."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "execution_type": self.execution_type,
            "step_name": self.step_name,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_data": self.error_data,
            "execution_time_ms": self.execution_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
"""
Proactive agent service for handling ongoing instructions and event-driven actions.

This service manages the AI assistant's proactive behavior, including
ongoing instructions, webhook processing, and automatic task execution.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from app.core.exceptions import AIError, ExternalServiceError
from app.models.user import User
from app.models.task import Task, OngoingInstruction
from app.models.integration import WebhookEvent
from app.services.ai_service import AIService
from app.services.tool_service import ToolService
from app.services.rag_service import RAGService

logger = structlog.get_logger(__name__)


class ProactiveAgent:
    """
    Proactive agent for handling ongoing instructions and event-driven actions.
    
    This agent monitors webhook events, processes ongoing instructions,
    and executes proactive tasks based on user-defined rules.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the proactive agent.
        
        Args:
            db: Database session
        """
        self.db = db
        self.ai_service = AIService()
        self.tool_service = ToolService(db)
        self.rag_service = RAGService(db)
    
    async def process_webhook_event(self, event: WebhookEvent) -> None:
        """
        Process a webhook event and trigger proactive actions.
        
        Args:
            event: Webhook event to process
        """
        try:
            logger.info("Processing webhook event", event_id=str(event.id), event_type=event.event_type)
            
            # Get the user associated with this webhook
            user = await self._get_user_from_webhook(event)
            if not user:
                logger.warning("No user found for webhook event", event_id=str(event.id))
                return
            
            # Get relevant ongoing instructions
            instructions = await self._get_relevant_instructions(user.id, event)
            
            # Process each instruction
            for instruction in instructions:
                await self._process_instruction(instruction, event, user)
            
            # Update event status
            event.status = "completed"
            event.processed_at = datetime.utcnow()
            await self.db.commit()
            
            logger.info("Webhook event processed successfully", event_id=str(event.id))
            
        except Exception as e:
            logger.error("Failed to process webhook event", event_id=str(event.id), error=str(e))
            event.status = "failed"
            event.processing_error = str(e)
            await self.db.commit()
            raise
    
    async def _get_user_from_webhook(self, event: WebhookEvent) -> Optional[User]:
        """
        Get the user associated with a webhook event.
        
        Args:
            event: Webhook event
            
        Returns:
            Optional[User]: Associated user
        """
        try:
            # Get webhook and account information
            result = await self.db.execute(
                select(WebhookEvent)
                .join(WebhookEvent.webhook)
                .join(Webhook.account)
                .where(WebhookEvent.id == event.id)
            )
            webhook_event = result.scalar_one_or_none()
            
            if not webhook_event:
                return None
            
            # Get user from account
            result = await self.db.execute(
                select(User).where(User.id == webhook_event.webhook.account.user_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get user from webhook", error=str(e))
            return None
    
    async def _get_relevant_instructions(
        self, 
        user_id: str, 
        event: WebhookEvent
    ) -> List[OngoingInstruction]:
        """
        Get ongoing instructions relevant to a webhook event.
        
        Args:
            user_id: User ID
            event: Webhook event
            
        Returns:
            List[OngoingInstruction]: Relevant instructions
        """
        try:
            # Get active instructions for the user
            result = await self.db.execute(
                select(OngoingInstruction).where(
                    and_(
                        OngoingInstruction.user_id == user_id,
                        OngoingInstruction.is_active == True,
                        or_(
                            OngoingInstruction.expires_at.is_(None),
                            OngoingInstruction.expires_at > datetime.utcnow()
                        )
                    )
                )
            )
            instructions = result.scalars().all()
            
            # Filter instructions based on event type and conditions
            relevant_instructions = []
            for instruction in instructions:
                if await self._is_instruction_relevant(instruction, event):
                    relevant_instructions.append(instruction)
            
            return relevant_instructions
            
        except Exception as e:
            logger.error("Failed to get relevant instructions", error=str(e))
            return []
    
    async def _is_instruction_relevant(
        self, 
        instruction: OngoingInstruction, 
        event: WebhookEvent
    ) -> bool:
        """
        Check if an instruction is relevant to a webhook event.
        
        Args:
            instruction: Ongoing instruction
            event: Webhook event
            
        Returns:
            bool: True if relevant
        """
        try:
            trigger_conditions = instruction.trigger_conditions
            
            # Check event type
            if "event_types" in trigger_conditions:
                if event.event_type not in trigger_conditions["event_types"]:
                    return False
            
            # Check source
            if "sources" in trigger_conditions:
                # Get source from webhook
                source = await self._get_webhook_source(event)
                if source not in trigger_conditions["sources"]:
                    return False
            
            # Check custom conditions
            if "custom_conditions" in trigger_conditions:
                if not await self._evaluate_custom_conditions(
                    trigger_conditions["custom_conditions"], 
                    event
                ):
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Failed to check instruction relevance", error=str(e))
            return False
    
    async def _get_webhook_source(self, event: WebhookEvent) -> str:
        """
        Get the source service for a webhook event.
        
        Args:
            event: Webhook event
            
        Returns:
            str: Source service name
        """
        try:
            # Get webhook and account information
            result = await self.db.execute(
                select(WebhookEvent)
                .join(WebhookEvent.webhook)
                .join(Webhook.account)
                .where(WebhookEvent.id == event.id)
            )
            webhook_event = result.scalar_one_or_none()
            
            if webhook_event:
                return webhook_event.webhook.account.service
            
            return "unknown"
            
        except Exception as e:
            logger.error("Failed to get webhook source", error=str(e))
            return "unknown"
    
    async def _evaluate_custom_conditions(
        self, 
        conditions: Dict[str, Any], 
        event: WebhookEvent
    ) -> bool:
        """
        Evaluate custom conditions for an instruction.
        
        Args:
            conditions: Custom conditions
            event: Webhook event
            
        Returns:
            bool: True if conditions are met
        """
        try:
            # This is a simplified implementation
            # In a real system, you might use a more sophisticated rule engine
            
            for condition_type, condition_value in conditions.items():
                if condition_type == "contains_keywords":
                    # Check if event data contains specific keywords
                    event_data_str = str(event.event_data).lower()
                    keywords = [kw.lower() for kw in condition_value]
                    if not any(keyword in event_data_str for keyword in keywords):
                        return False
                
                elif condition_type == "time_range":
                    # Check if event is within time range
                    now = datetime.utcnow()
                    if "start_hour" in condition_value:
                        if now.hour < condition_value["start_hour"]:
                            return False
                    if "end_hour" in condition_value:
                        if now.hour > condition_value["end_hour"]:
                            return False
                
                elif condition_type == "day_of_week":
                    # Check if event is on specific days
                    if now.weekday() not in condition_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error("Failed to evaluate custom conditions", error=str(e))
            return False
    
    async def _process_instruction(
        self, 
        instruction: OngoingInstruction, 
        event: WebhookEvent, 
        user: User
    ) -> None:
        """
        Process an ongoing instruction and execute actions.
        
        Args:
            instruction: Ongoing instruction
            event: Webhook event
            user: User
        """
        try:
            logger.info("Processing instruction", instruction_id=str(instruction.id))
            
            # Update instruction trigger count
            instruction.trigger_count += 1
            instruction.last_triggered_at = datetime.utcnow()
            
            # Generate action based on instruction template
            action = await self._generate_action(instruction, event, user)
            
            if action:
                # Create and execute task
                task = await self._create_task_from_action(action, user, instruction)
                await self._execute_task(task, user)
                
                # Update instruction success count
                instruction.success_count += 1
            else:
                # Update instruction failure count
                instruction.failure_count += 1
            
            await self.db.commit()
            
            logger.info("Instruction processed successfully", instruction_id=str(instruction.id))
            
        except Exception as e:
            logger.error("Failed to process instruction", instruction_id=str(instruction.id), error=str(e))
            instruction.failure_count += 1
            await self.db.commit()
            raise
    
    async def _generate_action(
        self, 
        instruction: OngoingInstruction, 
        event: WebhookEvent, 
        user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an action based on instruction template and event.
        
        Args:
            instruction: Ongoing instruction
            event: Webhook event
            user: User
            
        Returns:
            Optional[Dict]: Generated action
        """
        try:
            # Prepare context for AI
            context = {
                "instruction": instruction.description,
                "action_template": instruction.action_template,
                "event": {
                    "type": event.event_type,
                    "data": event.event_data
                },
                "user": {
                    "id": str(user.id),
                    "email": user.email
                }
            }
            
            # Generate action using AI
            prompt = f"""
            Based on the following ongoing instruction and webhook event, generate a specific action to execute.
            
            Instruction: {instruction.description}
            Action Template: {instruction.action_template}
            Event: {event.event_type} - {event.event_data}
            
            Generate a JSON action with the following structure:
            {{
                "tool_name": "tool_to_execute",
                "parameters": {{"param1": "value1"}},
                "description": "What this action will do"
            }}
            
            Return only valid JSON.
            """
            
            response = await self.ai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                user_id=str(user.id),
                context=[{"content": str(context), "source": "instruction", "relevance_score": 100}]
            )
            
            # Get the response
            ai_response = await response.__anext__()
            
            if ai_response.get("content"):
                import json
                try:
                    action = json.loads(ai_response["content"])
                    return action
                except json.JSONDecodeError:
                    logger.error("Failed to parse AI response as JSON", response=ai_response["content"])
                    return None
            
            return None
            
        except Exception as e:
            logger.error("Failed to generate action", error=str(e))
            return None
    
    async def _create_task_from_action(
        self, 
        action: Dict[str, Any], 
        user: User, 
        instruction: OngoingInstruction
    ) -> Task:
        """
        Create a task from a generated action.
        
        Args:
            action: Generated action
            user: User
            instruction: Ongoing instruction
            
        Returns:
            Task: Created task
        """
        try:
            task = Task(
                user_id=user.id,
                task_type="proactive_action",
                title=f"Proactive: {action.get('description', 'Unknown action')}",
                description=f"Automated action triggered by: {instruction.title}",
                input_data={
                    "instruction_id": str(instruction.id),
                    "action": action
                },
                tool_name=action.get("tool_name"),
                tool_parameters=action.get("parameters", {}),
                priority=instruction.priority
            )
            
            self.db.add(task)
            await self.db.commit()
            await self.db.refresh(task)
            
            return task
            
        except Exception as e:
            logger.error("Failed to create task from action", error=str(e))
            raise
    
    async def _execute_task(self, task: Task, user: User) -> None:
        """
        Execute a proactive task.
        
        Args:
            task: Task to execute
            user: User
        """
        try:
            if task.tool_name and task.tool_parameters:
                # Execute tool
                result = await self.tool_service.execute_tool(
                    tool_name=task.tool_name,
                    parameters=task.tool_parameters,
                    user=user
                )
                
                # Update task with result
                task.status = "completed"
                task.output_data = result
                task.completed_at = datetime.utcnow()
                
            else:
                # No tool to execute
                task.status = "completed"
                task.completed_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info("Proactive task executed successfully", task_id=str(task.id))
            
        except Exception as e:
            logger.error("Failed to execute proactive task", task_id=str(task.id), error=str(e))
            task.status = "failed"
            task.error_message = str(e)
            await self.db.commit()
            raise
    
    async def create_ongoing_instruction(
        self,
        user_id: str,
        title: str,
        description: str,
        trigger_conditions: Dict[str, Any],
        action_template: Dict[str, Any],
        priority: int = 0
    ) -> OngoingInstruction:
        """
        Create a new ongoing instruction.
        
        Args:
            user_id: User ID
            title: Instruction title
            description: Instruction description
            trigger_conditions: Conditions for triggering
            action_template: Template for actions
            priority: Instruction priority
            
        Returns:
            OngoingInstruction: Created instruction
        """
        try:
            instruction = OngoingInstruction(
                user_id=user_id,
                title=title,
                description=description,
                trigger_conditions=trigger_conditions,
                action_template=action_template,
                priority=priority
            )
            
            self.db.add(instruction)
            await self.db.commit()
            await self.db.refresh(instruction)
            
            logger.info("Created ongoing instruction", instruction_id=str(instruction.id))
            return instruction
            
        except Exception as e:
            logger.error("Failed to create ongoing instruction", error=str(e))
            raise
    
    async def get_user_instructions(self, user_id: str) -> List[OngoingInstruction]:
        """
        Get all ongoing instructions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[OngoingInstruction]: User's instructions
        """
        try:
            result = await self.db.execute(
                select(OngoingInstruction).where(
                    OngoingInstruction.user_id == user_id
                ).order_by(OngoingInstruction.priority.desc(), OngoingInstruction.created_at.desc())
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Failed to get user instructions", error=str(e))
            return []
    
    async def update_instruction_status(
        self, 
        instruction_id: str, 
        is_active: bool
    ) -> bool:
        """
        Update the status of an ongoing instruction.
        
        Args:
            instruction_id: Instruction ID
            is_active: Whether instruction is active
            
        Returns:
            bool: True if updated successfully
        """
        try:
            result = await self.db.execute(
                update(OngoingInstruction)
                .where(OngoingInstruction.id == instruction_id)
                .values(is_active=is_active, updated_at=datetime.utcnow())
            )
            
            if result.rowcount > 0:
                await self.db.commit()
                logger.info("Updated instruction status", instruction_id=instruction_id, is_active=is_active)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to update instruction status", error=str(e))
            return False
"""
AI service for OpenAI integration and RAG operations.

This service handles OpenAI API interactions, embedding generation,
chat completions, and tool calling for the AI assistant.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

import structlog
import openai
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import AIError, ExternalServiceError
from app.core.logging import log_ai_interaction

logger = structlog.get_logger(__name__)


class AIService:
    """
    AI service for OpenAI API interactions.
    
    This service provides methods for generating embeddings, chat completions,
    tool calling, and RAG operations using OpenAI's API.
    """
    
    def __init__(self):
        """Initialize the AI service."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.max_context_length = settings.MAX_CONTEXT_LENGTH
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Embedding vector
            
        Raises:
            AIError: If embedding generation fails
        """
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            embedding = response.data[0].embedding
            tokens_used = response.usage.total_tokens
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_ai_interaction(
                interaction_type="embedding",
                user_id="system",
                model=self.embedding_model,
                tokens_used=tokens_used,
                duration_ms=duration_ms
            )
            
            logger.info("Generated embedding", text_length=len(text), tokens_used=tokens_used)
            return embedding
            
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise AIError("Failed to generate embedding")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            AIError: If embedding generation fails
        """
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            tokens_used = response.usage.total_tokens
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_ai_interaction(
                interaction_type="embedding_batch",
                user_id="system",
                model=self.embedding_model,
                tokens_used=tokens_used,
                duration_ms=duration_ms
            )
            
            logger.info("Generated batch embeddings", count=len(texts), tokens_used=tokens_used)
            return embeddings
            
        except Exception as e:
            logger.error("Failed to generate batch embeddings", error=str(e))
            raise AIError("Failed to generate batch embeddings")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        context: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        tool_service: Optional[Any] = None,
        user: Optional[Any] = None,
        ongoing_instructions: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate chat completion using OpenAI.
        
        Args:
            messages: List of chat messages
            user_id: User ID for logging
            context: RAG context for augmentation
            tools: Available tools for function calling
            stream: Whether to stream the response
            tool_service: Tool service for executing tools (required for streaming with tools)
            user: User object for tool execution (required for streaming with tools)
            
        Yields:
            Dict: Chat completion chunks or final response
        """
        try:
            start_time = datetime.utcnow()
            
            # Prepare system message with context and ongoing instructions
            system_message = self._prepare_system_message(context, ongoing_instructions)
            
            # Prepare messages
            chat_messages = [system_message] + messages
            
            # Prepare request
            request_data = {
                "model": self.model,
                "messages": chat_messages,
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": stream
            }
            
            if tools:
                request_data["tools"] = tools
                request_data["tool_choice"] = "auto"
            
            if stream:
                async for chunk in self._stream_chat_completion(request_data, user_id, start_time, tool_service, user):
                    yield chunk
            else:
                response = await self.client.chat.completions.create(**request_data)
                
                # Log interaction
                tokens_used = response.usage.total_tokens if response.usage else 0
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                log_ai_interaction(
                    interaction_type="chat_completion",
                    user_id=user_id,
                    model=self.model,
                    tokens_used=tokens_used,
                    duration_ms=duration_ms
                )
                
                # Prepare response
                response_data = {
                    "content": response.choices[0].message.content,
                    "role": response.choices[0].message.role,
                    "finish_reason": response.choices[0].finish_reason,
                    "tokens_used": tokens_used,
                    "model_used": self.model
                }
                
                # Handle tool calls
                if response.choices[0].message.tool_calls:
                    response_data["tool_calls"] = [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in response.choices[0].message.tool_calls
                    ]
                
                yield response_data
                
        except Exception as e:
            logger.error("Chat completion failed", user_id=user_id, error=str(e))
            yield {
                "error": "Chat completion failed",
                "content": "I apologize, but I encountered an error while processing your request. Please try again.",
                "role": "assistant",
                "finish_reason": "error"
            }
    
    async def _stream_chat_completion(
        self,
        request_data: Dict[str, Any],
        user_id: str,
        start_time: datetime,
        tool_service: Optional[Any] = None,
        user: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completion response.
        
        Args:
            request_data: OpenAI API request data
            user_id: User ID for logging
            start_time: Request start time
            tool_service: Tool service for executing tools
            user: User object for tool execution
            
        Yields:
            Dict: Streaming response chunks
        """
        try:
            stream = await self.client.chat.completions.create(**request_data)
            
            content = ""
            tool_calls = []
            
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    
                    if choice.delta.content:
                        content += choice.delta.content
                        yield {
                            "type": "content",
                            "content": choice.delta.content,
                            "role": "assistant"
                        }
                    
                    if choice.delta.tool_calls:
                        for tool_call in choice.delta.tool_calls:
                            if tool_call.index >= len(tool_calls):
                                tool_calls.extend([None] * (tool_call.index + 1 - len(tool_calls)))
                            
                            if tool_calls[tool_call.index] is None:
                                tool_calls[tool_call.index] = {
                                    "id": tool_call.id,
                                    "type": tool_call.type,
                                    "function": {
                                        "name": tool_call.function.name,
                                        "arguments": ""
                                    }
                                }
                            
                            if tool_call.function.arguments:
                                tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
                    
                    if choice.finish_reason:
                        # Check if we have tool calls and tool service is available
                        if tool_calls and tool_service and user:
                            # Execute tools
                            tool_results = []
                            for tool_call in tool_calls:
                                if tool_call is None:
                                    continue
                                    
                                try:
                                    # Parse tool arguments
                                    import json
                                    arguments = json.loads(tool_call["function"]["arguments"])
                                    
                                    # Execute tool
                                    result = await tool_service.execute_tool(
                                        tool_name=tool_call["function"]["name"],
                                        parameters=arguments,
                                        user=user
                                    )
                                    
                                    tool_results.append({
                                        "tool_call_id": tool_call["id"],
                                        "name": tool_call["function"]["name"],
                                        "result": result
                                    })
                                    
                                except Exception as e:
                                    logger.error("Tool execution failed", tool_name=tool_call["function"]["name"], error=str(e))
                                    tool_results.append({
                                        "tool_call_id": tool_call["id"],
                                        "name": tool_call["function"]["name"],
                                        "result": {"error": f"Tool execution failed: {str(e)}"}
                                    })
                            
                            # Send tool results
                            yield {
                                "type": "tool_results",
                                "tool_results": tool_results
                            }
                            
                            # Create follow-up request with tool results
                            follow_up_messages = request_data["messages"] + [
                                {
                                    "role": "assistant",
                                    "content": content,
                                    "tool_calls": [
                                        {
                                            "id": tc["id"],
                                            "type": tc["type"],
                                            "function": {
                                                "name": tc["function"]["name"],
                                                "arguments": tc["function"]["arguments"]
                                            }
                                        }
                                        for tc in tool_calls if tc is not None
                                    ]
                                }
                            ]
                            
                            # Add tool result messages
                            for tool_result in tool_results:
                                follow_up_messages.append({
                                    "role": "tool",
                                    "content": json.dumps(tool_result["result"]),
                                    "tool_call_id": tool_result["tool_call_id"]
                                })
                            
                            # Get final response after tool execution
                            follow_up_request = {
                                **request_data,
                                "messages": follow_up_messages,
                                "tools": None,  # Remove tools from follow-up request
                                "tool_choice": None
                            }
                            
                            # Stream the final response
                            final_stream = await self.client.chat.completions.create(**follow_up_request)
                            
                            final_content = ""
                            async for final_chunk in final_stream:
                                if final_chunk.choices:
                                    final_choice = final_chunk.choices[0]
                                    
                                    if final_choice.delta.content:
                                        final_content += final_choice.delta.content
                                        yield {
                                            "type": "content",
                                            "content": final_choice.delta.content,
                                            "role": "assistant"
                                        }
                                    
                                    if final_choice.finish_reason:
                                        # Log interaction
                                        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                                        
                                        log_ai_interaction(
                                            interaction_type="chat_completion_stream",
                                            user_id=user_id,
                                            model=self.model,
                                            tokens_used=0,
                                            duration_ms=duration_ms
                                        )
                                        
                                        yield {
                                            "type": "finish",
                                            "content": final_content,
                                            "role": "assistant",
                                            "finish_reason": final_choice.finish_reason,
                                            "tool_calls": [tc for tc in tool_calls if tc is not None],
                                            "model_used": self.model
                                        }
                                        break
                        else:
                            # No tool calls or no tool service, finish normally
                            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                            
                            log_ai_interaction(
                                interaction_type="chat_completion_stream",
                                user_id=user_id,
                                model=self.model,
                                tokens_used=0,
                                duration_ms=duration_ms
                            )
                            
                            yield {
                                "type": "finish",
                                "content": content,
                                "role": "assistant",
                                "finish_reason": choice.finish_reason,
                                "tool_calls": [tc for tc in tool_calls if tc is not None],
                                "model_used": self.model
                            }
                        break
                        
        except Exception as e:
            logger.error("Streaming chat completion failed", user_id=user_id, error=str(e))
            yield {
                "type": "error",
                "error": "Streaming failed",
                "content": "I apologize, but I encountered an error while processing your request."
            }
    
    def _prepare_system_message(self, context: Optional[List[Dict[str, Any]]] = None, ongoing_instructions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """
        Prepare system message with context.
        
        Args:
            context: RAG context for augmentation
            
        Returns:
            Dict: System message
        """
        system_prompt = """You are a helpful AI assistant for financial advisors. You have access to the advisor's Gmail, Google Calendar, and HubSpot CRM data to help answer questions and perform tasks.

Key capabilities:
- Answer questions about clients, meetings, and communications
- Schedule appointments and manage calendar events
- Send emails and manage communications
- Create and update CRM contacts and notes
- Provide insights based on client interactions

Guidelines:
- Always be professional and helpful
- Use the provided context to give accurate, specific answers
- When creating contacts, ensure all required information is collected
- Ask clarifying questions when information is missing
- Be proactive in suggesting follow-up actions
- For complex tasks, break them down into steps and execute them systematically
- Use multiple tools in sequence when needed (e.g., search contact, then get availability, then send options)
- When searching for contacts: First search HubSpot, if not found OR if HubSpot access fails, then search Gmail emails for the person
- If HubSpot tool execution fails with "User does not have HubSpot access", immediately search Gmail emails instead
- When sending emails: Always search for the recipient's email address first (HubSpot, then Gmail if HubSpot fails)
- For email tasks: Search for contact info, then send the email using gmail_send tool

Appointment Scheduling Workflow:
- When scheduling appointments: DO NOT create calendar events immediately
- For appointment requests: First search for the contact, get available times, send email with options, wait for response
- Appointment workflow: Search contact → Get available times → Send email with options → Wait for response → Take action based on response
- If contact picks a time: Create calendar event and send confirmation
- If contact says no times work: Send new available times and follow up
- If contact suggests different times: Check availability and respond accordingly
- Be flexible and handle all edge cases through conversation
- Only create calendar events after the contact confirms a specific time

Available tools:
- gmail_send: Send emails
- gmail_search: Search emails
- calendar_get_events: Get calendar events
- calendar_get_availability: Get available time slots
- calendar_create_event: Create calendar events
- hubspot_get_contacts: Get CRM contacts
- hubspot_create_contact: Create CRM contacts
- hubspot_create_note: Create contact notes
- hubspot_search_contacts: Search contacts

Use these tools to help the advisor manage their client relationships effectively."""
        
        # Add ongoing instructions
        if ongoing_instructions:
            instructions_text = "\n\nOngoing Instructions (apply when relevant):\n"
            for instruction in ongoing_instructions:
                instructions_text += f"- {instruction.get('description', instruction.get('title', 'Unknown instruction'))}\n"
            system_prompt += instructions_text
        
        if context:
            context_text = "\n\nRelevant Context:\n"
            for item in context:
                source = item.get("source", "Unknown")
                content = item.get("content", "")
                relevance = item.get("relevance_score", 0)
                context_text += f"\n[{source}] (Relevance: {relevance}%)\n{content}\n"
            
            system_prompt += context_text
        
        return {
            "role": "system",
            "content": system_prompt
        }
    
    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from text using OpenAI.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Dict: Extracted entities by type
        """
        try:
            prompt = f"""Extract entities from the following text and return as JSON with these categories:
- people: Names of people mentioned
- companies: Company names mentioned
- dates: Dates and times mentioned
- emails: Email addresses mentioned
- phones: Phone numbers mentioned
- topics: Main topics or subjects discussed

Text: {text}

Return only valid JSON with the entity categories as keys and arrays of strings as values."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an entity extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            entities = json.loads(content)
            
            logger.info("Extracted entities", text_length=len(text), entity_count=sum(len(v) for v in entities.values()))
            return entities
            
        except Exception as e:
            logger.error("Failed to extract entities", error=str(e))
            return {}
    
    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        Summarize text using OpenAI.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            str: Text summary
        """
        try:
            prompt = f"""Summarize the following text in {max_length} characters or less, focusing on key information:

{text}

Summary:"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful summarization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            summary = response.choices[0].message.content.strip()
            
            logger.info("Generated text summary", original_length=len(text), summary_length=len(summary))
            return summary
            
        except Exception as e:
            logger.error("Failed to summarize text", error=str(e))
            return text[:max_length] + "..." if len(text) > max_length else text
    
    def get_query_hash(self, query: str) -> str:
        """
        Generate hash for query caching.
        
        Args:
            query: Query text
            
        Returns:
            str: SHA256 hash of the query
        """
        return hashlib.sha256(query.encode()).hexdigest()
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for embedding.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size
            overlap: Overlap between chunks
            
        Returns:
            List[str]: Text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
"""
LangChain-based AI service for proactive agent pipeline.

This service provides a LangChain-powered AI agent that can execute
multi-step processes automatically using tools.
"""

import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import hashlib
import os

# Set tiktoken cache directory to avoid download issues
os.environ['TIKTOKEN_CACHE_DIR'] = '/tmp/tiktoken_cache'

import structlog
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from app.core.config import settings
from app.core.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)


class LangChainService:
    """
    LangChain-based AI service for proactive agent pipeline.
    
    This service uses LangChain agents to automatically execute
    multi-step processes with tools.
    """
    
    def __init__(self):
        """Initialize the LangChain AI service."""
        self.model = "gpt-4"
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0.1,
            api_key=settings.OPENAI_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        self.agent_executor = None
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        # Cache for calendar availability to avoid duplicate API calls
        self._cached_availability = None
        self._availability_cache_time = None
    
    def _format_time_slots(self, slots: List[Dict[str, Any]]) -> str:
        """
        Format calendar time slots into human-readable text.
        
        Args:
            slots: List of time slot dictionaries with 'start', 'end', and optionally 'duration_minutes'
            
        Returns:
            Formatted string with human-readable time slots
        """
        if not slots:
            return "No specific time slots available"
        
        formatted_slots = []
        for slot in slots:
            try:
                # Parse the start time
                start_time = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(slot['end'].replace('Z', '+00:00'))
                
                # Format the time slot
                day_name = start_time.strftime("%A")
                date_str = start_time.strftime("%B %d, %Y")
                start_str = start_time.strftime("%I:%M %p")
                end_str = end_time.strftime("%I:%M %p")
                
                # Get timezone abbreviation (simplified)
                timezone_str = start_time.strftime("%Z") if start_time.tzinfo else "EDT"
                
                formatted_slot = f"{day_name}, {date_str} from {start_str} to {end_str} ({timezone_str})"
                formatted_slots.append(formatted_slot)
            except Exception as e:
                logger.warning("Failed to format time slot", slot=slot, error=str(e))
                # Fallback to raw slot info - ensure no template variables
                start_time = slot.get('start', 'Unknown time')
                end_time = slot.get('end', 'Unknown time')
                # Use string formatting instead of f-string to avoid any template issues
                formatted_slots.append("{} to {}".format(start_time, end_time))
        
        return "\n".join([f"- {slot}" for slot in formatted_slots])
    
    def _create_tool_wrapper(self, tool_service, tool_name: str):
        """
        Create a tool wrapper function for LangChain.
        
        Args:
            tool_service: Tool service instance
            tool_name: Name of the tool
            
        Returns:
            Tool wrapper function
        """
        def tool_wrapper(*args, **kwargs):
            # Convert positional args to kwargs if needed
            if args and not kwargs:
                # For single argument tools like hubspot_search_contacts
                if tool_name in ["hubspot_search_contacts", "gmail_search"]:
                    kwargs["query"] = args[0]
                elif tool_name == "calendar_get_availability":
                    if len(args) >= 2:
                        kwargs["time_min"] = args[0]
                        kwargs["time_max"] = args[1]
                    else:
                        kwargs["time_min"] = args[0]
                        kwargs["time_max"] = "2025-10-17T17:00:00-04:00"  # Default end time
                elif tool_name == "gmail_send":
                    # Handle gmail_send with multiple arguments
                    if len(args) == 1 and isinstance(args[0], str):
                        # Single string argument - try to parse as JSON or use as email
                        arg = args[0]
                        if arg.startswith('{') and arg.endswith('}'):
                            # JSON string
                            import json
                            try:
                                parsed = json.loads(arg)
                                kwargs.update(parsed)
                            except:
                                # If JSON parsing fails, require the agent to provide complete email
                                kwargs["to"] = arg
                                kwargs["subject"] = "Meeting Request"
                                kwargs["body"] = "ERROR: Please provide complete email content with time slots. Use format: gmail_send(to='email', subject='subject', body='complete email with time slots')"
                        else:
                            # Just an email address - use cached availability if available
                            kwargs["to"] = arg
                            kwargs["subject"] = "Meeting Request"
                            
                            # Check if we have recent cached availability (within last 5 minutes)
                            if (self._cached_availability and 
                                self._availability_cache_time and 
                                (datetime.now() - self._availability_cache_time).seconds < 300):
                                
                                # Use cached availability
                                try:
                                    # Parse the cached availability result
                                    if isinstance(self._cached_availability, str):
                                        import json
                                        cached_data = json.loads(self._cached_availability)
                                    else:
                                        cached_data = self._cached_availability
                                    
                                    if 'available_slots' in cached_data and cached_data['available_slots']:
                                        slots = cached_data['available_slots'][:5]  # First 5 slots
                                        slots_text = self._format_time_slots(slots)
                                        kwargs["body"] = f"""Dear {arg.split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have the following available time slots:

{slots_text}

Please let me know which time works best for you, and I'll send you a calendar invitation.

Best regards"""
                                    else:
                                        kwargs["body"] = f"""Dear {arg.split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                                except Exception as e:
                                    logger.warning("Failed to parse cached availability", error=str(e))
                                    kwargs["body"] = f"""Dear {arg.split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                            else:
                                # No cached availability - get fresh data
                                try:
                                    from datetime import timedelta
                                    now = datetime.now()
                                    time_min = now.strftime("%Y-%m-%dT%H:%M:%S%z")
                                    time_max = (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S%z")
                                    
                                    availability_result = tool_service.calendar_get_availability(
                                        time_min=time_min,
                                        time_max=time_max
                                    )
                                    
                                    # Cache the result
                                    self._cached_availability = availability_result
                                    self._availability_cache_time = datetime.now()
                                    
                                    # Use the result
                                    if availability_result and 'available_slots' in availability_result:
                                        slots = availability_result['available_slots'][:5]
                                        slots_text = self._format_time_slots(slots)
                                        kwargs["body"] = f"""Dear {arg.split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have the following available time slots:

{slots_text}

Please let me know which time works best for you, and I'll send you a calendar invitation.

Best regards"""
                                    else:
                                        kwargs["body"] = f"""Dear {arg.split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                                except Exception as e:
                                    logger.warning("Failed to get calendar availability", error=str(e))
                                    kwargs["body"] = f"""Dear {arg.split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                    elif len(args) >= 3:
                        # Multiple arguments: to, subject, body
                        kwargs["to"] = args[0]
                        kwargs["subject"] = args[1]
                        kwargs["body"] = args[2]
                    elif len(args) == 2:
                        # Two arguments: to, subject (no body) - use cached availability
                        kwargs["to"] = args[0]
                        kwargs["subject"] = args[1]
                        
                        # Check if we have recent cached availability (within last 5 minutes)
                        if (self._cached_availability and 
                            self._availability_cache_time and 
                            (datetime.now() - self._availability_cache_time).seconds < 300):
                            
                            # Use cached availability
                            try:
                                # Parse the cached availability result
                                if isinstance(self._cached_availability, str):
                                    import json
                                    cached_data = json.loads(self._cached_availability)
                                else:
                                    cached_data = self._cached_availability
                                
                                if 'available_slots' in cached_data and cached_data['available_slots']:
                                    slots = cached_data['available_slots'][:5]  # First 5 slots
                                    slots_text = self._format_time_slots(slots)
                                    kwargs["body"] = f"""Dear {args[0].split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have the following available time slots:

{slots_text}

Please let me know which time works best for you, and I'll send you a calendar invitation.

Best regards"""
                                else:
                                    kwargs["body"] = f"""Dear {args[0].split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                            except Exception as e:
                                logger.warning("Failed to parse cached availability", error=str(e))
                                kwargs["body"] = f"""Dear {args[0].split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                        else:
                            # No cached availability - get fresh data
                            try:
                                from datetime import timedelta
                                now = datetime.now()
                                time_min = now.strftime("%Y-%m-%dT%H:%M:%S%z")
                                time_max = (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S%z")
                                
                                availability_result = tool_service.calendar_get_availability(
                                    time_min=time_min,
                                    time_max=time_max
                                )
                                
                                # Cache the result
                                self._cached_availability = availability_result
                                self._availability_cache_time = datetime.now()
                                
                                # Use the result
                                if availability_result and 'available_slots' in availability_result:
                                    slots = availability_result['available_slots'][:5]
                                    slots_text = self._format_time_slots(slots)
                                    kwargs["body"] = f"""Dear {args[0].split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have the following available time slots:

{slots_text}

Please let me know which time works best for you, and I'll send you a calendar invitation.

Best regards"""
                                else:
                                    kwargs["body"] = f"""Dear {args[0].split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                            except Exception as e:
                                logger.warning("Failed to get calendar availability", error=str(e))
                                kwargs["body"] = f"""Dear {args[0].split('@')[0].title()},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                    else:
                        # Fallback case - use cached availability
                        kwargs["to"] = args[0] if args else ""
                        kwargs["subject"] = "Meeting Request"
                        
                        # Check if we have recent cached availability (within last 5 minutes)
                        if (self._cached_availability and 
                            self._availability_cache_time and 
                            (datetime.now() - self._availability_cache_time).seconds < 300):
                            
                            # Use cached availability
                            try:
                                # Parse the cached availability result
                                if isinstance(self._cached_availability, str):
                                    import json
                                    cached_data = json.loads(self._cached_availability)
                                else:
                                    cached_data = self._cached_availability
                                
                                if 'available_slots' in cached_data and cached_data['available_slots']:
                                    slots = cached_data['available_slots'][:5]  # First 5 slots
                                    slots_text = self._format_time_slots(slots)
                                    email_name = args[0].split('@')[0].title() if args else "there"
                                    kwargs["body"] = f"""Dear {email_name},

I hope this message finds you well. I would like to schedule a meeting with you.

I have the following available time slots:

{slots_text}

Please let me know which time works best for you, and I'll send you a calendar invitation.

Best regards"""
                                else:
                                    email_name = args[0].split('@')[0].title() if args else "there"
                                    kwargs["body"] = f"""Dear {email_name},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                            except Exception as e:
                                logger.warning("Failed to parse cached availability", error=str(e))
                                email_name = args[0].split('@')[0].title() if args else "there"
                                kwargs["body"] = f"""Dear {email_name},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                        else:
                            # No cached availability - get fresh data
                            try:
                                from datetime import timedelta
                                now = datetime.now()
                                time_min = now.strftime("%Y-%m-%dT%H:%M:%S%z")
                                time_max = (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S%z")
                                
                                availability_result = tool_service.calendar_get_availability(
                                    time_min=time_min,
                                    time_max=time_max
                                )
                                
                                # Cache the result
                                self._cached_availability = availability_result
                                self._availability_cache_time = datetime.now()
                                
                                # Use the result
                                if availability_result and 'available_slots' in availability_result:
                                    slots = availability_result['available_slots'][:5]
                                    slots_text = self._format_time_slots(slots)
                                    email_name = args[0].split('@')[0].title() if args else "there"
                                    kwargs["body"] = f"""Dear {email_name},

I hope this message finds you well. I would like to schedule a meeting with you.

I have the following available time slots:

{slots_text}

Please let me know which time works best for you, and I'll send you a calendar invitation.

Best regards"""
                                else:
                                    email_name = args[0].split('@')[0].title() if args else "there"
                                    kwargs["body"] = f"""Dear {email_name},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                            except Exception as e:
                                logger.warning("Failed to get calendar availability", error=str(e))
                                email_name = args[0].split('@')[0].title() if args else "there"
                                kwargs["body"] = f"""Dear {email_name},

I hope this message finds you well. I would like to schedule a meeting with you.

I have some available time slots and would be happy to work around your schedule. Please let me know what times work best for you, and I'll send you a calendar invitation.

Best regards"""
                elif tool_name == "calendar_create_event":
                    if len(args) >= 3:
                        kwargs["summary"] = args[0]
                        kwargs["start_time"] = args[1]
                        kwargs["end_time"] = args[2]
                        kwargs["description"] = args[3] if len(args) > 3 else ""
                    else:
                        kwargs["summary"] = args[0] if args else ""
            
            # Cache calendar availability results to avoid duplicate API calls
            if tool_name == "calendar_get_availability":
                result = self._execute_tool_sync(tool_service, tool_name, kwargs)
                self._cached_availability = result
                self._availability_cache_time = datetime.now()
                return result
            
            return self._execute_tool_sync(tool_service, tool_name, kwargs)
        
        return tool_wrapper

    def _create_tools(self, tool_service) -> List[Tool]:
        """
        Convert existing tool service tools to LangChain tools.
        
        Args:
            tool_service: Existing tool service instance
            
        Returns:
            List of LangChain tools
        """
        tools = []
        
        # HubSpot tools
        tools.append(Tool(
            name="hubspot_search_contacts",
            func=self._create_tool_wrapper(tool_service, "hubspot_search_contacts"),
            description="Search for contacts in HubSpot CRM. Use this to find contact information by name or email."
        ))
        
        tools.append(Tool(
            name="hubspot_create_contact",
            func=self._create_tool_wrapper(tool_service, "hubspot_create_contact"),
            description="Create a new contact in HubSpot CRM."
        ))
        
        # Gmail tools
        tools.append(Tool(
            name="gmail_search",
            func=self._create_tool_wrapper(tool_service, "gmail_search"),
            description="Search Gmail emails. Use this to find emails from or to a specific person."
        ))
        
        tools.append(Tool(
            name="gmail_send",
            func=self._create_tool_wrapper(tool_service, "gmail_send"),
            description="""Send an email using Gmail. 
            
            CRITICAL: When sending meeting requests, you MUST provide the complete email content including time slots.
            
            Required format: gmail_send(to='email@example.com', subject='Meeting Request', body='Dear [Name], I would like to schedule a meeting. Available times: [list specific times from calendar_get_availability results]. Please let me know what works for you.')
            
            DO NOT just provide the email address - you MUST provide the complete email body with time slots."""
        ))
        
        # Calendar tools
        tools.append(Tool(
            name="calendar_get_availability",
            func=self._create_tool_wrapper(tool_service, "calendar_get_availability"),
            description="Get available time slots from calendar. Returns available time slots that should be included in meeting request emails. Always provide both time_min and time_max parameters in ISO format with timezone (e.g., '2025-10-13T09:00:00-04:00')."
        ))
        
        tools.append(Tool(
            name="calendar_create_event",
            func=self._create_tool_wrapper(tool_service, "calendar_create_event"),
            description="Create a calendar event. Requires summary, start_time, and end_time in ISO format."
        ))
        
        return tools
    
    def _execute_tool_sync(self, tool_service, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Execute a tool synchronously for LangChain.
        
        Args:
            tool_service: Tool service instance
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            
        Returns:
            Tool result as string
        """
        try:
            # This is a synchronous wrapper - in production, you'd want async
            import asyncio
            
            async def _async_execute():
                return await tool_service.execute_tool(tool_name, parameters, tool_service.user)
            
            result = asyncio.run(_async_execute())
            
            # Convert result to string for LangChain
            if isinstance(result, dict):
                if result.get("success"):
                    return json.dumps(result, indent=2)
                else:
                    return f"Error: {result.get('error', 'Unknown error')}"
            else:
                return str(result)
                
        except Exception as e:
            logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
            return f"Error executing {tool_name}: {str(e)}"
    
    def _create_agent_executor(self, tool_service, ongoing_instructions: List[Dict[str, Any]] = None, context: Optional[List[Dict[str, Any]]] = None):
        """
        Create LangChain agent executor with tools and prompt.
        
        Args:
            tool_service: Tool service instance
            ongoing_instructions: List of ongoing instructions
            context: RAG context from document retrieval
        """
        tools = self._create_tools(tool_service)
        
        # Create system prompt
        system_prompt = self._create_system_prompt(ongoing_instructions, context)
        
        # Escape all curly braces to prevent template variable interpretation
        # This is the standard solution for handling template variable conflicts
        import re
        
        # First, protect known template variables
        placeholders = {}
        placeholder_pattern = r'\{(input|chat_history|agent_scratchpad)\}'
        
        def protect_placeholder(match):
            key = f"__PLACEHOLDER_{len(placeholders)}__"
            placeholders[key] = match.group(0)
            return key
        
        system_prompt = re.sub(placeholder_pattern, protect_placeholder, system_prompt)
        
        # Now escape all remaining curly braces
        system_prompt = system_prompt.replace('{', '{{').replace('}', '}}')
        
        # Restore protected placeholders
        for key, value in placeholders.items():
            system_prompt = system_prompt.replace(key, value)
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        
        # Create agent
        agent = create_openai_tools_agent(self.llm, tools, prompt)
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,  # Allow multiple tool calls
            early_stopping_method="generate"
        )
    
    def _create_system_prompt(self, ongoing_instructions: List[Dict[str, Any]] = None, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Create system prompt for the agent.
        
        Args:
            ongoing_instructions: List of ongoing instructions
            context: RAG context from document retrieval
            
        Returns:
            System prompt string
        """
        # Get current date and time
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        current_time = datetime.now().strftime("%I:%M %p %Z")
        
        system_prompt = f"""You are a helpful AI assistant for financial advisors. You have access to Gmail, Google Calendar, and HubSpot CRM data.

Current Information:
- Today's date: {current_date}
- Current time: {current_time}

Core Capabilities:
- Answer questions about clients, meetings, and communications
- Schedule appointments and manage calendar events
- Send emails and manage communications
- Create and update CRM contacts and notes

Core Behavior:
- Execute multiple tools in sequence without asking permission
- Use fallback tools automatically if primary tool fails
- Complete multi-step processes before providing summary
- Be proactive and take action immediately
- When searching contacts: First try HubSpot, then Gmail if HubSpot fails
- When HubSpot access fails, immediately try Gmail search instead
- For calendar operations: Always use ISO format with timezone (e.g., '2025-10-13T09:00:00-04:00')
- For date ranges: Use reasonable business hours (9 AM to 5 PM) and next 5 business days
- When calling calendar_get_availability: ALWAYS provide both time_min and time_max parameters

Appointment Scheduling Process:
- When scheduling appointments: DO NOT create calendar events immediately
- For appointment requests: First search for the contact, get available times, send email with options
- Process: Search contact → Get available times → Send email with options → Wait for response → Take action based on response
- **IMPORTANT: When sending emails for meeting requests, ALWAYS include the specific available time slots in the email body**
- **IMPORTANT: Use the calendar availability results to create a detailed email with specific dates and times**
- **IMPORTANT: Format time slots clearly in the email (e.g., "Monday, October 13, 2025 from 9:00 AM to 9:30 AM (EDT)")**
- If contact picks a time: Create calendar event and send confirmation
- If contact says no times work: Send new available times and follow up
- If contact suggests different times: Check availability and respond accordingly
- Be flexible and handle all edge cases through conversation
- Only create calendar events after the contact confirms a specific time

Available Tools:
- hubspot_search_contacts: Search HubSpot contacts
- hubspot_create_contact: Create HubSpot contacts
- gmail_search: Search Gmail emails
- gmail_send: Send emails
- calendar_get_availability: Get available time slots
- calendar_create_event: Create calendar events

Use these tools to help the advisor manage their client relationships effectively."""
        
        # Add RAG context if available
        if context:
            context_text = "\n\nRelevant Context from Documents:\n"
            for item in context:
                content = item.get('content', '')
                source = item.get('source', 'Unknown')
                context_text += f"- {content}\n  (Source: {source})\n"
            system_prompt += context_text
        
        # Add ongoing instructions
        if ongoing_instructions:
            instructions_text = "\n\nOngoing Instructions (apply when relevant):\n"
            for instruction in ongoing_instructions:
                instructions_text += f"- {instruction.get('description', instruction.get('title', 'Unknown instruction'))}\n"
            system_prompt += instructions_text
        
        return system_prompt
    
    def chunk_text(self, text: str, max_length: int = 1000) -> List[str]:
        """
        Chunk text into smaller pieces for processing using LangChain's text splitter.
        
        Args:
            text: Text to chunk
            max_length: Maximum length per chunk (used to configure splitter)
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        # Use LangChain's text splitter
        documents = self.text_splitter.split_text(text)
        return documents
    
    def get_query_hash(self, query: str) -> str:
        """
        Generate a hash for the query to use for caching.
        
        Args:
            query: Query text
            
        Returns:
            str: Hash of the query
        """
        return hashlib.md5(query.encode()).hexdigest()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using OpenAI embeddings.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Embedding vector
        """
        embedding = await self.embeddings.aembed_query(text)
        return embedding
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using OpenAI embeddings.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        embeddings = await self.embeddings.aembed_documents(texts)
        return embeddings
    
    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        Summarize text using the LLM.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            str: Summarized text
        """
        if len(text) <= max_length:
            return text
        
        try:
            # Use LangChain's LLM to generate a summary
            prompt = f"""Please summarize the following text in {max_length} characters or less:

{text}

Summary:"""
            
            response = await self.llm.ainvoke(prompt)
            summary = response.content.strip()
            
            # Ensure summary doesn't exceed max_length
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
        except Exception as e:
            logger.error("Failed to summarize text", error=str(e))
            # Fallback to simple truncation
            return text[:max_length-3] + "..." if len(text) > max_length else text
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        ongoing_instructions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
        tool_service: Optional[Any] = None,
        user: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate chat completion using LangChain agent.
        
        Args:
            messages: List of chat messages
            user_id: User ID
            context: Additional context
            ongoing_instructions: List of ongoing instructions
            tools: Available tools (not used in LangChain version)
            stream: Whether to stream response
            tool_service: Tool service instance
            user: User instance
            
        Yields:
            Response chunks
        """
        try:
            # Set user in tool service for authentication
            if tool_service and user:
                tool_service.user = user
            
            # Create agent executor if not exists
            if not self.agent_executor:
                self._create_agent_executor(tool_service, ongoing_instructions or [], context)
            
            # Get the last user message
            user_message = messages[-1]["content"] if messages else ""
            
            # Execute agent
            result = await self.agent_executor.ainvoke({"input": user_message})
            
            # Yield content chunks (simulate streaming)
            content = result["output"]
            chunk_size = 50  # Characters per chunk
            
            for i in range(0, len(content), chunk_size):
                chunk_content = content[i:i + chunk_size]
                yield {
                    "type": "content",
                    "content": chunk_content,
                    "role": "assistant"
                }
            
            # Yield final chunk
            yield {
                "type": "finish",
                "content": result["output"],
                "role": "assistant",
                "finish_reason": "stop",
                "model_used": self.model,
                "tool_calls": []  # LangChain handles tools internally
            }
            
        except Exception as e:
            logger.error("LangChain chat completion failed", error=str(e), user_id=user_id)
            
            # Yield error response
            yield {
                "type": "content",
                "content": "I apologize, but I encountered an error while processing your request. Please try again.",
                "role": "assistant"
            }
            
            yield {
                "type": "finish",
                "content": "I apologize, but I encountered an error while processing your request. Please try again.",
                "role": "assistant",
                "finish_reason": "error"
            }

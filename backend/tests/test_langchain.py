#!/usr/bin/env python3
"""
Test script for LangChain AI service.

This script tests the LangChain implementation
without requiring the full backend server.
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.langchain_service import LangChainService
from app.services.tool_service import ToolService
from app.core.database import get_db
from app.models.user import User


class MockUser:
    """Mock user for testing."""
    def __init__(self):
        self.id = "test-user-id"
        self.has_google_access = True
        self.has_hubspot_access = True


async def test_langchain_service():
    """Test the LangChain AI service."""
    print("🧪 Testing LangChain AI Service")
    print("=" * 50)
    
    try:
        # Initialize services
        langchain_service = LangChainService()
        
        # Create mock tool service
        class MockToolService:
            def __init__(self):
                self.user = MockUser()
            
            async def execute_tool(self, tool_name: str, parameters: dict, user):
                """Mock tool execution."""
                print(f"🔧 Mock tool execution: {tool_name} with {parameters}")
                
                # Mock responses for different tools
                if tool_name == "hubspot_search_contacts":
                    return {
                        "success": True,
                        "contacts": [
                            {"name": "Yamada Tomoya", "email": "yamada@example.com"}
                        ]
                    }
                elif tool_name == "calendar_get_availability":
                    return {
                        "success": True,
                        "available_slots": [
                            {"start": "2025-10-13T10:00:00-04:00", "end": "2025-10-13T10:30:00-04:00"},
                            {"start": "2025-10-13T14:00:00-04:00", "end": "2025-10-13T14:30:00-04:00"}
                        ]
                    }
                elif tool_name == "gmail_send":
                    return {
                        "success": True,
                        "message_id": "test-message-id"
                    }
                else:
                    return {"success": True, "result": f"Mock {tool_name} executed"}
        
        tool_service = MockToolService()
        
        # Test simple message
        print("\n📝 Test 1: Simple message")
        messages = [{"role": "user", "content": "Hello, how are you?"}]
        
        response_chunks = []
        async for chunk in langchain_service.chat_completion(
            messages=messages,
            user_id="test-user",
            tool_service=tool_service,
            user=MockUser(),
            stream=False
        ):
            response_chunks.append(chunk)
            if chunk["type"] == "content":
                print(f"🤖 AI Response: {chunk['content']}")
        
        # Test appointment scheduling
        print("\n📅 Test 2: Appointment scheduling")
        messages = [{"role": "user", "content": "Schedule a meeting with Yamada"}]
        
        response_chunks = []
        async for chunk in langchain_service.chat_completion(
            messages=messages,
            user_id="test-user",
            tool_service=tool_service,
            user=MockUser(),
            stream=False
        ):
            response_chunks.append(chunk)
            if chunk["type"] == "content":
                print(f"🤖 AI Response: {chunk['content']}")
        
        print("\n✅ LangChain service test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_langchain_service())

import os
import uuid
import requests
import streamlit as st
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

os.environ["STREAMLIT_SERVER_ENABLE_STATIC_FILE_WATCHER"] = "false"

API_BASE_URL = "http://localhost:8000/api"  # Update with your actual API URL

# Schema definitions matching backend
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = None
    thread_id: Optional[str] = None

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool

class ChatResponse(BaseModel):
    thread_id: str
    response: str
    requires_approval: bool = False
    tool_details: Optional[Dict[str, Any]] = None

def initialize_session():
    """Initialize session state variables if they don't exist"""
    session_defaults = {
        "messages": [],  # Chat messages
        "pending_approval": None,  # Details about pending tool call
        "user_id": 1,  # Default customer ID
        "thread_id": None,  # Current thread ID
        "loaded_thread_id": None  # Loaded thread ID for reference
    }
    
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Generate a new thread_id if none exists
    if not st.session_state.thread_id:
        st.session_state.thread_id = str(uuid.uuid4())

def send_chat_request(message: str) -> Dict[str, Any]:
    """Send chat message to the backend API"""
    try:
        payload = ChatRequest(
            message=message,
            user_id=st.session_state.user_id,
            thread_id=st.session_state.thread_id
        ).model_dump()
        
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=payload,
            timeout=30  # Increased timeout for longer processing
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def send_approval(approved: bool) -> Dict[str, Any]:
    """Send approval decision to the backend API"""
    try:
        payload = ApprovalRequest(
            thread_id=st.session_state.thread_id,
            approved=approved
        ).model_dump()
        
        response = requests.post(
            f"{API_BASE_URL}/approve",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"Approval Error: {str(e)}")
        return None

def load_conversation(thread_id: str) -> bool:
    """Load an existing conversation by thread ID"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/conversation/{thread_id}",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Update session state with loaded conversation
        st.session_state.messages = format_messages_for_display(data.get("messages", []))
        st.session_state.thread_id = thread_id
        st.session_state.loaded_thread_id = thread_id
        st.session_state.user_id = data.get("user_id")
        st.session_state.pending_approval = None
        
        return True
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading conversation: {str(e)}")
        return False

def format_messages_for_display(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format messages from API response for Streamlit display"""
    formatted_messages = []
    
    for msg in messages:
        msg_type = msg.get("type")
        if msg_type == "human":
            formatted_messages.append({
                "role": "user",
                "content": msg.get("content", "")
            })
        elif msg_type == "ai":
            formatted_messages.append({
                "role": "assistant",
                "content": msg.get("content", "")
            })
        elif msg_type == "tool":
            # Optional: Display tool messages if needed
            formatted_messages.append({
                "role": "system",
                "content": f"Tool '{msg.get('name')}' executed: {msg.get('content', '')}"
            })
    
    return formatted_messages

def main():
    st.set_page_config(
        page_title="Chat Assistant",
        page_icon="💬",
        layout="wide"
    )
    
    initialize_session()
    
    with st.sidebar:
        st.title("Chat Settings")
        
        # Customer ID management
        new_user_id = st.number_input(
            "Customer ID",
            min_value=1,
            value=st.session_state.user_id,
            key="customer_input"
        )
        
        if st.button("Update Customer ID"):
            if new_user_id != st.session_state.user_id:
                st.session_state.user_id = new_user_id
                # Reset conversation if customer ID changes
                if not st.session_state.loaded_thread_id:
                    st.session_state.thread_id = str(uuid.uuid4())
                    st.session_state.messages = []
                st.toast(f"Customer ID updated to {new_user_id}")
                st.rerun()
        
        # Thread ID management
        st.divider()
        st.subheader("Conversation Management")
        
        # Thread ID input
        thread_id_input = st.text_input(
            "Enter Thread ID to load",
            key="thread_id_input",
            value=st.session_state.loaded_thread_id or ""
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Load Conversation"):
                if thread_id_input:
                    with st.spinner("Loading conversation..."):
                        success = load_conversation(thread_id_input)
                        if success:
                            st.toast(f"Loaded conversation {thread_id_input}")
                            st.rerun()
                else:
                    st.error("Please enter a Thread ID")
        
        with col2:
            if st.button("🆕 New Conversation"):
                # Generate new thread ID for a fresh conversation
                st.session_state.thread_id = str(uuid.uuid4())
                st.session_state.messages = []
                st.session_state.pending_approval = None
                st.session_state.loaded_thread_id = None
                st.toast("Started new conversation")
                st.rerun()
        
        # Display current thread ID
        if st.session_state.thread_id:
            st.markdown(f"""**Current Thread ID:**  `{st.session_state.thread_id}`""")
            
            # Copy button for thread ID
            if st.button("📋 Copy Thread ID"):
                st.write("Thread ID copied to clipboard!")
                st.toast("Thread ID copied to clipboard!")
    
    # Main chat interface
    st.title("Chat Assistant")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Handle pending approvals
    if st.session_state.pending_approval:
        st.warning("Action Requires Approval")
        with st.expander("Approval Details", expanded=True):
            st.json(st.session_state.pending_approval)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve Action", use_container_width=True):
                handle_approval(True)
        with col2:
            if st.button("❌ Deny Action", use_container_width=True):
                handle_approval(False)
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        process_message(prompt)

def process_message(prompt: str):
    """Process user message and get response from API"""
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Show user message immediately
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.spinner("Processing..."):
        response = send_chat_request(prompt)
        
        if response:
            if response.get("requires_approval"):
                # Store pending approval details
                st.session_state.pending_approval = response.get("tool_details")
            else:
                # Add assistant response to chat history
                assistant_msg = {
                    "role": "assistant",
                    "content": response.get("response", "No response received")
                }
                st.session_state.messages.append(assistant_msg)
                
                # Show assistant message
                with st.chat_message("assistant"):
                    st.write(assistant_msg["content"])
            
            st.rerun()

def handle_approval(approved: bool):
    """Handle user's approval decision"""
    with st.spinner("Processing approval..."):
        response = send_approval(approved)
        
        if response:
            if not approved:
                st.session_state.messages.append({
                    "role": "system",
                    "content": "Action was denied."
                })
            else:
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.get("response", "Approval processed")
                })
            
            # Clear pending approval
            st.session_state.pending_approval = None
            st.rerun()

if __name__ == "__main__":
    main()
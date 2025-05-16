import streamlit as st
import json
import uuid
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from app.services.assistant import graph

class StreamlitChatTester:
    def __init__(self):
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "thread_id" not in st.session_state:
            st.session_state.thread_id = str(uuid.uuid4())
            
        if "pending_approval" not in st.session_state:
            st.session_state.pending_approval = None
            
        self.config = {
            "configurable": {
                "user_id": 3,
                "thread_id": st.session_state.thread_id,
            }
        }
        
    def reset_chat(self):
        """Reset the chat history and create a new thread"""
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.pending_approval = None
        self.config["configurable"]["thread_id"] = st.session_state.thread_id
        
    def process_events(self, event):
        """Process events from the graph and extract messages"""
        tool_call = None
        
        if isinstance(event, dict) and "messages" in event:
            messages = event["messages"]
            last_message = messages[-1] if messages else None
            
            if isinstance(last_message, AIMessage):
                if last_message.content:
                    st.session_state.messages.append(last_message)
                
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    tool_call = last_message.tool_calls[0]
                    
        return tool_call
        
    def handle_user_input(self):
        """Process user input from the chat input field"""
        if st.session_state.user_input and st.session_state.user_input.strip():
            user_input = st.session_state.user_input.strip()
            
            # Add user message to chat history
            human_message = HumanMessage(content=user_input)
            st.session_state.messages.append(human_message)
            
            try:
                with st.spinner("Assistant is thinking..."):
                    events = list(
                        graph.stream(
                            {"messages": st.session_state.messages},
                            self.config,
                            stream_mode="values",
                        )
                    )
                    
                    last_event = events[-1]
                    tool_call = self.process_events(last_event)
                    
                    if tool_call:
                        st.session_state.pending_approval = tool_call
                        st.rerun()
            except Exception as e:
                st.error(f"Error processing message: {str(e)}")
                
    def handle_tool_approval(self, approve):
        """Handle tool approval response"""
        tool_call = st.session_state.pending_approval
        
        try:
            if approve:
                result = graph.invoke(None, self.config)
                self.process_events(result)
            else:
                result = graph.invoke(
                    {
                        "messages": [
                            ToolMessage(
                                tool_call_id=tool_call["id"],
                                content="API call denied by user.",
                                name=tool_call["name"]
                            )
                        ]
                    },
                    self.config,
                )
                self.process_events(result)
        except Exception as e:
            st.error(f"Error processing {'approval' if approve else 'denial'}: {str(e)}")
            
        st.session_state.pending_approval = None
        st.rerun()
    
    def display_chat_history(self):
        """Display the chat messages in the Streamlit UI"""
        # Welcome message when no messages
        if not st.session_state.messages:
            st.chat_message("assistant").write("Welcome! How can I assist you today?")
            return
            
        # Display existing chat messages
        for message in st.session_state.messages:
            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.write(message.content)
            elif isinstance(message, AIMessage):
                with st.chat_message("assistant"):
                    st.write(message.content)
                    
    def display_tool_approval(self):
        """Display tool approval interface"""
        tool_call = st.session_state.pending_approval
        
        with st.container():
            st.warning("The assistant wants to perform an action:")
            
            st.subheader(f"Function: {tool_call['name']}")
            
            try:
                args_formatted = json.dumps(tool_call["args"], indent=2)
                st.code(args_formatted, language="json")
            except:
                st.code(str(tool_call["args"]))
                
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Approve", key="approve_btn", type="primary"):
                    self.handle_tool_approval(True)
            with col2:
                if st.button("Deny", key="deny_btn"):
                    self.handle_tool_approval(False)
    
    def render(self):
        """Main method to render the Streamlit interface"""
        st.title("Agent Testing Interface")
        
        # Sidebar with options
        with st.sidebar:
            st.header("Settings")
            st.button("Reset Chat", on_click=self.reset_chat)
            st.write(f"Thread ID: {st.session_state.thread_id}")
        
        # Display chat history
        self.display_chat_history()
        
        # Display tool approval if needed
        if st.session_state.pending_approval:
            self.display_tool_approval()
        else:
            # Chat input - Streamlit will automatically clear this after submission
            st.chat_input(
                placeholder="Type your message here...",
                key="user_input",
                on_submit=self.handle_user_input
            )

if __name__ == "__main__":
    st.set_page_config(
        page_title="Agent Testing Interface",
        page_icon="🤖",
        layout="wide"
    )
    
    # Apply some custom CSS
    st.markdown("""
    <style>
    .stButton button {
        width: 100%;
    }
    .stSpinner > div > div {
        border-top-color: #4169E1 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    chat_tester = StreamlitChatTester()
    chat_tester.render()
import json
import uuid
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from app.services.assistant import graph

class TerminalChatTester:
    def __init__(self):
        self.messages = []
        self.thread_id = str(uuid.uuid4())
        self.pending_approval = None
        self.config = {
            "configurable": {
                "user_id": 3,
                "thread_id": self.thread_id,
            }
        }
        self.running = True
        
    def display_chat_history(self):
        """Display current chat history in terminal"""
        if not self.messages:
            print("\n Welcome! How can I assist you today?\n")
            return
            
        for message in self.messages:
            if isinstance(message, HumanMessage):
                print(f"\n[USER]: {message.content}")
            elif isinstance(message, AIMessage):
                print(f"\n[ASSISTANT]: {message.content}")
                
    def process_events(self, event):
        """Process events from the graph and extract messages"""
        tool_call = None
        
        if isinstance(event, dict) and "messages" in event:
            messages = event["messages"]
            last_message = messages[-1] if messages else None
            
            if isinstance(last_message, AIMessage):
                if last_message.content:
                    self.messages.append(last_message)
                    print(f"\n[ASSISTANT]: {last_message.content}")
                
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    tool_call = last_message.tool_calls[0]
                    
        return tool_call
        
    def handle_tool_approval(self, tool_call):
        """Handle tool approval in terminal"""
        print("\n The assistant wants to perform an action. Do you approve?")
        print(f"\n Function: {tool_call['name']}")
        
        try:
            args_formatted = json.dumps(tool_call["args"], indent=2)
            print(f"Arguments:\n{args_formatted}")
        except:
            print(f"Arguments: {tool_call['args']}")
            
        while True:
            choice = input("\nApprove? (y/n): ").lower().strip()
            
            if choice in ['y', 'yes']:
                print("\nProcessing approval...")
                try:
                    result = graph.invoke(None, self.config)
                    self.process_events(result)
                    self.pending_approval = None
                    break
                except Exception as e:
                    print(f"Error processing approval: {str(e)}")
                    
            elif choice in ['n', 'no']:
                print("\nAction denied.")
                try:
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
                    self.pending_approval = None
                    break
                except Exception as e:
                    print(f"Error processing denial: {str(e)}")
            else:
                print("Invalid input. Please enter 'y' or 'n'.")
    
    def run(self):
        """Run the terminal chat test interface"""
        print("\n===== AGENT TESTING TERMINAL =====")
        print("Type 'exit' or 'quit' to end the session")
        print("===================================\n")
        
        self.display_chat_history()
        
        while self.running:
            if self.pending_approval:
                self.handle_tool_approval(self.pending_approval)
                continue
                
            prompt = input("\n[YOU]: ")
            
            if prompt.lower() in ['exit', 'quit']:
                self.running = False
                print("\nEnding test session. Goodbye!")
                break
                
            if prompt:
                human_message = HumanMessage(content=prompt)
                self.messages.append(human_message)
                
                try:
                    print("\nThinking...")
                    events = list(
                        graph.stream(
                            {"messages": self.messages},
                            self.config,
                            stream_mode="values",
                        )
                    )
                    
                    last_event = events[-1]
                    tool_call = self.process_events(last_event)
                    
                    if tool_call:
                        self.pending_approval = tool_call  
                            
                except Exception as e:
                    print(f"Error processing message: {str(e)}")

if __name__ == "__main__":
    tester = TerminalChatTester()
    tester.run()

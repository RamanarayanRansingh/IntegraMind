from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

def serialize_message(message):
    """Serialize LangChain messages for JSON storage"""
    if isinstance(message, HumanMessage):
        return {"type": "human", "content": message.content}
    elif isinstance(message, AIMessage):
        msg_dict = {"type": "ai", "content": message.content}
        if hasattr(message, "tool_calls") and message.tool_calls:
            msg_dict["tool_calls"] = message.tool_calls
        return msg_dict
    elif isinstance(message, ToolMessage):
        return {
            "type": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
            "name": message.name
        }
    return {"type": "unknown", "content": str(message)}

def deserialize_message(message_dict):
    """Deserialize messages from JSON storage to LangChain messages"""
    if message_dict["type"] == "human":
        return HumanMessage(content=message_dict["content"])
    elif message_dict["type"] == "ai":
        msg = AIMessage(content=message_dict["content"])
        if "tool_calls" in message_dict:
            msg.tool_calls = message_dict["tool_calls"]
        return msg
    elif message_dict["type"] == "tool":
        return ToolMessage(
            content=message_dict["content"],
            tool_call_id=message_dict["tool_call_id"],
            name=message_dict["name"]
        )
    return HumanMessage(content=str(message_dict))
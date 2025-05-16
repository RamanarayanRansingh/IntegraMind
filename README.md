# IntegraMind

![IntegraMind Logo](./images/integramind_logo.png)

## An Intelligent Framework for Unified Assessment and Intervention in Dual Diagnosis

IntegraMind is a novel graph-based chatbot framework that simultaneously addresses co-occurring mental health disorders and substance use disorders (SUDs) through a unified system. This framework employs a multi-agent architecture implemented with LangGraph, where specialized agents handle distinct conversation aspects while collaborating to provide comprehensive support.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 🌟 Features

- **Multi-agent Architecture**: Specialized agents for conversation management, assessment, knowledge retrieval, and safety protocols
- **Integrated Assessment Tools**: Seamlessly embeds validated clinical assessments (PHQ-9, GAD-7, DAST-10, CAGE) into natural conversation
- **Evidence-Based Support**: Utilizes Retrieval-Augmented Generation (RAG) to deliver contextually relevant therapeutic content
- **Human-in-the-Loop Safety**: Automatically alerts therapists when crisis indicators are detected
- **Unified Approach**: Addresses both mental health and substance use concerns simultaneously

## 📊 System Architecture

The system is designed as a directed graph where each node represents a functional component with specific responsibilities.

![System Architecture](./images/fig_1.png)

### Agent Graph Structure

IntegraMind's multi-agent structure enables modular development and clear separation of concerns.

![Agent Graph](./images/graph.png)

## 🔄 Key Components

### 1. Assessment Integration

IntegraMind naturally embeds clinical assessments into the conversation flow, making the process feel natural and engaging.

![PHQ-9 Integration](./images/fig_2.png)

After completing assessments, users receive feedback on their results:

![Assessment Results](./images/fig_3.png)

### 2. Safety Protocol System

A tiered risk assessment protocol with human oversight ensures user safety:

![Crisis Response Interface](./images/fig_4.png)

For Level 3 and Level 4 situations, the system notifies the designated therapist:

![Email Notification](./images/fig_5.png)

### 3. Knowledge Base Structure

The knowledge base is organized into four main categories:
- CBT Exercises and Worksheets
- Psychoeducational Materials
- Crisis Protocols and Safety Planning
- Evidence-Based Intervention Guides

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/integramind.git
   cd integramind
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. Run the application:
   ```bash
   python src/main.py
   ```

## 📝 Usage Example

```python
from integramind import IntegraMindApp

# Initialize the application
app = IntegraMindApp(
    api_key="your_api_key",
    knowledge_base_path="path/to/knowledge_base"
)

# Start a conversation
response = app.chat("I've been feeling really down lately and drinking more than usual.")
print(response)
```

## 📊 Comparative Advantages

| Feature | IntegraMind | Traditional Chatbots |
|---------|-------------|----------------------|
| Integrated assessment | Embeds validated tools for both mental health and SUDs | May include only mental health or only SUD assessments |
| Crisis detection | Multi-level risk assessment with substance-specific protocols | Limited to specific crisis types or generic detection |
| Human oversight | Automated therapist alerts with detailed clinical context | Limited or no human involvement |
| Knowledge foundation | Evidence-based content for co-occurring disorders | Single domain focus |
| Architecture | Graph-based multi-agent system with specialized nodes | Typically single-agent or rule-based |

## 🧠 Technical Implementation

The system is implemented using Python with the following key libraries:
- LangChain and LangGraph: For the agentic architecture and graph-based orchestration
- Google Generative AI: As the underlying large language model
- SQLite: For persistent state management and checkpoint storage

Core implementation of the state graph:

```python
# Build the state graph
builder = StateGraph(State)

# Add nodes
builder.add_node("assistant", MentalHealthAssistant(assistant_runnable))
builder.add_node("assessment_tools", create_tool_node_with_fallback(assessment_tools))
builder.add_node("safety_tools", create_tool_node_with_fallback(safety_tools))
builder.add_node("knowledge_tools", create_tool_node_with_fallback(knowledge_tools))

# Define routing function and add edges
# ... (see documentation for full implementation)
```

## 🔮 Future Directions

- Large-scale clinical validation studies
- Language and cultural adaptation for diverse populations
- Enhanced longitudinal engagement capabilities
- Integration with electronic health records and care systems

## 📄 Citation

If you use IntegraMind in your research, please cite:

```
@article{agarwal2025integramind,
  title={IntegraMind: An Intelligent Framework for Unified Assessment and Intervention in Dual Diagnosis},
  author={Agarwal, Arun and Ransingh, Ramanarayan},
  journal={},
  year={2025}
}
```

## 📜 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to the mental health professionals who provided feedback during early development
- Powered by LangChain's LangGraph framework

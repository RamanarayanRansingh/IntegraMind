# IntegraMind

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.0-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.22.0-red.svg)](https://streamlit.io/)


> An Intelligent Framework for Unified Assessment and Intervention in Dual Diagnosis

IntegraMind is a novel graph-based chatbot framework that simultaneously addresses co-occurring mental health disorders and substance use disorders (SUDs) through a unified system. This framework employs a multi-agent architecture implemented with LangGraph, where specialized agents handle distinct conversation aspects while collaborating to provide comprehensive support.

![System Architecture](./images/fig_1.png)

## 🌟 Features

- **Multi-agent Architecture**: Specialized agents for conversation management, assessment, knowledge retrieval, and safety protocols
- **Integrated Assessment Tools**: Seamlessly embeds validated clinical assessments (PHQ-9, GAD-7, DAST-10, CAGE) into natural conversation
- **Evidence-Based Support**: Utilizes Retrieval-Augmented Generation (RAG) to deliver contextually relevant therapeutic content
- **Human-in-the-Loop Safety**: Automatically alerts therapists when crisis indicators are detected
- **Unified Approach**: Addresses both mental health and substance use concerns simultaneously

## 📊 System Architecture

The system is designed as a directed graph where each node represents a functional component with specific responsibilities.

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

<div align="center">
  <table>
    <tr>
      <th>Category</th>
      <th>Contents</th>
    </tr>
    <tr>
      <td>📝 CBT Exercises and Worksheets</td>
      <td>Thought record sheets, cognitive restructuring guides, behavioral activation worksheets, substance use tracking diaries, relapse prevention exercises</td>
    </tr>
    <tr>
      <td>📚 Psychoeducational Materials</td>
      <td>Anxiety and depression self-help guides, substance use disorder information, co-occurring disorders resources</td>
    </tr>
    <tr>
      <td>🚨 Crisis Protocols and Safety Planning</td>
      <td>Safety plan templates, suicide risk assessment guides, crisis intervention protocols, substance-related emergency procedures</td>
    </tr>
    <tr>
      <td>🔍 Evidence-Based Intervention Guides</td>
      <td>Treatment manuals for substance use, guidelines for co-occurring disorders, best practice recommendations</td>
    </tr>
  </table>
</div>

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

## 📝 Running the Application

### FastAPI Backend

The IntegraMind backend is built with FastAPI, which provides the API endpoints for the chatbot functionality.

1. Start the FastAPI server:
   ```bash
   # Navigate to the backend directory
   cd backend
   
   # Start the FastAPI server with hot reload enabled
   uvicorn app.main:app --reload
   ```

2. The API documentation will be available at:
   ```
   http://localhost:8000/docs
   ```

### Streamlit Frontend

The user interface is built with Streamlit for an interactive chat experience.

1. Start the Streamlit application:
   ```bash
   # Navigate to the frontend directory
   cd frontend
   
   # Run the Streamlit app
   streamlit run app.py
   ```

2. Access the web interface at:
   ```
   http://localhost:8501
   ```

## 📊 Comparative Advantages

<div align="center">
  <table>
    <tr>
      <th>Feature</th>
      <th>IntegraMind</th>
      <th>Traditional Chatbots</th>
    </tr>
    <tr>
      <td><b>Integrated assessment</b></td>
      <td>✅ Embeds validated tools for both mental health and SUDs</td>
      <td>❌ May include only mental health or only SUD assessments</td>
    </tr>
    <tr>
      <td><b>Crisis detection</b></td>
      <td>✅ Multi-level risk assessment with substance-specific protocols</td>
      <td>❌ Limited to specific crisis types or generic detection</td>
    </tr>
    <tr>
      <td><b>Human oversight</b></td>
      <td>✅ Automated therapist alerts with detailed clinical context</td>
      <td>❌ Limited or no human involvement</td>
    </tr>
    <tr>
      <td><b>Knowledge foundation</b></td>
      <td>✅ Evidence-based content for co-occurring disorders</td>
      <td>❌ Single domain focus</td>
    </tr>
    <tr>
      <td><b>Architecture</b></td>
      <td>✅ Graph-based multi-agent system with specialized nodes</td>
      <td>❌ Typically single-agent or rule-based</td>
    </tr>
  </table>
</div>

## 🧠 Technical Implementation

The system is implemented using a modern tech stack:

- **Backend**: FastAPI for high-performance API endpoints
- **Frontend**: Streamlit for an interactive user interface
- **AI Engine**: LangChain and LangGraph for the agentic architecture and conversation flow
- **LLM Integration**: Google Generative AI as the underlying language model
- **Database**: SQLite for persistent state management

## 🔮 Future Directions

<div align="center">
  <table>
    <tr>
      <td align="center">🔬</td>
      <td><b>Clinical Validation</b>: Large-scale studies to measure effectiveness and outcomes</td>
    </tr>
    <tr>
      <td align="center">🌍</td>
      <td><b>Cultural Adaptation</b>: Extending support for diverse languages and cultural contexts</td>
    </tr>
    <tr>
      <td align="center">📈</td>
      <td><b>Longitudinal Engagement</b>: Enhancing personalization over extended periods of use</td>
    </tr>
    <tr>
      <td align="center">🏥</td>
      <td><b>Healthcare Integration</b>: Connecting with electronic health records and care systems</td>
    </tr>
    <tr>
      <td align="center">🧪</td>
      <td><b>Machine Learning</b>: Developing predictive models for intervention effectiveness</td>
    </tr>
  </table>
</div>

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

## 👥 Contributors

- Arun Agarwal (arunagrawal@soa.ac.in)
- Ramanarayan Ransingh (ramanarayanransingh@gmail.com)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to the mental health professionals who provided feedback during early development
- Powered by LangChain's LangGraph framework

# ConverseAgent

A powerful framework for building custom AI agents using Amazon Bedrock and the Converse API. ConverseAgent provides a flexible foundation for creating, customizing, and deploying AI-powered systems with advanced capabilities.

DISCLAIMER: The provided sample code are only for experimenting and reference. It is not meant to be used directly in production deployments. It is currently being developed and can have breaking changes.

[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-yellow.svg)](https://opensource.org/licenses/MIT-0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blue)](https://python-poetry.org/)

## 🌟 Features

- **Flexible Input Processing**: Handle text, images, and documents seamlessly
- **Customizable Agent Runtime**: Modify agent behavior to suit your needs
- **Advanced Tool Integration**:
  - Local and external tool execution
  - Extensible tool framework
- **Amazon Bedrock Integration**:
  - Knowledge Base support with dynamic metadata filtering
  - Multiple model support
- **Modular Architecture**: Build and extend functionality with ease

## 📋 Prerequisites

- AWS Account with appropriate permissions
- Python 3.11 or later
- AWS IAM user with access to:
  - Amazon Bedrock
  - Supported foundation models
- AWS CLI installed and configured
- virtualenv or conda
- Poetry (Python dependency management)
- Make (for using Makefile commands)
- Git
- Node.js 18.18 or later

## 🚀 Installation

## Development Environment Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/aws-samples/sample-aws-field-samples.git
   cd ConverseAgent
   ```

2. **Install Dependencies**

If using venv and pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

If using poetry:

```bash
# Install all dependencies including development tools
make build
make install
poetry install --with extras, ui
```

### Development Installation

Follow the [Developer Guide](./DEVELOPER-GUIDE.md)

## 🏃‍♂️ Quick Start

### Basic Usage

```python
from converseagent.agents import BaseAgent
from converseagent.messages import UserMessage
from converseagent.models.bedrock import BedrockModel

# Initialize the agent
bedrock_model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
model = BedrockModel(bedrock_model_id=bedrock_model_id)
agent = BaseAgent(model=model)

# Create and send a message
user_message = UserMessage(text="Hey, how's it going?")
response = agent.invoke(user_message=user_message)

print(response["body"]["text"])
```

## 📚 Documentation

For more detailed information and examples:

- [Sample Notebooks](./notebooks)
- [Developer Guide](./DEVELOPER-GUIDE.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./DEVELOPER-GUIDE.md) for details on:

- Setting up your development environment
- Running tests
- Submitting pull requests
- Coding standards

## 📜 License

This project is licensed under the MIT-0 License - see the [LICENSE.md](./LICENSE.md) file for details.

## 📞 Support

- Create an Issue

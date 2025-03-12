# Developer Guide

Welcome to the ConverseAgent developer guide! This document will help you set up your development environment and understand how to contribute to the project effectively.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Style and Standards](#code-style-and-standards)
- [UI Development](#ui-development)

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.11 or later
- Poetry (Python dependency management)
- Make (for using Makefile commands)
- Git

Required development tools (automatically installed via Poetry):

- ruff: linter and code formatter
- bandit: security tool
- pytest: Testing framework
- pytest-cov: Test coverage reporting

## Development Environment Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/aws-samples/sample-aws-field-samples.git
   cd ConverseAgent
   ```

2. **Create a virtual environment**
   Use virtualenv or conda to create your environment.
   Make sure to update pip as well.

   If using virtualenv:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

   If using conda:

   ```bash
   conda create -n converseagent python=3.11
   conda activate converseagent
   pip install -U pip
   ```

3. **Install Dependencies**

   ```bash
   # Install all dependencies including development tools
   make build
   make install
   ```

4. **Configure AWS Credentials**

   - Ensure you have AWS credentials configured with access to Amazon Bedrock
   - Set up your AWS profile in `~/.aws/credentials` or use environment variables

5. **Install Optional Dependencies**

   ```bash
   # For converseagent_extras
   poetry install --extras "extras"

   # For webui development
   poetry install --extras "ui"
   ```

## Project Structure

```
src
├── converseagent                      # Main package directory
│   ├── agents                         # Core agent implementations and conversation handlers
│   │   └── base                       # Base agent classes and interfaces
│   ├── content                        # Content blocks such as text, image, document
│   ├── context                        # Context management for conversations
│   │   └── management                 # Context management utilities and handlers
│   ├── explainability                 # Invocation logging including input/output messages
│   ├── logging_utils                  # Application logging configuration and utilities
│   ├── memory                         # Conversation history and memory management
│   ├── memory_store                   # Storage of memory objects
│   ├── messages                       # Message objects such as User, Assistant, System
│   ├── models                         # LLM model integrations
│   │   └── bedrock                    # Amazon Bedrock specific implementations
│   ├── prompts                        # System prompt templates and configurations
│   ├── tools                          # Tool framework for agent capabilities
│   │   └── tool_groups                # Organized collections of related tools
│   │       └── core                   # Essential/basic tool implementations
│   └── utils                          # Common utilities and helper functions
└── converseagent_extras               # Additional optional features
    ├── agents                         # Extended agent implementations
    └── tools                          # Additional tool implementations
        └── tool_groups                # Organized extra tool collections
            ├── collaboration          # Agent collaboration tools
            ├── computer               # Computer interaction tools
            ├── filesystem             # Filesystem tools
            └── web                    # Web-related tools
                └── web_browser        # Web browsing capabilities

```

## Development Workflow

1. **Create a New Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test**
   PyTest is used for testing.

   ```bash
   # Run tests
   make test
   ```

3. **Lint Code**
   Ruff is used for linting.

   ```bash
   # Run linter
   make lint
   ```

4. **Format Code**
   Ruff is used for linting.

   ```bash
   make format
   ```

5. **Run code scanner**
   Run bandit to scan the scode and resolve any issues.

   ```bash
   make scan
   ```

6. **Submit Changes**
   - Commit your changes with clear messages
   - Push to your branch
   - Create a pull request

## Testing Guidelines

- Write tests for all new features
- Run tests using:
  ```bash
  # Run all tests
  make test
  ```

## Code Style and Standards

We follow these coding standards:

- PEP 8 style guide
- Type hints for all functions
- Docstrings for all public APIs
- Maximum line length: 88 characters (configured in ruff)

## UI Development

The WebUI is built on Next.JS, TailwindCSS, and FastAPI.
It is only meant to provide UI for interacting with the example code
and is not meant for production use. This should only be used locally.

1. **Start the UI Server**

   ```bash
   make run-ui
   ```

2. **Access the UI**
   - Open http://localhost:8000 in your browser
   - UI components are in the `webui/` directory

## Getting Help

- Create an issue on GitHub
- Check existing documentation in the `notebooks/` directory
- Review test cases for implementation examples

---

© Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

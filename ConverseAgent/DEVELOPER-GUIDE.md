# Developer Guide

Welcome to the ConverseAgent developer guide! This document will help you set up your development environment and understand how to contribute to the project effectively.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Style and Standards](#code-style-and-standards)
- [Building and Packaging](#building-and-packaging)
- [UI Development](#ui-development)
- [Advanced Usage](#advanced-usage)

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.11 or later
- Poetry (Python dependency management)
- Make (for using Makefile commands)
- Git

Required development tools (automatically installed via Poetry):
- black: Code formatter
- pytest: Testing framework
- pytest-cov: Test coverage reporting
- bandit: Security analysis
- ruff: Linting tool

## Development Environment Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/ConverseAgent.git
   cd ConverseAgent
   ```

2. **Install Dependencies**
   ```bash
   # Install all dependencies including development tools
   make build
   make install
   ```

3. **Configure AWS Credentials**
   - Ensure you have AWS credentials configured with access to Amazon Bedrock
   - Set up your AWS profile in `~/.aws/credentials` or use environment variables

4. **Install Optional Dependencies**
   ```bash
   # For extra utilities
   poetry install --extras "extras"
   
   # For UI development
   poetry install --extras "ui"
   ```

## Project Structure

```
ConverseAgent/
├── src/
│   ├── converseagent/           # Core library implementation
│   └── converseagent_extras     # Additional features
├── ui/                          # Web interface components
├── tests/                       # Test suite
│   └── unit/                    # Unit tests
├── notebooks/                   # Example notebooks
├── pyproject.toml               # Project configuration
└── Makefile                     # Development commands
```

## Development Workflow

1. **Create a New Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test**
   ```bash
   # Run tests
   make test

3. **Format Code**
   ```bash
   make format
   ```

4. **Submit Changes**
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

## Building and Packaging

1. **Local Development Build**
   ```bash
   make build
   ```

2. **Create Distribution Package**
   ```bash
   make dist
   ```

3. **Reinstall for Development**
   ```bash
   make reinstall
   ```

## UI Development

1. **Start the UI Server**
   ```bash
   make run-ui
   ```

2. **Access the UI**
   - Open http://localhost:8000 in your browser
   - UI components are in the `ui/` directory

## Getting Help

- Create an issue on GitHub
- Check existing documentation in the `notebooks/` directory
- Review test cases for implementation examples

---
© Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
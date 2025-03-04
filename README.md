# EPAiV5-CapStone

Submitted by: Aravind D. Chakravarti
Email ID: aravinddcsadguru@gmail.com


# AI-Powered File Organization Agent

An intelligent file organization system that uses a dual-LLM (Large Language Model) architecture to automatically organize files in a directory based on their types. The system employs Google's Gemini AI to break down complex tasks and execute them efficiently.

## Project Overview

This project is part of EPAiV5-CapStone, developed by Aravind D. Chakravarti (aravinddcsadguru@gmail.com).

## Features

### Core Functionality
- **Dual LLM Architecture**:
  - LLM1: Task decomposition and planning
  - LLM2: Task execution and function calling
- **Smart Task Processing**:
  - Automatic task breakdown into manageable subtasks
  - Intelligent function selection and execution
  - Support for both direct commands and todo.txt file processing

### File Organization
- **Automatic File Categorization** into predefined types:
  - Images: jpg, jpeg, png, gif, bmp, svg, ico
  - Documents: txt, doc, docx, pdf, ppt, pptx, xls, xlsx, csv
  - Code Files: py, ipynb

### System Features
- **Comprehensive Error Handling**:
  - File permission management
  - Read-only file handling
  - Directory existence verification
- **Detailed Logging System**:
  - Operation timestamps
  - Success/failure tracking
  - Error tracing
- **Flexible Configuration**:
  - Customizable file type mappings
  - Extensible function registry
  - Environment-based configuration

## Prerequisites

- Python 3.12 or higher
- Google Gemini AI API Key
- Required Python packages:
  ```
  google-generativeai
  python-dotenv
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/aravindchakravarti/EPAiV5-CapStone.git
   cd EPAiV5-CapStone
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   # Create .env file
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

## Project Structure
   ```

EPAiV5-CapStone/ 
├── main.py # Main agent implementation with LLM logic 
├── functions/ 
│ └── file_ops.py # File organization operations 
| └── email_services.py # Email services
| └── text_file_read.py # Text related  operations
├── .env # Environment configuration 
├── requirements.txt # Project dependencies 
└── README.md # Project documentation

## Usage

## Usage

### Basic Usage

```python
from main import run_agent

# Simple file organization
result = run_agent("Please organize the folder named 'un_organized'")

# Process tasks from todo.txt
result = run_agent("Process the tasks in todo.txt")
```

### Advanced Usage

```python
# Custom directory organization
result = run_agent("Organize files in 'custom_directory' with specific categories")

# Check execution results
if result["success"]:
    print("Organization completed successfully")
    for subtask in result["subtasks"]:
        print(f"Subtask {subtask['id']}: {subtask['description']}")
        print(f"Result: {subtask['result']}")
else:
    print(f"Error: {result['error']}")
```

## Architecture

### LLM1 (Task Decomposer)
- Receives user tasks
- Analyzes requirements
- Breaks down into subtasks
- Formats output for LLM2

### LLM2 (Task Executor)
- Processes individual subtasks
- Maps tasks to functions
- Executes operations
- Handles errors and logging

### File Operations
- Directory scanning
- File type identification
- Folder creation
- File movement and organization

## Error Handling

The system handles various error scenarios:
- FileNotFoundError
- PermissionError
- Read-only file conflicts
- Invalid function calls
- LLM response parsing errors

## Logging

Comprehensive logging system includes:
- Function entry/exit logs
- Operation success/failure
- Error tracing
- LLM responses
- Task decomposition details

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini AI for LLM capabilities
- Python community for essential libraries
- EPAi5 program for project guidance
# EPAiV5-CapStone
CapStone project

Submitted by: Aravind D. Chakravarti
Email ID: aravinddcsadguru@gmail.com


# AI-Powered File Organization Agent

An intelligent file organization system that uses AI agents to automatically organize files in a directory based on their types. The system employs a two-LLM (Large Language Model) architecture to break down complex tasks and execute them efficiently.

## Features

- **Smart Task Decomposition**: Uses AI to break down complex file organization tasks into manageable subtasks
- **Automatic File Categorization**: Organizes files into predefined categories:
  - Images (jpg, jpeg, png, gif, bmp, svg, ico)
  - Documents (txt, doc, docx, pdf, ppt, pptx, xls, xlsx, csv)
  - Code Files (py, ipynb)
- **Robust Error Handling**: Includes comprehensive error handling and logging
- **Read-Only File Support**: Handles read-only files during deletion operations
- **Logging System**: Detailed logging of all operations for debugging and monitoring

## Prerequisites

- Python 3.12 or higher
- Google API Key for Gemini AI
- Required Python packages:
  ```
  google-generativeai
  python-dotenv
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone <your-repository-url>
   cd <repository-name>
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

## Project Structure
├── main.py # Main agent implementation
├── functions/
│ └── file_ops.py # File operations functions
├── .env # Environment variables
└── requirements.txt # Project dependencies

## Usage

1. Basic usage:
   ```python
   from main import run_agent
   
   # Organize files in the 'un_organized' folder
   result = run_agent("Please organize the folder named 'un_organized'")
   ```

2. The agent will:
   - Scan the specified directory
   - Identify file types
   - Create appropriate folders
   - Move files to their respective categories

## How It Works

1. **Task Decomposition (LLM1)**:
   - Receives the user's task
   - Breaks it down into smaller, manageable subtasks
   - Outputs a structured list of operations

2. **Task Execution (LLM2)**:
   - Receives each subtask
   - Identifies appropriate functions to execute
   - Executes the functions with correct parameters

3. **File Operations**:
   - Scans directories recursively
   - Creates organized folder structure
   - Moves files to appropriate categories
   - Handles read-only files and permissions

## Error Handling

The system includes comprehensive error handling for:
- File not found errors
- Permission issues
- Read-only file conflicts
- Invalid file operations

## Logging

All operations are logged with timestamps and severity levels:
- INFO: Regular operations
- ERROR: Operation failures
- WARNING: Potential issues

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini AI for providing the LLM capabilities
- Python community for the various libraries used in this project

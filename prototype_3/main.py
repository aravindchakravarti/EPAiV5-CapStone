import os
import json
import logging
import inspect
import importlib.util
from google import genai
from google.genai import types
from dotenv import load_dotenv, find_dotenv
from typing import Union, get_type_hints
import re
import ast

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Fetch API key
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in environment variables.")

# Configure GenAI client 1
client_1 = genai.Client(api_key=API_KEY)

# Configure GenAI client 2
client_2 = genai.Client(api_key=API_KEY)

# Function registry (automatically populated)
function_registry = {}

def load_functions_from_directory(directory: str):
    """
    Scans a directory and its subdirectories for Python files, imports them, and registers functions.

    Args:
        directory (str): The directory containing function modules.
    """
    global function_registry

    if not os.path.isdir(directory):
        logging.error(f"Directory {directory} does not exist!")
        return

    for root, _, files in os.walk(directory):  # Recursively walk through subdirectories
        for filename in files:
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]  # Remove '.py' extension
                module_path = os.path.join(root, filename)

                # Dynamically load the module
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Register only functions that start with "ai_"
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if name.startswith("ai_"):  # Naming convention check
                        function_registry[name] = func

                logging.info(f"Loaded functions from {filename}: {list(function_registry.keys())}")

def extract_function_metadata():
    """
    Extracts function names and signatures dynamically.

    Returns:
        str: JSON-formatted string containing function metadata.
    """
    json_list = [
        {"name": name, "signature": str(inspect.signature(func))}
        for name, func in function_registry.items()
    ]
    
    return json.dumps(json_list, indent=2)  # Pretty-print JSON for readability

def get_completion(system_prompt: str, user_prompt: str, model: str = "gemini-2.0-flash") -> str:
    """
    Generates a response using Google's Gemini API.

    Args:
        system_prompt (str): The system prompt providing context.
        user_prompt (str): The user's input prompt.
        model (str): The AI model to use (default: gemini-2.0-flash).

    Returns:
        str: The AI-generated response.
    """
    try:
        response = client_1.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt, 
                temperature=0),
            contents=user_prompt
        )
        if not response or not hasattr(response, "text"):
            raise ValueError("Invalid response format from API.")

        return response.text.strip()
    
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        return "An error occurred while generating the response."

def extract_function_header_args(path: str) -> str:
    """
    Extracts function header and arguments all the files in the directory.
    """
    load_functions_from_directory("functions")
    func_def_n_info = extract_function_metadata()
    logging.debug(f"Function definitions and metadata: {func_def_n_info}")
    return func_def_n_info

system_prompt = f"""We are building an AI agent with two LLMs.  
You are the first LLM, responsible for breaking down complex tasks into smaller subtasks.  
Your outputs will be processed by the second LLM, which will execute the subtasks.  

The second LLM will have access to:  
1. Your outputs  
2. The following Python functions:  

{extract_function_header_args("functions")}

### Instructions for You:
- Break down the task in a way that allows the second LLM to identify and call the necessary functions.  
- Format your output as a **Python list** of subtasks.  
- **Do not** include function names or arguments in your output.  

Your focus is on structuring the task effectively, ensuring smooth execution by the second LLM.  
""" 

user_prompt = """Please organize the folder named "un_organized"""

# Send request to Gemini API
llm_response = get_completion(system_prompt, user_prompt)

# Regex to extract text inside square brackets
match = re.search(r"\[(.*?)\]", llm_response, re.DOTALL)
if match:
    extracted_list = match.group(0)  # Includes square brackets
    extracted_list = ast.literal_eval(extracted_list)  # Convert to Python list
    print(extracted_list)
else:
    print("No valid list found in the response.")

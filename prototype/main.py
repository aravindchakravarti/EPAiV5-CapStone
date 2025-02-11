import os
import json
import logging
import inspect
import importlib.util
import google.generativeai as genai
from dotenv import load_dotenv, find_dotenv
from typing import Union, get_type_hints
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
if not load_dotenv(find_dotenv()):
    logging.warning("Could not find .env file. Make sure it exists and contains the required API key.")

# Fetch API key
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in environment variables.")

# Configure GenAI
genai.configure(api_key=API_KEY)

# # Function to cleanly shut down the API
# def shutdown_grpc():
#     genai.shutdown()  # Ensure gRPC terminates properly

# # Register cleanup function to run on exit
# atexit.register(shutdown_grpc)

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

# Load functions from 'functions/' directory and its subdirectories
load_functions_from_directory("functions")

def extract_function_metadata():
    """
    Extracts function signatures and docstrings dynamically.

    Returns:
        str: Formatted string containing function metadata.
    """
    metadata_str = ""
    for name, func in function_registry.items():
        signature = str(inspect.signature(func))
        docstring = inspect.getdoc(func) or "No description available."
        metadata_str += f"{name}{signature} - {docstring}\n\n"

    return metadata_str

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
        model_instance = genai.GenerativeModel(model)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = model_instance.generate_content(full_prompt)

        if not response or not hasattr(response, "text"):
            raise ValueError("Invalid response format from API.")

        return response.text.strip()
    
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        return "An error occurred while generating the response."

def validate_args(func, args):
    """
    Validates function arguments before execution.

    Args:
        func (Callable): The function to validate arguments for.
        args (list): The arguments to validate.

    Returns:
        bool: True if arguments are valid, False otherwise.
    """
    try:
        sig = inspect.signature(func)
        param_types = get_type_hints(func)
        
        if len(args) != len(sig.parameters):
            logging.error(f"Incorrect number of arguments. Expected {len(sig.parameters)}, got {len(args)}")
            return False

        # Check argument types (if type hints exist)
        for (arg, param) in zip(args, sig.parameters.values()):
            expected_type = param_types.get(param.name, None)
            if expected_type and not isinstance(arg, expected_type):
                logging.error(f"Type mismatch for '{param.name}': Expected {expected_type}, got {type(arg)}")
                return False

        return True
    except Exception as e:
        logging.error(f"Error validating arguments: {e}")
        return False

def select_and_execute_function(user_input: str):
    """
    Determines the appropriate function based on user input, retrieves arguments, validates them, and executes the function.

    Args:
        user_input (str): The user's request.

    Returns:
        The function result or an error message.
    """
    function_metadata = extract_function_metadata()

    system_prompt = f"""You are an AI that selects the most appropriate function based on user input.
    Available functions:\n\n{function_metadata}
    
    Return JSON in the following format but do not include ```json or any markdown formatting in your reesponse:
    {{"function": "function_name", "args": [arg1, arg2]}}"""

    llm_response = get_completion(system_prompt, user_input)

    try:
        response_data = json.loads(llm_response)
        func_name = response_data["function"]
        args = response_data["args"]

        if func_name in function_registry:
            func = function_registry[func_name]

            # Validate arguments before execution
            if validate_args(func, args):
                return func(*args)
            else:
                return "Error: Invalid arguments provided."
        else:
            raise ValueError(f"Function {func_name} not found.")
    except json.JSONDecodeError:
        logging.error(f"Failed to parse LLM response: {llm_response}")
        return "Error: Could not understand the response from AI."
    except Exception as e:
        logging.error(f"Execution error: {e}")
        return "Error: Something went wrong while executing the function."

# Example usage
user_query = "I have 4 apples and my friend gave me 3 more. Howw many apples do I have now?"
result = select_and_execute_function(user_query)
print(f"Result: {result}")

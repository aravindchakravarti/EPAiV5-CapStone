import os
import json
import logging
import inspect
import importlib.util
from google import genai
from google.genai import types
from dotenv import load_dotenv, find_dotenv
import re
import ast
from typing import List, Dict, Any, Callable, Optional, Tuple
from functions.text_file_read import ai_read_file

# Load environment variables
load_dotenv(find_dotenv())

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Fetch API key
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in environment variables.")

# Configure GenAI clients
llm1_client = genai.Client(api_key=API_KEY)
llm2_client = genai.Client(api_key=API_KEY)

# Function registry (automatically populated)
function_registry = {}

def load_functions_from_directory(directory: str):
    """
    Scans a directory and its subdirectories for Python files, imports them, and registers functions.

    Args:
        directory (str): The directory containing function modules.
    """
    if not os.path.isdir(directory):
        logging.error(f"Directory {directory} does not exist!")
        return

    for root, _, files in os.walk(directory):  # Recursively walk through subdirectories
        for filename in files:
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]  # Remove '.py' extension
                module_path = os.path.join(root, filename)

                try:
                    # Dynamically load the module
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Register only functions that start with "ai_"
                    for name, func in inspect.getmembers(module, inspect.isfunction):
                        if name.startswith("ai_"):  # Naming convention check
                            function_registry[name] = func
                            
                    loaded_funcs = [f for f in function_registry.keys() if f in [name for name, _ in inspect.getmembers(module, inspect.isfunction) if name.startswith('ai_')]]
                    if loaded_funcs:
                        logging.info(f"Loaded functions from {filename}: {loaded_funcs}")
                except Exception as e:
                    logging.error(f"Error loading module {module_path}: {e}")

def extract_function_metadata():
    """
    Extracts function names, signatures, and docstrings dynamically.

    Returns:
        str: JSON-formatted string containing function metadata.
    """
    json_list = []
    
    for name, func in function_registry.items():
        signature = str(inspect.signature(func))
        docstring = inspect.getdoc(func) or ""
        
        # Get type hints if available
        try:
            type_hints = inspect.get_annotations(func)
            type_hints_str = {param: str(hint) for param, hint in type_hints.items()}
        except Exception:
            type_hints_str = {}
            
        json_list.append({
            "name": name,
            "signature": signature,
            "docstring": docstring,
            "type_hints": type_hints_str
        })
    
    return json.dumps(json_list, indent=2)  # Pretty-print JSON for readability

def get_llm1_completion(system_prompt: str, user_prompt: str, model: str = "gemini-2.0-flash") -> str:
    """
    Generates a response using the first LLM (task decomposition).

    Args:
        system_prompt (str): The system prompt providing context.
        user_prompt (str): The user's input prompt.
        model (str): The AI model to use.

    Returns:
        str: The AI-generated response.
    """
    try:
        response = llm1_client.models.generate_content(
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
        logging.error(f"Error generating response from LLM1: {e}")
        return "An error occurred while generating the response."

def get_llm2_completion(system_prompt: str, user_prompt: str, model: str = "gemini-2.0-flash") -> str:
    """
    Generates a response using the second LLM (task execution).

    Args:
        system_prompt (str): The system prompt providing context.
        user_prompt (str): The user's input prompt.
        model (str): The AI model to use.

    Returns:
        str: The AI-generated response.
    """
    try:
        response = llm2_client.models.generate_content(
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
        logging.error(f"Error generating response from LLM2: {e}")
        return "An error occurred while generating the response."

def extract_function_header_args(path: str) -> str:
    """
    Extracts function header and arguments from all the files in the directory.
    
    Args:
        path (str): Path to the directory containing function files.
        
    Returns:
        str: JSON-formatted string containing function metadata.
    """
    load_functions_from_directory(path)
    func_def_n_info = extract_function_metadata()
    logging.debug(f"Function definitions and metadata: {func_def_n_info}")
    return func_def_n_info

def process_llm1_response(response: str) -> List[str]:
    """
    Process the first LLM response to extract the subtask list.
    
    Args:
        response (str): The raw response from the LLM.
        
    Returns:
        List[str]: The extracted list of subtasks.
    """
    try:
        # Try multiple approaches to extract the list
        # First, try to find with square brackets
        match = re.search(r"\[(.*?)\]", response, re.DOTALL)
        if match:
            extracted_list = match.group(0)  # Includes square brackets
            return ast.literal_eval(extracted_list)  # Convert to Python list
            
        # Alternative approach: Look for lines that might be list items
        lines = response.split('\n')
        potential_list = []
        for line in lines:
            # Look for numbered or bulleted list items
            clean_line = re.sub(r'^\s*[\d\-\*]+\.\s*', '', line).strip()
            if clean_line and line != clean_line:
                potential_list.append(clean_line)
                
        if potential_list:
            return potential_list
            
        # If all else fails, return the entire response as a single item
        return [response.strip()]
            
    except (SyntaxError, ValueError) as e:
        logging.error(f"Error parsing LLM1 response: {e}")
        logging.error(f"Raw response: {response}")
        return []
    
def parse_function_call(func_call_str: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Parse the function call string from LLM2 into function name and arguments.
    
    Args:
        func_call_str (str): String representing a function call like "ai_function_name(arg1='value', arg2=42)"
        
    Returns:
        Tuple[Optional[str], Dict[str, Any]]: Function name and dictionary of arguments
    """
    try:
        # Extract function name
        match = re.match(r'(\w+)\s*\(', func_call_str)
        if not match:
            return None, {}
            
        func_name = match.group(1)
        
        # Extract arguments string
        args_match = re.search(r'\((.*)\)', func_call_str, re.DOTALL)
        if not args_match:
            return func_name, {}
            
        args_str = args_match.group(1).strip()
        if not args_str:
            return func_name, {}
            
        # Parse arguments into a dictionary
        args_dict = {}
        
        # Handle string arguments with potential commas inside
        in_string = False
        quote_char = None
        current_arg = ""
        args_list = []
        
        for char in args_str:
            if char in ['"', "'"]:
                if not in_string:
                    in_string = True
                    quote_char = char
                elif char == quote_char:
                    in_string = False
                    quote_char = None
                current_arg += char
            elif char == ',' and not in_string:
                args_list.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char
                
        if current_arg:
            args_list.append(current_arg.strip())
        
        # Process each argument
        for arg in args_list:
            if '=' in arg:
                key, value = arg.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Try to evaluate the value safely
                try:
                    # Remove quotes for strings
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    # Try to convert to appropriate Python type for non-string values
                    elif value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.lower() == 'none':
                        value = None
                    elif value.replace('.', '', 1).isdigit():
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                except Exception as e:
                    logging.warning(f"Could not parse argument value '{value}': {e}")
                
                args_dict[key] = value
        
        return func_name, args_dict
        
    except Exception as e:
        logging.error(f"Error parsing function call '{func_call_str}': {e}")
        return None, {}


def execute_function(func_name: str, args: Dict[str, Any]) -> Any:
    """
    Execute the specified function with the given arguments.
    
    Args:
        func_name (str): Name of the function to execute
        args (Dict[str, Any]): Arguments to pass to the function
        
    Returns:
        Any: Result of the function execution
    """
    if func_name not in function_registry:
        raise ValueError(f"Function '{func_name}' not found in registry")
    
    func = function_registry[func_name]
    
    # Get function signature
    sig = inspect.signature(func)
    
    # Prepare arguments
    valid_args = {}
    for param_name, param in sig.parameters.items():
        if param_name in args:
            valid_args[param_name] = args[param_name]
    
    # Execute function
    try:
        logging.info(f"Executing function '{func_name}' with args: {valid_args}")
        result = func(**valid_args)
        return result
    except Exception as e:
        logging.error(f"Error executing function '{func_name}': {e}")
        raise

def run_agent(user_task: str, functions_dir: str = "functions") -> Dict[str, Any]:
    """
    Run the complete agent workflow: task decomposition and execution.
    
    Args:
        user_task (str): The user's task description
        functions_dir (str): Directory containing function modules
        
    Returns:
        Dict[str, Any]: Results of the agent execution
    """
    # Load available functions
    load_functions_from_directory(functions_dir)
    function_metadata = extract_function_metadata()
    
    # Create system prompt for LLM1 (Task Decomposer)
    llm1_system_prompt = f"""We are building an AI agent with two LLMs.  
You are the first LLM, responsible for breaking down complex tasks into smaller subtasks.  
Your outputs will be processed by the second LLM, which will execute the subtasks. 

The second LLM will have access to:  
1. Your outputs  
2. The following Python functions:  

{function_metadata}

optionally, If use prompt suggests to read the todo.txt file, then here is the content of todo.txt

{ai_read_file("todo.txt")}. 

You are going to provide sub tasks for instructions in this file as well.
However, if user prompt, doesn't suggest to read todo.txt file, then you going to ignore content of todo.txt file.

### Instructions for You:
- Break down the task in a way that allows the second LLM to identify and call the necessary functions.  
- Format your output as a **Python list** of subtasks.  
- **Do not** include function names or arguments in your output.  
- Let the instructions be stright forward and clear. For example:
    - Retrieve list of all files within <folder name> 
    - Identify unique file types
    - Create organized folders based on the identified unique file types within the <folder name> directory.
    - Compress all images in "images" directory if directory exists
- In each of your predictions, if required, do not just say "source folder", but always \
    say "source_path=<<<folder name>>>" or "destination_path='<<<folder name>>>'".

Your focus is on structuring the task effectively, ensuring smooth execution by the second LLM.  
"""
    
    # Get task decomposition from LLM1
    llm1_response = get_llm1_completion(llm1_system_prompt, user_task)
    subtasks = process_llm1_response(llm1_response)
    
    logging.info(f"LLM1 generated {len(subtasks)} subtasks, and they are:")
    for i, subtask in enumerate(subtasks, start=1):
        logging.info(f"{i}. {subtask}")

    if True:
        logging.info("\n\n ****************** LLM2 RESPONSE BEGINS ************************ \n\n")
        # Create system prompt for LLM2 (Task Executor)
        llm2_system_prompt = f"""We are building an AI agent with two LLMs. The first LLM \
    has received a task from user and it sub-divided the complex task into smaller \
    sub-tasks. You are the second LLM in an AI agent system, responsible for executing subtasks. \
    You have access to the following Python functions that can be called to complete tasks:
    {function_metadata}

    ### Instructions for You:
    1. Analyze the subtask provided to you.
    2. Identify the most appropriate function to execute for this subtask.
    3. Format your response as a single function call with appropriate arguments.
    4. Use ONLY functions that exist in the provided list. Do not invent new functions.

    Example Response Format:
    <<<
    user_input : Retrieve list of all files within the 'un_organized' folder
    response : ai_get_file_list(path='un_organized')

    user_input : Create organized folders based on the identified unique file types within the 'un_organized' directory
    response : ai_create_organized_folders(unique_file_types=unique_file_types, base_path='un_organized')

    >>>

    Your response should contain ONLY the function call, nothing else. Do not include any formatting like ``` or toolcode etc.
    """

        # Execute each subtask using LLM2
        results = {
            "task": user_task,
            "subtasks": [],
            "success": True,
            "error": None
        }

        for i, subtask in enumerate(subtasks):
            subtask_result = {
                "id": i + 1,
                "description": subtask,
                "function_call": None,
                "success": False,
                "result": None,
                "error": None
            }

            try:
                # Get function call from LLM2
                llm2_response = get_llm2_completion(llm2_system_prompt, f"Subtask: {subtask}")

                logging.info(f"LLM2 response for subtask {i}: {llm2_response}")

                # Clean the response
                clean_response = llm2_response.strip()
                if clean_response.startswith("```") and clean_response.endswith("```"):
                    clean_response = clean_response[3:-3].strip()
                logging.info(f"LLM2 cleaned response: {clean_response}")

                # Parse the function call
                func_name, args = parse_function_call(clean_response)
                
                if not func_name:
                    raise ValueError(f"Could not parse function call: {clean_response}")
                
                logging.info(f"Parsed function name: {func_name}, args: {args}")

                # Execute the function
                func_result = execute_function(func_name, args)
                
                subtask_result["success"] = True
                subtask_result["result"] = str(func_result)

            except Exception as e:
                subtask_result["success"] = False
                subtask_result["error"] = str(e)
                results["success"] = False
                if not results["error"]:
                    results["error"] = f"Error in subtask {i+1}: {str(e)}"
            
            results["subtasks"].append(subtask_result)
            logging.info("\n------------------------------------------")
            
        return results


if __name__ == "__main__":
    task = """ I want you to do three tasks. \
    First task is to, read the todo.txt file in base folder path, i.e., './' which \
    contains list of task to be accomplished. Please complete them. \
    Second task is to Please organize the folder named 'un_organized' 
    Third task is to compress all the images in 'un_organized' directory.
    """

    result = run_agent(task)

    # Print results in a readable format
    print(f"\n===== AGENT EXECUTION RESULTS =====")
    print(f"Task: {result['task']}")
    print(f"Overall success: {'✓' if result['success'] else '✗'}")
    
    if result.get("error"):
        print(f"Error: {result['error']}")
        
    print("\nSubtasks execution:")
    for subtask in result["subtasks"]:
        status = "✓" if subtask["success"] else "✗"
        print(f"\n{subtask['id']}. {subtask['description']} {status}")
        #print(f"   Function call: {subtask['function_call']}")
        
        #if subtask["success"]:
        #    print(f"   Result: {subtask['result']}")
        #else:
        #    print(f"   Error: {subtask['error']}")
            
    print("\n===================================")

""" ==================================== PROMPTS ==================================== """

"""
def ai_get_file_list(path: str) -> List[str]:
def ai_get_unique_file_types(file_list: List[str]) -> Set[str]:
def ai_create_folders(unique_file_types: Set[str], base_path: str = ".") -> Dict[str, str]:
def ai_move_files_to_folder(source_folder: str, folder_paths: Dict[str, str]) -> None:

"""


'''
Please organize the folder named 'un_organized'. It has mix of different file types
'''

'''
read the todo.txt file in base folder path, i.e., './' which contains list of task to be accomplished
'''

'''
I want you to do two tasks. \
    First task is to, read the todo.txt file in base folder path, i.e., './' which \
    contains list of task to be accomplished. Please complete them. \
    Second task is to Please organize the folder named 'un_organized' 
'''

'''
I want you to do three tasks. \
    First task is to, read the todo.txt file in base folder path, i.e., './' which \
    contains list of task to be accomplished. Please complete them. \
    Second task is to Please organize the folder named 'un_organized' 
    Third task is to compress all the images in 'un_organized' directory.
'''

'''
I will always use below names for returned values for correspding functions. This will help you\
    in determining the params for next function call.

    <<<
    files_list = ai_get_file_list(source_path)
    unique_file_types = ai_get_unique_file_types(files_list)
    folder_paths = ai_create_folders(unique_file_types, base_path)
    ai_move_files_to_folder(source_path, folder_paths)
    >>>
'''
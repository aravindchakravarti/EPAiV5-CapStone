import importlib.util
import logging
import os
import inspect
import json
from typing import List, Dict, Any, Callable, Optional, Tuple
import re

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
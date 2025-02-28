import os
import json
import logging
import inspect
import importlib.util
from google import genai
from google.genai import types
from dotenv import load_dotenv, find_dotenv
from typing import Union, get_type_hints
import atexit
import gradio as gr

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
client = genai.Client(api_key=API_KEY)

# # Function to cleanly shut down the API
# def shutdown_grpc():
#     genai.shutdown()  # Ensure gRPC terminates properly

# # Register cleanup function to run on exit
# atexit.register(shutdown_grpc)

# Function registry (automatically populated)
function_registry = {}

# def gradio_interface(user_input):
#     """Wrapper function for Gradio to call AI agent."""
#     return iterative_function_execution(user_input)

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
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt, 
                temperature=0),
            contents=user_prompt
        )

        # model_instance = genai.GenerativeModel(model)
        # full_prompt = f"{system_prompt}\n\n{user_prompt}"
        # response = model_instance.generate_content(full_prompt)

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

# def select_and_execute_function(user_input: str):
#     """
#     Determines the appropriate function based on user input, retrieves arguments, validates them, and executes the function.

#     Args:
#         user_input (str): The user's request.

#     Returns:
#         The function result or an error message.
#     """
#     function_metadata = extract_function_metadata()

#     system_prompt = f"""You are an AI that selects the most appropriate function based on user input.
#     Available functions:\n\n{function_metadata}
    
#     Return JSON in the following format but do not include ```json or any markdown formatting in your reesponse:
#     {{"function": "function_name", "args": [arg1, arg2]}}"""

#     llm_response = get_completion(system_prompt, user_input)

#     try:
#         response_data = json.loads(llm_response)
#         func_name = response_data["function"]
#         args = response_data["args"]

#         if func_name in function_registry:
#             func = function_registry[func_name]

#             # Validate arguments before execution
#             if validate_args(func, args):
#                 return func(*args)
#             else:
#                 return "Error: Invalid arguments provided."
#         else:
#             raise ValueError(f"Function {func_name} not found.")
#     except json.JSONDecodeError:
#         logging.error(f"Failed to parse LLM response: {llm_response}")
#         return "Error: Could not understand the response from AI."
#     except Exception as e:
#         logging.error(f"Execution error: {e}")
#         return "Error: Something went wrong while executing the function."

def iterative_function_execution(user_input: str, max_iterations: int = 4) -> str:
    """Loops through function calls until LLM decides it's done."""

    # Few-shot examples to improve multi-step reasoning
    few_shot_examples = """
    Example 1:
    User: "I had 5 chocolates. My friend gave me 2 more, but later I ate 3. How many do I have now?"
    AI Thought Process:
    - First, use ai_add_two_numbers(5, 2) -> 7
    - Then, use ai_sub_two_numbers(7, 3) -> 4
    - Answer is 4.

    Example 2:
    User: ""I had 10 apples. I gave 2 to my friend and 3 to my sister. How many do I have left?"
    AI thought process:
    - First, use ai_sub_two_numbers(10, 2) -> 8
    - Then, use ai_sub_two_numbers(8, 3) -> 5
    - Answer is 5.

    Example 3:
    User: "I saved 100 dollars, then spent 20 on food and 10 on transport. How much do I have left?"
    AI Thought Process:
    - First, use ai_sub_two_numbers(100, 20) -> 80
    - Then, use ai_sub_two_numbers(80, 10) -> 70
    - Answer is 70.
    """

    conversation_state = []  # Stores function calls & results

    for iteration in range(max_iterations):
        logging.info(f"Iteration {iteration + 1}")
        # Create a system prompt with conversation memory
        function_metadata = extract_function_metadata()
        system_prompt = f"""You are an AI agent that selects the best function(s) based on user input.
        
        Available functions are listed below select one at a time:
        {function_metadata}

        Here are some examples of how to use the functions based on user inputs:
        {few_shot_examples}

        You have access to previous function calls which you made, this will help you in deciding which functoin to call next. \
        Use previous results to decide the next function call.
        {json.dumps(conversation_state)}

        
        If the final answer is reached, return in following format but do not include ```json or any markdown formatting in your response:
        {{"function": "DONE", "args": []}}

        Else return JSON in the following format but do not include ```json or any markdown formatting in your response:
        {{"function": "function_name", "args": [arg1, arg2]}}
        
        """

        # Send request to Gemini API
        llm_response = get_completion(system_prompt, user_input)

        try:
            response_data = json.loads(llm_response)
            func_name = response_data["function"]
            args = response_data["args"]

            if func_name == "DONE":
                return conversation_state[-1]["result"] if conversation_state else "No valid output."

            if func_name in function_registry:
                logging.info(f"Calling function: {func_name} with args: {args}")
                func = function_registry[func_name]

                if validate_args(func, args):
                    result = func(*args)
                    conversation_state.append({"function": func_name, "args": args, "result": result})
                else:
                    return "Error: Invalid arguments provided."
            else:
                return f"Error: Function {func_name} not found."

        except json.JSONDecodeError:
            logging.error(f"Failed to parse LLM response: {llm_response}")
            return "Error: Could not understand the response from AI."
        except Exception as e:
            logging.error(f"Execution error: {e}")
            return "Error: Something went wrong while executing the function."

    logging.warning("Max iterations reached. Stopping execution.")
    return "Error: Maximum iterations reached."


# # Create the Gradio UI
# gr.Interface(
#     fn=gradio_interface,
#     inputs=gr.Textbox(label="Enter your query"),
#     outputs=gr.Textbox(label="AI Response"),
#     title="AI Function Executor",
#     description="This AI selects and executes functions based on user input.",
#     live=True
# ).launch()
# Example usage
user_query = "I have 4 apples and my friend gave me 3 more. How many apples do I have now?"
# I have 4 apples and my friend gave me 3 more. I ate 2 apples out of it. Later my another friend gifted me 10 apples!. How many apples do I have now?
result = iterative_function_execution(user_query)
print(f"Result: {result}")

# # user_query = "I have 4 apples and my friend gave me 3 more later my father ate 2. How many apples do I have now?"
# user_query = "I had four apples, my friend ate 3. How may apples do I have now?"
# result = iterative_function_execution(user_query)
# print(f"Result: {result}")
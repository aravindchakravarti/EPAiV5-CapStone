import logging
from typing import List, Dict, Any, Callable, Optional, Tuple
import os
from google import genai
from google.genai import types
import re
import ast
from functions.text_file_read import ai_read_file

# Fetch API key
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in environment variables.")

# Configure GenAI clients
llm1_client = genai.Client(api_key=API_KEY)
llm2_client = genai.Client(api_key=API_KEY)

def get_system_promt_llm1(function_metadata:str)->str:
    prompt = f"""We are building an AI agent with two LLMs. \
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
    
    return prompt

def get_system_promt_llm2(function_metadata:str)->str:
    prompt = f"""We are building an AI agent with two LLMs. The first LLM \
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
    return prompt



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
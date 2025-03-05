import logging
from dotenv import load_dotenv, find_dotenv
from typing import List, Dict, Any, Callable, Optional, Tuple
from function_ops import *
from LLM_ops import *

# Load environment variables
load_dotenv(find_dotenv())

# Configure logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
    llm1_system_prompt = get_system_promt_llm1(function_metadata)
    
    # Get task decomposition from LLM1
    llm1_response = get_llm1_completion(llm1_system_prompt, user_task)
    subtasks = process_llm1_response(llm1_response)
    
    logging.info(f"LLM1 generated {len(subtasks)} subtasks, and they are:")
    for i, subtask in enumerate(subtasks, start=1):
        logging.info(f"{i}. {subtask}")

    if True:
        logging.info("\n\n ****************** LLM2 RESPONSE BEGINS ************************ \n\n")
        # Create system prompt for LLM2 (Task Executor)
        llm2_system_prompt = get_system_promt_llm2(function_metadata)

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

                logging.debug(f"LLM2 response for subtask {i}: {llm2_response}")

                # Clean the response
                clean_response = llm2_response.strip()
                if clean_response.startswith("```") and clean_response.endswith("```"):
                    clean_response = clean_response[3:-3].strip()
                logging.debug(f"LLM2 cleaned response: {clean_response}")

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

    print("\n===================================")
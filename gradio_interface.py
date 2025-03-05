import logging
import gradio as gr
import io
import queue
from main import run_agent  # Import your main function
import time
import threading

class AccumulatingQueueHandler(logging.Handler):
    def __init__(self, max_logs=1000):
        super().__init__()
        self.log_queue = queue.Queue()
        self.accumulated_logs = []
        self.max_logs = max_logs
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    
    def emit(self, record):
        try:
            msg = self.formatter.format(record)
            self.log_queue.put(msg)
            
            # Accumulate logs
            self.accumulated_logs.append(msg)
            
            # Trim logs if exceeding max_logs
            if len(self.accumulated_logs) > self.max_logs:
                self.accumulated_logs = self.accumulated_logs[-self.max_logs:]
        except Exception:
            self.handleError(record)
    
    def get_logs(self):
        logs = []
        while not self.log_queue.empty():
            logs.append(self.log_queue.get())
        return logs
    
    def clear_logs(self):
        # Clear both queue and accumulated logs
        while not self.log_queue.empty():
            self.log_queue.get()
        self.accumulated_logs.clear()

# Configure logging
queue_handler = AccumulatingQueueHandler()
logging.basicConfig(
    level=logging.INFO,
    handlers=[queue_handler]
)

def run_agent_with_real_time_logs(user_task: str):
    """
    Runs the agent and streams logs in real-time, maintaining log history.
    """
    # Clear only the current queue, keeping accumulated logs
    queue_handler.clear_logs()
    
    # Yield the accumulated logs to start with
    yield gr.update(value="\n".join(queue_handler.accumulated_logs))
    
    # Create a thread-safe flag to track thread completion
    thread_completed = threading.Event()
    
    def agent_execution():
        try:
            # Ensure logging works within the thread
            logging.info(f"Starting agent with task: {user_task}")
            result = run_agent(user_task)
            # Print results in a readable format
            logging.info(f"\n===== AGENT EXECUTION RESULTS =====")
            logging.info(f"Task: {result['task']}")
            logging.info(f"Overall success: {'✓' if result['success'] else '✗'}")
            
            if result.get("error"):
                logging.info(f"Error: {result['error']}")
                
            logging.info("\nSubtasks execution:")
            for subtask in result["subtasks"]:
                status = "✓" if subtask["success"] else "✗"
                logging.info(f"\n{subtask['id']}. {subtask['description']} {status}")
            
            logging.info("Agent execution completed")
        except Exception as e:
            logging.error(f"Error in agent execution: {e}")
        finally:
            thread_completed.set()
    
    # Start the agent in a separate thread
    thread = threading.Thread(target=agent_execution)
    thread.start()
    
    # Continuously yield logs while the agent runs
    while not thread_completed.is_set() or not queue_handler.log_queue.empty():
        # Retrieve and display logs
        current_logs = queue_handler.get_logs()
        if current_logs:
            # Combine accumulated and new logs
            full_logs = "\n".join(queue_handler.accumulated_logs + current_logs)
            yield gr.update(value=full_logs)
        
        # Small sleep to prevent tight looping
        time.sleep(0.5)
    
    # Final log update
    final_logs = queue_handler.get_logs()
    if final_logs:
        full_logs = "\n".join(queue_handler.accumulated_logs + final_logs)
        yield gr.update(value=full_logs)
    else:
        # If no new logs, just show accumulated logs
        yield gr.update(value="\n".join(queue_handler.accumulated_logs))

# Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("# <center>AI Agent</center>")
    with gr.Row():
        user_input = gr.Textbox(label="Enter Task", lines=5, scale=1)
    with gr.Row():
        log_output = gr.Textbox(label="Execution Logs", lines=20, scale=3, interactive=False)
    run_button = gr.Button("Run Agent")
    run_button.click(fn=run_agent_with_real_time_logs, inputs=user_input, outputs=log_output)

if __name__ == "__main__":
    demo.launch()
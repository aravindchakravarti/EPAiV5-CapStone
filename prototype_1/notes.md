Your Capstone Project!

Your go-to model is Gemini-2.0-flash-exp. It's free for the usage you're going to have. Build an agent that:
scans a folder,
identifies file types
moves them into categorized folders (e.g., PDFs, images, code files, etc)
uses online services to compress PDF
uses online services to compress PNGs and JPGs
reads a particular file called "todo.txt" and performs these tasks if mentioned inside:
Remind me to "------" via email
Add a calendar invite for "" date and share it with "--@--.com"
Share the stock price for NVIDIA every day at 5 PM via email with me
more if you wish
Restriction:
You CANNOT use any LLM for any of the tasks mentioned directly. Your LLM use is to call a python function that does these jobs!
You need to show the start-to-end of all 6 tasks in a YouTube video
Submission:
Link to the YouTube video
Link to the GitHub Code


your_project/
│── main.py  # Your AI agent
│── functions/  # Directory for function modules
│   │── math_ops.py  # Contains functions like add, subtract
│   │── string_ops.py  # Contains string manipulation functions
│   └── more_functions.py  # More dynamically loaded functions

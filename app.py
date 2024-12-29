from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
import json
from typing import Optional
import uvicorn
from termcolor import colored
from crewai import Crew, Process
import shutil

# Import the lead generation script
from main import create_tasks
from web_tools import WebTools

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store job status
current_job_status = {
    "is_running": False,
    "current_agent": None,
    "current_task": None,
    "error": None,
    "csv_path": None
}

class SearchParams(BaseModel):
    query: str
    num_prospects: int

def run_lead_generation(search_params: SearchParams):
    """Run the lead generation process"""
    try:
        global current_job_status
        current_job_status["is_running"] = True
        current_job_status["error"] = None
        current_job_status["csv_path"] = None
        current_job_status["current_agent"] = "Initializing"
        current_job_status["current_task"] = "Setting up environment"

        # Create a safe filename from the query
        safe_query = "".join(c for c in search_params.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_query = safe_query.replace(' ', '_')[:50]  # Limit filename length
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"{safe_query}_leads_{timestamp}.csv"
        output_file = os.path.join('static', 'downloads', csv_filename)

        # Ensure the downloads directory exists
        os.makedirs(os.path.join('static', 'downloads'), exist_ok=True)

        # Initialize tools
        web_tools = WebTools()

        # Create tasks with the filename
        tasks = create_tasks(web_tools, search_params.query, search_params.num_prospects, output_file)

        def process_step(step):
            """Process each step and update status"""
            update_status(step)
            # Print detailed step information for debugging
            if hasattr(step, 'agent'):
                print(colored("\n# Agent: " + step.agent.role, "yellow"))
                if hasattr(step, 'task'):
                    print(colored("## Task: " + step.task.description.split(chr(10))[0], "yellow"))
                if hasattr(step, 'tool'):
                    print(colored("## Using tool: " + step.tool, "yellow"))
                if hasattr(step, 'tool_input'):
                    print(colored("## Tool Input: \n" + str(step.tool_input), "yellow"))
                if hasattr(step, 'tool_output'):
                    print(colored("## Tool Output: \n" + str(step.tool_output), "yellow"))

        # Create and run crew
        crew = Crew(
            agents=[task.agent for task in tasks],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            step_callback=process_step
        )

        # Execute the tasks
        result = crew.kickoff()

        # Update status with CSV path
        if os.path.exists(output_file):
            current_job_status["csv_path"] = f"/static/downloads/{csv_filename}"
            current_job_status["is_running"] = False
            current_job_status["current_agent"] = "Completed"
            current_job_status["current_task"] = "Task finished - CSV file ready for download"
            print(colored(f"CSV file created successfully: {csv_filename}", "green"))
        else:
            raise Exception("CSV file was not created successfully")

    except Exception as e:
        current_job_status["error"] = str(e)
        current_job_status["is_running"] = False
        current_job_status["current_agent"] = "Error"
        current_job_status["current_task"] = f"Error: {str(e)}"
        print(colored(f"Error in lead generation: {str(e)}", "red"))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'web_tools' in locals():
            web_tools.cleanup()
            print(colored("Closing Chrome WebDriver...", "cyan"))

def update_status(step):
    """Update the current job status based on the crew step"""
    global current_job_status
    try:
        # Print raw step information for debugging
        print(colored("\nRaw Step Info:", "blue"))
        print(colored(f"Step type: {type(step)}", "blue"))
        print(colored(f"Step attributes: {dir(step)}", "blue"))

        # Set agent name
        if hasattr(step, 'agent') and step.agent:
            current_job_status["current_agent"] = step.agent.role
        elif hasattr(step, 'text') and 'Agent:' in step.text:
            # Extract agent name from text if available
            agent_text = step.text.split('Agent:')[1].split('\n')[0].strip()
            current_job_status["current_agent"] = agent_text
            
        # Set task description
        if hasattr(step, 'task') and step.task:
            task_desc = step.task.description.split("\n")[0].strip()
            if hasattr(step, 'tool') and step.tool:
                tool_name = step.tool.replace('_', ' ').title()
                task_desc = f"{task_desc} (Using {tool_name})"
            current_job_status["current_task"] = task_desc
        elif hasattr(step, 'thought'):
            current_job_status["current_task"] = f"Thinking: {step.thought[:100]}..."
        elif hasattr(step, 'text'):
            current_job_status["current_task"] = f"Processing: {step.text[:100]}..."
        else:
            current_job_status["current_task"] = "Processing task"
            
        # Print status update for debugging
        print(colored("\nStatus Update:", "green"))
        print(colored(f"Agent: {current_job_status['current_agent']}", "green"))
        print(colored(f"Task: {current_job_status['current_task']}", "green"))
            
    except Exception as e:
        print(colored(f"Error updating status: {str(e)}", "red"))
        print(colored(f"Error traceback:", "red"))
        import traceback
        traceback.print_exc()
        current_job_status["current_agent"] = "Error"
        current_job_status["current_task"] = f"Error: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/run")
async def run(search_params: SearchParams, background_tasks: BackgroundTasks):
    """Start the lead generation process"""
    if current_job_status["is_running"]:
        raise HTTPException(status_code=400, detail="A job is already running")
    
    background_tasks.add_task(run_lead_generation, search_params)
    return {"message": "Job started successfully"}

@app.get("/status")
async def status():
    """Get the current job status"""
    return current_job_status

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a CSV file"""
    file_path = os.path.join("static", "downloads", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("lead_generation_output", exist_ok=True)
    os.makedirs("static/downloads", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    # Run the FastAPI application
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True) 
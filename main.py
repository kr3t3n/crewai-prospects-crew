from crewai import Agent, Task, Crew, Process
from web_tools import WebTools
import os
from datetime import datetime
from termcolor import colored
from dotenv import load_dotenv
import csv

# Load environment variables
load_dotenv()

# Ensure OpenAI API key is set
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Constants
OUTPUT_DIR = "lead_generation_output"
MODEL = "gpt-4o-mini"
SEARCH_QUERY = "UK influencer talent marketing agency"
NUM_PROSPECTS = 3  # Number of agencies to find

def create_tasks(web_tools):
    """Create tasks for the crew"""
    tasks = []
    
    # Create agents
    researcher = Agent(
        role="Lead Researcher",
        goal=f"Find {NUM_PROSPECTS} potential agency clients",
        backstory="""You are a Senior Research Analyst specializing in identifying potential clients 
        in the digital marketing space. You have extensive experience in analyzing agency websites 
        and determining their potential interest in AI solutions. You are thorough in your research 
        and always verify information from multiple sources.""",
        tools=web_tools.tools,
        allow_delegation=True,
        verbose=True,
        memory=True,
        llm_model=MODEL
    )
    
    qualifier = Agent(
        role="Lead Qualifier",
        goal="Research and qualify the potential clients",
        backstory="""You are an expert at analyzing companies and identifying their potential fit 
        for AI solutions. You have a deep understanding of the digital marketing industry and can 
        effectively assess a company's likelihood of adopting AI technologies. You are meticulous 
        in gathering and verifying information. You always use the extract_contact_info tool to get 
        complete contact details and ensure they are properly formatted in your response.""",
        tools=web_tools.tools,
        allow_delegation=True,
        verbose=True,
        memory=True,
        llm_model=MODEL
    )
    
    data_manager = Agent(
        role="Data Manager",
        goal="Save lead data in a structured format",
        backstory="""You are an expert at organizing and storing business data. You ensure all 
        data is properly formatted, validated, and saved in a way that maintains data integrity. 
        You are meticulous about data quality and always verify the output.""",
        tools=web_tools.tools,
        allow_delegation=False,
        verbose=True,
        memory=True,
        llm_model=MODEL
    )
    
    # Task 1: Search for agencies
    search_task = Task(
        description=f"""Search for {NUM_PROSPECTS} influencer talent marketing agencies that could be potential clients.
        Focus on finding UK-based agencies with these characteristics:
        1. Specializes in influencer marketing and talent management
        2. Has a strong digital presence
        3. Works with established influencers/creators
        4. Shows potential for AI integration
        
        Search query: "UK influencer talent marketing agency"
        
        Avoid:
        - Individual influencers/creators
        - General marketing agencies
        - Directory or listing websites
        - Software platforms
        
        Return {NUM_PROSPECTS} agency URLs with brief explanations of why you chose each one.
        """,
        expected_output=f"A list of {NUM_PROSPECTS} URLs for relevant UK influencer marketing agencies with explanations",
        agent=researcher
    )
    tasks.append(search_task)
    
    # Task 2: Qualify the leads
    qualify_task = Task(
        description="""For each URL provided in the previous task:
        1. Research the agency's services and focus
        2. Look for AI or innovation mentions
        3. Analyze their client base and projects
        4. Identify and extract contact information using the extract_contact_info tool
        5. Assess their potential interest in AI solutions
        
        IMPORTANT: First use the extract_contact_info tool to get ALL contact details and social media links.
        Then use that information to create your response dictionary.
        
        Format your response as a list of dictionaries with EXACTLY these fields for each agency:
        {
            "Company Name": "Exact name of the agency",
            "URL": "The agency's main website URL",
            "Primary Services": "Brief description of main services",
            "AI Mentions": "Yes",  # String "Yes" or "No"
            "Decision Makers": "Name 1, Name 2",  # Comma-separated string
            "Email": "email1, email2",  # Use emails from extract_contact_info
            "Phone": "phone1, phone2",  # Use phones from extract_contact_info
            "LinkedIn": "linkedin_profile_url",  # Use first LinkedIn URL from extract_contact_info
            "Instagram": "instagram_profile_url",  # Use first Instagram URL from extract_contact_info
            "Physical Address": "Full physical address",  # Use address from extract_contact_info
            "AI Interest Score": 8,  # Number between 1-10
            "Qualification Notes": "Detailed qualification notes"
        }
        
        Make sure to include ALL contact information found by the extract_contact_info tool in your response.
        """,
        expected_output="A list of dictionaries containing qualified lead information with complete contact details",
        agent=qualifier
    )
    tasks.append(qualify_task)
    
    # Task 3: Save the data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"lead_generation_output/leads_{timestamp}.csv"
    
    save_task_desc = Task(
        description=f"""Save all qualified leads to a CSV file.
        The CSV should have the following columns:
        - Company Name
        - URL
        - Primary Services
        - AI Mentions
        - Decision Makers
        - Email
        - Phone
        - LinkedIn
        - Instagram
        - Physical Address
        - AI Interest Score
        - Qualification Notes
        
        IMPORTANT: Make sure to include ALL contact information and social media links in the CSV.
        Use the save_to_csv_file tool to save the data to: {output_file}
        """,
        expected_output="A confirmation message that the data was saved successfully",
        agent=data_manager
    )
    tasks.append(save_task_desc)
    
    return tasks

def save_task(data, output_file):
    """Save the qualified lead data to a CSV file"""
    try:
        print(colored("Saving data to CSV...", "cyan"))
        
        # Ensure data is in the correct format (list of dictionaries)
        if isinstance(data, dict):
            data = [data]
        elif isinstance(data, str):
            # Try to parse string as JSON
            import json
            try:
                parsed_data = json.loads(data)
                if isinstance(parsed_data, dict):
                    data = [parsed_data]
                elif isinstance(parsed_data, list):
                    data = parsed_data
                else:
                    print(colored("Error: Invalid data format for CSV", "red"))
                    return False
            except json.JSONDecodeError:
                # Try to parse the markdown-like format
                parsed_data = []
                current_dict = {}
                for line in data.split("\n"):
                    line = line.strip()
                    if not line:
                        if current_dict:
                            parsed_data.append(current_dict)
                            current_dict = {}
                    elif line.startswith("- **") and "**:" in line:
                        parts = line.split("**:")
                        key = parts[0].replace("- **", "").strip()
                        value = parts[1].strip()
                        current_dict[key] = value
                if current_dict:
                    parsed_data.append(current_dict)
                if parsed_data:
                    data = parsed_data
                else:
                    print(colored("Error: Invalid data format for CSV", "red"))
                    return False

        # Generate timestamped filename
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"lead_generation_output/leads_{timestamp}.csv"
            
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Define fieldnames based on expected data structure
        fieldnames = [
            "Company Name",
            "URL", 
            "Primary Services",
            "AI Mentions",
            "Decision Makers",
            "Email",
            "Phone",
            "LinkedIn",
            "Instagram",
            "Physical Address",
            "AI Interest Score",
            "Qualification Notes"
        ]
        
        # Write data to CSV
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                # Parse contact info if it's in the old format
                contact_info = row.get("Contact Info", "")
                if isinstance(contact_info, str):
                    # Try to extract individual fields from the contact string
                    email = ""
                    phone = ""
                    linkedin = ""
                    instagram = ""
                    address = ""
                    
                    parts = contact_info.split(" | ")
                    for part in parts:
                        if part.startswith("Emails:"):
                            email = part.replace("Emails:", "").strip()
                        elif part.startswith("Phones:"):
                            phone = part.replace("Phones:", "").strip()
                        elif part.startswith("LinkedIn:"):
                            linkedin = part.replace("LinkedIn:", "").strip()
                        elif part.startswith("Instagram:"):
                            instagram = part.replace("Instagram:", "").strip()
                        elif part.startswith("Address:"):
                            address = part.replace("Address:", "").strip()
                else:
                    # Use the new format fields
                    email = row.get("Email", "")
                    phone = row.get("Phone", "")
                    linkedin = row.get("LinkedIn", "")
                    instagram = row.get("Instagram", "")
                    address = row.get("Physical Address", "")

                # Prepare row data with all required fields
                row_data = {
                    "Company Name": row.get("Company Name", ""),
                    "URL": row.get("URL", ""),
                    "Primary Services": row.get("Primary Services", ""),
                    "AI Mentions": row.get("AI Mentions", ""),
                    "Decision Makers": row.get("Decision Makers", ""),
                    "Email": email or row.get("Email", ""),  # Try both formats
                    "Phone": phone or row.get("Phone", ""),  # Try both formats
                    "LinkedIn": linkedin or row.get("LinkedIn", ""),  # Try both formats
                    "Instagram": instagram or row.get("Instagram", ""),  # Try both formats
                    "Physical Address": address or row.get("Physical Address", ""),  # Try both formats
                    "AI Interest Score": row.get("AI Interest Score", ""),
                    "Qualification Notes": row.get("Qualification Notes", "")
                }
                writer.writerow(row_data)
            
        print(colored("Data saved successfully", "green"))
        return True
        
    except Exception as e:
        print(colored(f"Error saving data: {str(e)}", "red"))
        return False

def main():
    """Main function to run the lead generation process"""
    try:
        print(colored("Setting up web tools...", "cyan"))
        web_tools = WebTools()
        
        print(colored("Creating tasks...", "cyan"))
        tasks = create_tasks(web_tools)
        
        print(colored("Setting up crew...", "cyan"))
        crew = Crew(
            agents=[task.agent for task in tasks],
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        print(colored(f"Starting lead generation process for {NUM_PROSPECTS} agencies...", "cyan"))
        result = crew.kickoff()
        
        # Process the final result
        if isinstance(result, list) and len(result) > 0:
            final_result = result[-1]  # Get the last task's result
            if isinstance(final_result, str):
                try:
                    # Try to parse as JSON if it's a string
                    import json
                    final_result = json.loads(final_result)
                except json.JSONDecodeError:
                    pass
            
            # Generate output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"lead_generation_output/leads_{timestamp}.csv"
            
            # Save the data
            save_task(final_result, output_file)
        
        print(colored(f"\nLead generation process completed successfully for {NUM_PROSPECTS} agencies!", "green"))
        
    except Exception as e:
        print(colored(f"\nError during lead generation: {str(e)}", "red"))
        raise
        
    finally:
        print(colored("Cleaning up crew resources...", "cyan"))
        if 'web_tools' in locals():
            web_tools.cleanup()
            print(colored("Closing Chrome WebDriver...", "cyan"))

if __name__ == "__main__":
    main() 
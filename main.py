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
OUTPUT_DIR = "static/downloads"
MODEL = "gpt-4o-mini"
DEFAULT_SEARCH_QUERY = "UK influencer talent marketing agency"
DEFAULT_NUM_PROSPECTS = 3  # Number of agencies to find

def create_tasks(web_tools, search_query=None, num_prospects=None, output_file=None):
    """Create tasks for the crew"""
    # Use default values if not provided
    search_query = search_query or DEFAULT_SEARCH_QUERY
    num_prospects = num_prospects or DEFAULT_NUM_PROSPECTS
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate output filename if not provided
    if not output_file:
        safe_query = "".join(c for c in search_query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_query = safe_query.replace(' ', '_')[:50]  # Limit filename length
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"{safe_query}_leads_{timestamp}.csv")
    
    tasks = []
    
    # Create agents
    query_analyzer = Agent(
        role="Query Analyzer",
        goal="Analyze search query and formulate search strategy",
        backstory="""You are an expert at understanding search queries and formulating effective search strategies. 
        You can identify key elements like location, industry, and business type from a query and create a focused 
        search plan that will yield relevant results.""",
        tools=web_tools.tools,
        allow_delegation=False,
        verbose=True,
        memory=True,
        llm_model=MODEL
    )
    
    researcher = Agent(
        role="Lead Researcher",
        goal=f"Find EXACTLY {num_prospects} potential agency clients",
        backstory="""You are a Senior Research Analyst specializing in identifying potential clients. 
        You MUST find EXACTLY {num_prospects} agencies, no more, no less. Do not disqualify any agencies 
        based on AI mentions or potential - just find agencies that match the location and industry. 
        You are thorough in your research and always verify information from multiple sources.""",
        tools=web_tools.tools,
        allow_delegation=True,
        verbose=True,
        memory=True,
        llm_model=MODEL
    )
    
    qualifier = Agent(
        role="Lead Qualifier",
        goal="Research and qualify each potential client",
        backstory="""You are an expert at analyzing companies and scoring their potential. Your job is to:
        1. Process EVERY prospect given to you, one at a time
        2. Collect ALL available information about each prospect
        3. Score their AI Interest (1-10) based on their technology mentions and innovation focus
        4. Record ALL information in the CSV, regardless of their score
        
        Never skip or disqualify any prospects. Your role is to gather information and score, not to filter.""",
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
        data is properly formatted and saved. You must include the search query in each row 
        and save ALL prospects that were qualified, regardless of their scores.""",
        tools=web_tools.tools,
        allow_delegation=False,
        verbose=True,
        memory=True,
        llm_model=MODEL
    )
    
    # Task 1: Analyze search query
    analyze_task = Task(
        description=f"""Analyze the search query "{search_query}" and identify:
        1. Target location/region
        2. Industry/business type
        3. Specific service focus
        4. Any other relevant criteria
        
        Format your response as a dictionary with these fields:
        {{
            "location": "identified location or region",
            "industry": "identified industry or business type",
            "service_focus": "specific service focus",
            "additional_criteria": ["criterion1", "criterion2", ...]
        }}
        """,
        expected_output="A dictionary containing analyzed search query components",
        agent=query_analyzer
    )
    tasks.append(analyze_task)
    
    # Task 2: Search for agencies
    search_task = Task(
        description=f"""Using the analyzed query components from the previous task, search for EXACTLY {num_prospects} agencies that match the criteria.
        Focus on finding agencies that:
        1. Match the specified location and industry
        2. Have a digital presence
        3. Are established businesses (not individual freelancers)
        4. Have a website with contact information
        
        Search query: "{search_query}"
        
        Avoid:
        - Individual practitioners/freelancers
        - Generic business listings
        - Directory or listing websites
        - Software platforms
        
        You MUST return EXACTLY {num_prospects} agency URLs. Do not filter based on:
        - AI mentions or technology focus
        - Size of the agency
        - Age of the company
        - Current services offered
        
        Process each URL one at a time and return ALL of them.
        """,
        expected_output=f"A list of EXACTLY {num_prospects} URLs for relevant agencies",
        agent=researcher
    )
    tasks.append(search_task)
    
    # Task 3: Qualify the leads
    qualify_task = Task(
        description=f"""For EACH URL provided in the previous task:
        1. Research the agency's services and focus
        2. Look for AI or innovation mentions
        3. Analyze their client base and projects
        4. Identify and extract contact information using the extract_contact_info tool
        5. Assess their potential interest in AI solutions
        
        You MUST process EVERY prospect given to you, one at a time, and record their information in the CSV.
        Never skip or combine prospects. Process each prospect thoroughly before moving to the next one.
        
        For each prospect:
        1. First use the extract_contact_info tool to get ALL contact details and social media links
        2. Then use get_website_content to analyze their services and AI mentions
        3. Create a complete dictionary entry with ALL required fields
        4. Save each prospect to the CSV file immediately after processing
        
        Format your response as a list of dictionaries with EXACTLY these fields for each agency:
        {{
            "Search Query": "{search_query}",  # Add the search query to each entry
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
        }}
        
        Make sure to:
        1. Include ALL contact information found by the extract_contact_info tool
        2. Process and return data for ALL prospects, regardless of their scores
        3. Include the exact search query in each entry
        4. Fill in ALL fields for each prospect
        5. Save each prospect to the CSV file immediately after processing
        """,
        expected_output="A list of dictionaries containing qualified lead information with complete contact details",
        agent=qualifier
    )
    tasks.append(qualify_task)
    
    # Task 4: Save the data
    save_task = Task(
        description=f"""Save all qualified leads to the CSV file.
        The CSV should have the following columns:
        - Search Query
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
        
        IMPORTANT: 
        1. Make sure to include ALL contact information and social media links in the CSV
        2. Save ALL prospects that were qualified, regardless of their scores
        3. The search query "{search_query}" must be included in each row
        4. Verify that all required fields are present before saving
        
        Use the save_to_csv_file tool to save the data to: {output_file}
        """,
        expected_output="A confirmation message that the data was saved successfully",
        agent=data_manager
    )
    tasks.append(save_task)
    
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
        tasks = create_tasks(web_tools)  # Use default values when running directly
        
        print(colored("Setting up crew...", "cyan"))
        crew = Crew(
            agents=[task.agent for task in tasks],
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        print(colored(f"Starting lead generation process for {DEFAULT_NUM_PROSPECTS} agencies...", "cyan"))
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
        
        print(colored(f"\nLead generation process completed successfully for {DEFAULT_NUM_PROSPECTS} agencies!", "green"))
        
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
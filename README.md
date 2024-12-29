# CrewAI Prospects Crew

An AI-powered lead generation system that uses CrewAI to find and qualify potential agency clients. The system searches for agencies based on user-provided search queries and criteria, collecting detailed information and assessing their potential interest in AI solutions.

## Features

- 🔍 Automated agency research without pre-filtering
- 📊 Lead qualification with AI interest scoring (1-10)
- 📝 Contact information extraction
- 💾 Structured data storage (CSV format with search query)
- 🤖 Real-time status updates
- 📥 Downloadable CSV reports

## Requirements

- Python 3.8+
- Chrome WebDriver
- OpenAI API Key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kr3t3n/crewai-prospects-crew.git
cd crewai-prospects-crew
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the FastAPI application:
```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

The application will:
1. Accept a search query and number of prospects
2. Analyze the search query components
3. Find exactly the requested number of agencies
4. Qualify and score each prospect
5. Save results to a CSV file with the search query included

## Project Structure

```
crewai-prospects-crew/
├── app.py              # FastAPI application
├── main.py            # CrewAI implementation
├── web_tools.py       # Web scraping and tools
├── templates/         # HTML templates
├── static/           # Static files and downloads
├── requirements.txt   # Project dependencies
└── README.md         # Project documentation
```

## Agents

The system uses four specialized AI agents:

1. **Query Analyzer**: Analyzes search queries and formulates search strategies
2. **Lead Researcher**: Finds exactly the requested number of agencies
3. **Lead Qualifier**: Processes and scores each prospect
4. **Data Manager**: Saves all data in structured CSV format

## Output

The CSV file includes the following information for each agency:
- Search Query (used to find the agency)
- Company Name
- URL
- Primary Services
- AI Mentions (Yes/No)
- Decision Makers
- Contact Information (Email, Phone)
- Social Media Links (LinkedIn, Instagram)
- Physical Address
- AI Interest Score (1-10)
- Qualification Notes

## Important Notes

- The system processes all prospects without pre-filtering
- Each prospect is processed individually
- The search query is included in both the CSV filename and data
- All prospects are included regardless of their AI interest score

## License

MIT License 
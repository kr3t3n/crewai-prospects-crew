# CrewAI Prospects Crew

An AI-powered lead generation system that uses CrewAI to find and qualify potential agency clients. The system specifically targets UK-based influencer marketing agencies that might be interested in AI solutions.

## Features

- 🔍 Automated agency research and discovery
- 📊 Intelligent lead qualification
- 📝 Contact information extraction
- 💾 Structured data storage (CSV format)
- 🤖 AI potential assessment

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

Run the main script:
```bash
python main.py
```

The script will:
1. Search for potential agency clients
2. Qualify leads based on specified criteria
3. Extract contact information
4. Save results to a CSV file in the `lead_generation_output` directory

## Project Structure

```
crewai-prospects-crew/
├── main.py              # Main script
├── web_tools.py         # Web scraping and tools
├── requirements.txt     # Project dependencies
├── README.md           # Project documentation
└── lead_generation_output/  # Generated CSV files
```

## Configuration

You can modify the number of prospects to search for by changing the `NUM_PROSPECTS` constant in `main.py`.

## Output

The script generates a CSV file with the following information for each agency:
- Company Name
- URL
- Primary Services
- AI Mentions
- Decision Makers
- Contact Information (Email, Phone)
- Social Media Links
- Physical Address
- AI Interest Score
- Qualification Notes

## License

MIT License 
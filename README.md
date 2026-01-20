# LinkedIn Profile Crawler

Simple Selenium-based LinkedIn profile scraper that extracts profile data into JSON format.

## Features

- ✅ Targeted section expansion (no "go back" needed)
- ✅ Anti-detection measures
- ✅ Human-like scrolling and delays
- ✅ Handles LinkedIn's dynamic hash classes
- ✅ Lazy loading support for skills
- ✅ Clean JSON output

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure Chrome and ChromeDriver are installed and ChromeDriver is in your PATH

3. Configure credentials in `.env`:
```
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password
```

## Usage

Run the scraper:
```bash
python main.py
```

Enter the LinkedIn profile URL when prompted.

## Output Format

```json
{
  "name": "John Doe",
  "about": "Full about text...",
  "experiences": [
    {
      "title": "Software Engineer",
      "company": "Tech Corp",
      "duration": "Jan 2020 - Present",
      "description": "..."
    }
  ],
  "education": [
    {
      "school": "University Name",
      "degree": "Bachelor of Science",
      "duration": "2016 - 2020"
    }
  ],
  "skills": ["Python", "JavaScript", "..."],
  "languages": ["English - Native", "Indonesian - Professional"]
}
```

Output files are saved to `data/output/` directory.

## How It Works

1. **Login** - Authenticates with LinkedIn
2. **Navigate** - Goes to target profile
3. **Extract per section**:
   - Scroll to section
   - Click "show more" within that section only
   - Extract data immediately
   - Move to next section
4. **Save** - Outputs JSON file with timestamp

## Anti-Detection Features

- Random delays between actions
- Smooth scrolling behavior
- Disabled automation flags
- Human-like interaction patterns

## Notes

- LinkedIn may rate limit or block automated access
- Use responsibly and respect LinkedIn's Terms of Service
- Consider adding delays between multiple profile scrapes

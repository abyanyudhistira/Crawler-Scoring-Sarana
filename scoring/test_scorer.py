"""
Test script to verify scoring system without RabbitMQ
"""
import json
from scorer import ProfileScorer


def load_sample_profile():
    """Load a sample profile for testing"""
    return {
        "profile_url": "https://linkedin.com/in/test",
        "name": "John Doe",
        "about": "Experienced backend developer with 5 years of experience building scalable web applications using Python, FastAPI, and PostgreSQL. Passionate about clean code and microservices architecture.",
        "skills": [
            "Python",
            "FastAPI",
            "Django",
            "PostgreSQL",
            "MySQL",
            "REST API",
            "Docker",
            "Redis",
            "Git",
            "Linux",
            "AWS",
            "Microservices"
        ],
        "experiences": [
            {
                "title": "Senior Backend Developer",
                "company": "Tech Company · Full-time",
                "duration": "Jan 2021 - Present · 3 yrs 2 mos",
                "location": "Jakarta, Indonesia"
            },
            {
                "title": "Backend Developer",
                "company": "Startup Inc · Full-time",
                "duration": "Jun 2019 - Dec 2020 · 1 yr 7 mos",
                "location": "Jakarta, Indonesia"
            }
        ],
        "education": [
            {
                "school": "University of Indonesia",
                "degree": "Bachelor of Computer Science",
                "year": "2019"
            }
        ],
        "projects": [
            {
                "name": "E-commerce API",
                "description": "Built RESTful API using FastAPI and PostgreSQL"
            }
        ]
    }


def test_scoring():
    """Test the scoring system"""
    print("="*60)
    print("TESTING SCORING SYSTEM")
    print("="*60)
    
    # Load sample profile
    print("\n1. Loading sample profile...")
    profile = load_sample_profile()
    print(f"   Profile: {profile['name']}")
    print(f"   Skills: {len(profile['skills'])} skills")
    print(f"   Experience: {len(profile['experiences'])} positions")
    
    # Load requirements
    print("\n2. Loading requirements...")
    with open('requirements/backend_dev_senior.json', 'r') as f:
        requirements = json.load(f)
    print(f"   Position: {requirements['position']}")
    print(f"   Required skills: {len(requirements['required_skills'])}")
    print(f"   Preferred skills: {len(requirements['preferred_skills'])}")
    
    # Calculate score
    print("\n3. Calculating score...")
    scorer = ProfileScorer(requirements)
    result = scorer.calculate_score(profile)
    
    # Print results
    print("\n" + "="*60)
    print("SCORE RESULT")
    print("="*60)
    print(f"Total Score: {result['total_score']}/{result['max_score']}")
    print(f"Percentage: {result['percentage']}%")
    print(f"Recommendation: {result['recommendation']}")
    
    print("\n" + "-"*60)
    print("BREAKDOWN")
    print("-"*60)
    
    # Skills
    skills = result['breakdown']['skills']
    print(f"\n1. Skills: {skills['score']}/40")
    print(f"   Required: {skills['required']['score']}/30")
    print(f"   - Matched: {len(skills['required']['matches'])} skills")
    for match in skills['required']['matches'][:5]:  # Show first 5
        print(f"     • {match['skill']} → {match['matched_with']} ({match['similarity']}% similar) = {match['points']} pts")
    if skills['required']['missing']:
        print(f"   - Missing: {', '.join(skills['required']['missing'][:5])}")
    
    print(f"   Preferred: {skills['preferred']['score']}/10")
    print(f"   - Matched: {len(skills['preferred']['matches'])} skills")
    for match in skills['preferred']['matches'][:3]:  # Show first 3
        print(f"     • {match['skill']} → {match['matched_with']} ({match['similarity']}% similar) = {match['points']} pts")
    
    # Text similarity
    text_sim = result['breakdown']['text_similarity']
    print(f"\n2. Text Similarity: {text_sim['score']}/30")
    if 'similarity_percentage' in text_sim:
        print(f"   Similarity: {text_sim['similarity_percentage']}%")
    
    # Experience
    exp = result['breakdown']['experience']
    print(f"\n3. Experience: {exp['score']}/20")
    print(f"   Total years: {exp['total_years']} years")
    print(f"   Required: {exp['required_years']} years")
    print(f"   Meets requirement: {'✓' if exp['meets_requirement'] else '✗'}")
    
    # Education
    edu = result['breakdown']['education']
    print(f"\n4. Education: {edu['score']}/10")
    if 'profile_degrees' in edu:
        print(f"   Degrees: {', '.join(edu['profile_degrees'])}")
    print(f"   Required: {', '.join(edu['required_levels'])}")
    if 'meets_requirement' in edu:
        print(f"   Meets requirement: {'✓' if edu['meets_requirement'] else '✗'}")
    
    print("\n" + "="*60)
    
    # Save result
    print("\n4. Saving result...")
    import os
    from datetime import datetime
    
    os.makedirs('data/scores', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"data/scores/test_result_{timestamp}.json"
    
    output = {
        'profile': profile,
        'requirements_id': 'backend_dev_senior',
        'score': result,
        'scored_at': datetime.now().isoformat()
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"   Saved to: {filename}")
    
    print("\n✓ Test completed successfully!")


if __name__ == "__main__":
    test_scoring()

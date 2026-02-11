"""
Simple Scoring System - All in One
Usage: python score.py
"""
import json
import os
import csv
import re
from datetime import datetime
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Scorer:
    def __init__(self, requirements):
        self.requirements = requirements
        self.breakdown = {}
    
    def score(self, profile):
        """Calculate total score"""
        total = 0
        max_score = 130  # Updated: 100 + 30 for demographics
        
        # 1. Skills (40 points)
        skills_score = self._score_skills(profile.get('skills', []))
        total += skills_score
        
        # 2. Text similarity (30 points)
        text_score = self._score_text(profile)
        total += text_score
        
        # 3. Experience (20 points)
        exp_score = self._score_experience(profile.get('experiences', []))
        total += exp_score
        
        # 4. Education (10 points)
        edu_score = self._score_education(profile.get('education', []))
        total += edu_score
        
        # 5. Gender (10 points) - NEW
        gender_score = self._score_gender(profile.get('gender', 'Unknown'))
        total += gender_score
        
        # 6. Location (10 points) - NEW
        location_score = self._score_location(profile.get('location', 'N/A'))
        total += location_score
        
        # 7. Age (10 points) - NEW
        age_score = self._score_age(profile.get('estimated_age', 'Unknown'))
        total += age_score
        
        percentage = (total / max_score) * 100
        
        return {
            'total_score': round(total, 2),
            'max_score': max_score,
            'percentage': round(percentage, 2),
            'breakdown': self.breakdown,
            'recommendation': self._get_recommendation(percentage)
        }
    
    def _score_skills(self, profile_skills):
        """Score skills (40 points)"""
        required = self.requirements.get('required_skills', {})
        preferred = self.requirements.get('preferred_skills', {})
        
        # Normalize skills
        skills_list = []
        if isinstance(profile_skills, list):
            for s in profile_skills:
                if isinstance(s, dict):
                    name = s.get('name', '')
                    if name and name != 'N/A':
                        skills_list.append(name.lower().strip())
                elif isinstance(s, str) and s and s != 'N/A':
                    skills_list.append(s.lower().strip())
        
        # Score required (30 points)
        req_score = 0
        req_matches = []
        if required:
            total_weight = sum(required.values())
            for skill, weight in required.items():
                for profile_skill in skills_list:
                    ratio = fuzz.ratio(skill.lower(), profile_skill)
                    if ratio >= 80:
                        points = (weight / total_weight) * 30 * (ratio / 100)
                        req_score += points
                        req_matches.append(skill)
                        break
        
        # Score preferred (10 points)
        pref_score = 0
        pref_matches = []
        if preferred:
            total_weight = sum(preferred.values())
            for skill, weight in preferred.items():
                for profile_skill in skills_list:
                    ratio = fuzz.ratio(skill.lower(), profile_skill)
                    if ratio >= 80:
                        points = (weight / total_weight) * 10 * (ratio / 100)
                        pref_score += points
                        pref_matches.append(skill)
                        break
        
        total = req_score + pref_score
        self.breakdown['skills'] = {
            'score': round(total, 2),
            'required_matched': len(req_matches),
            'preferred_matched': len(pref_matches)
        }
        return total
    
    def _score_text(self, profile):
        """Score text similarity (30 points)"""
        job_desc = self.requirements.get('job_description', '')
        if not job_desc:
            self.breakdown['text_similarity'] = {'score': 0}
            return 0
        
        # Collect profile text
        texts = []
        about = profile.get('about', '')
        if about and about != 'N/A':
            texts.append(about)
        
        for exp in profile.get('experiences', []):
            if isinstance(exp, dict):
                title = exp.get('title', '')
                company = exp.get('company', '')
                if title:
                    texts.append(title)
                if company:
                    texts.append(company)
        
        if not texts:
            self.breakdown['text_similarity'] = {'score': 0}
            return 0
        
        combined = ' '.join(texts)
        
        try:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
            tfidf = vectorizer.fit_transform([job_desc, combined])
            similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            score = similarity * 30
            self.breakdown['text_similarity'] = {'score': round(score, 2)}
            return score
        except:
            self.breakdown['text_similarity'] = {'score': 0}
            return 0
    
    def _score_experience(self, experiences):
        """Score experience (20 points)"""
        min_years = self.requirements.get('min_experience_years', 0)
        
        total_months = 0
        for exp in experiences:
            if not isinstance(exp, dict):
                continue
            duration = exp.get('duration', '')
            if not duration:
                continue
            
            years = 0
            months = 0
            year_match = re.search(r'(\d+)\s*yr', duration)
            if year_match:
                years = int(year_match.group(1))
            month_match = re.search(r'(\d+)\s*mo', duration)
            if month_match:
                months = int(month_match.group(1))
            
            total_months += (years * 12) + months
        
        total_years = total_months / 12
        
        if total_years >= min_years:
            score = 20
        else:
            score = (total_years / min_years) * 20 if min_years > 0 else 0
        
        self.breakdown['experience'] = {
            'score': round(score, 2),
            'years': round(total_years, 1)
        }
        return score
    
    def _score_education(self, education):
        """Score education (10 points)"""
        required = self.requirements.get('education_level', [])
        if not required:
            self.breakdown['education'] = {'score': 10}
            return 10
        
        if not education:
            self.breakdown['education'] = {'score': 0}
            return 0
        
        levels = {
            'high school': 1, 'diploma': 2, 'associate': 2,
            'bachelor': 3, 'master': 4, 'mba': 4,
            'doctoral': 5, 'phd': 5
        }
        
        highest = 0
        for edu in education:
            if not isinstance(edu, dict):
                continue
            degree = edu.get('degree', '').lower()
            if not degree:
                continue
            for level_name, level_val in levels.items():
                if level_name in degree and level_val > highest:
                    highest = level_val
        
        required_level = 0
        for req in required:
            for level_name, level_val in levels.items():
                if level_name in req.lower() and level_val > required_level:
                    required_level = level_val
        
        if highest >= required_level:
            score = 10
        elif highest > 0:
            score = (highest / required_level) * 10 if required_level > 0 else 0
        else:
            score = 0
        
        self.breakdown['education'] = {'score': round(score, 2)}
        return score
    
    def _score_gender(self, profile_gender):
        """Score gender match (10 points)"""
        required_gender = self.requirements.get('required_gender', None)
        
        if not required_gender:
            self.breakdown['gender'] = {'score': 10, 'note': 'No requirement'}
            return 10
        
        if not profile_gender or profile_gender == 'Unknown':
            self.breakdown['gender'] = {'score': 0, 'profile': profile_gender, 'required': required_gender}
            return 0
        
        if profile_gender.lower() == required_gender.lower():
            score = 10
        else:
            score = 0
        
        self.breakdown['gender'] = {'score': score, 'profile': profile_gender, 'required': required_gender}
        return score
    
    def _score_location(self, profile_location):
        """Score location match (10 points)"""
        required_location = self.requirements.get('required_location', None)
        
        if not required_location:
            self.breakdown['location'] = {'score': 10, 'note': 'No requirement'}
            return 10
        
        if not profile_location or profile_location == 'N/A':
            self.breakdown['location'] = {'score': 0, 'profile': profile_location, 'required': required_location}
            return 0
        
        # Fuzzy match
        similarity = fuzz.ratio(profile_location.lower(), required_location.lower())
        
        if similarity >= 80:
            score = (similarity / 100) * 10
        else:
            score = 0
        
        self.breakdown['location'] = {'score': round(score, 2), 'profile': profile_location, 'required': required_location, 'similarity': similarity}
        return score
    
    def _score_age(self, estimated_age):
        """Score age range match (10 points)"""
        required_age_range = self.requirements.get('required_age_range', None)
        
        if not required_age_range:
            self.breakdown['age'] = {'score': 10, 'note': 'No requirement'}
            return 10
        
        if not estimated_age or estimated_age == 'Unknown':
            self.breakdown['age'] = {'score': 0, 'estimated': estimated_age, 'required': required_age_range}
            return 0
        
        # Extract age value
        age_value = None
        if isinstance(estimated_age, dict):
            age_value = estimated_age.get('estimated_age')
        elif isinstance(estimated_age, (int, float)):
            age_value = estimated_age
        
        if not age_value:
            self.breakdown['age'] = {'score': 0, 'estimated': estimated_age, 'required': required_age_range}
            return 0
        
        min_age = required_age_range.get('min', 0)
        max_age = required_age_range.get('max', 100)
        
        if min_age <= age_value <= max_age:
            score = 10
        else:
            # Partial points if close (within 5 years)
            if age_value < min_age:
                diff = min_age - age_value
            else:
                diff = age_value - max_age
            
            if diff <= 5:
                score = max(0, 10 - (diff * 2))
            else:
                score = 0
        
        self.breakdown['age'] = {'score': round(score, 2), 'estimated': age_value, 'required': f"{min_age}-{max_age}"}
        return score
    
    def _get_recommendation(self, percentage):
        """Get hiring recommendation based on percentage"""
        if percentage >= 80:
            return "Highly Recommended - Strong match"
        elif percentage >= 60:
            return "Recommended - Good match"
        elif percentage >= 40:
            return "Consider - Moderate match"
        else:
            return "Not Recommended - Weak match"


def batch_score(profiles_dir, requirements_id):
    """Score all profiles and save to CSV"""
    
    print("="*60)
    print("BATCH SCORING")
    print("="*60)
    
    # Load requirements
    req_file = f'requirements/{requirements_id}.json'
    if not os.path.exists(req_file):
        print(f"✗ Requirements not found: {req_file}")
        return
    
    with open(req_file, 'r') as f:
        requirements = json.load(f)
    
    print(f"\nPosition: {requirements.get('position')}")
    print(f"Profiles: {profiles_dir}")
    
    # Get profiles
    files = [f for f in os.listdir(profiles_dir) if f.endswith('.json')]
    if not files:
        print(f"✗ No JSON files found")
        return
    
    print(f"Found: {len(files)} profiles\n")
    
    # Score each profile
    results = []
    scorer = Scorer(requirements)
    
    for i, filename in enumerate(files, 1):
        try:
            with open(os.path.join(profiles_dir, filename), 'r') as f:
                profile = json.load(f)
            
            # Get name
            name = profile.get('name', '').strip()
            if not name or name == 'N/A':
                url = profile.get('profile_url', '')
                if '/in/' in url:
                    name = url.split('/in/')[-1].split('/')[0].split('?')[0]
                    name = name.replace('-', ' ').title()
                else:
                    name = filename.replace('.json', '').replace('_', ' ').title()
            
            # Score
            score_result = scorer.score(profile)
            
            results.append({
                'name': name,
                'profile_url': profile.get('profile_url', ''),
                'score': score_result['percentage']
            })
            
            print(f"[{i}/{len(files)}] {name}: {score_result['percentage']}%")
            
        except Exception as e:
            print(f"[{i}/{len(files)}] Error: {e}")
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Save CSV
    os.makedirs('data/scores', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f'data/scores/scores_{requirements_id}_{timestamp}.csv'
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['rank', 'name', 'profile_url', 'score'])
        writer.writeheader()
        for rank, result in enumerate(results, 1):
            writer.writerow({
                'rank': rank,
                'name': result['name'],
                'profile_url': result['profile_url'],
                'score': result['score']
            })
    
    print(f"\n{'='*60}")
    print(f"✓ Saved: {csv_file}")
    print(f"{'='*60}")
    print(f"\nTop 5:")
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r['name']}: {r['score']}%")
    print()


def main():
    print("Available requirements:")
    reqs = [f.replace('.json', '') for f in os.listdir('requirements') if f.endswith('.json')]
    for r in reqs:
        print(f"  - {r}")
    
    req_id = input(f"\nRequirements ID (default: desk_collection): ").strip()
    if not req_id:
        req_id = 'desk_collection'
    
    profiles_dir = input(f"Profiles directory (default: ../crawler/data/output): ").strip()
    if not profiles_dir:
        profiles_dir = '../crawler/data/output'
    
    if not os.path.exists(profiles_dir):
        print(f"✗ Directory not found: {profiles_dir}")
        return
    
    batch_score(profiles_dir, req_id)


if __name__ == "__main__":
    main()

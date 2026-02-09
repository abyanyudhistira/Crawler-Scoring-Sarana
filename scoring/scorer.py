"""
Hybrid Scoring System
Combines: Keyword Matching + Fuzzy Matching + TF-IDF Similarity
"""
import re
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ProfileScorer:
    def __init__(self, requirements):
        """
        Initialize scorer with requirements
        
        Args:
            requirements (dict): Job requirements from JSON
        """
        self.requirements = requirements
        self.score_breakdown = {}
    
    def calculate_score(self, profile_data):
        """
        Calculate total score for a profile
        
        Args:
            profile_data (dict): Profile data from crawler
            
        Returns:
            dict: Score result with breakdown
        """
        total_score = 0
        max_score = 100
        
        # 1. Skills matching (40 points)
        skills_score = self._score_skills(profile_data.get('skills', []))
        total_score += skills_score
        
        # 2. TF-IDF similarity for about/experience (30 points)
        text_score = self._score_text_similarity(profile_data)
        total_score += text_score
        
        # 3. Experience years (20 points)
        exp_score = self._score_experience(profile_data.get('experiences', []))
        total_score += exp_score
        
        # 4. Education level (10 points)
        edu_score = self._score_education(profile_data.get('education', []))
        total_score += edu_score
        
        return {
            'total_score': round(total_score, 2),
            'max_score': max_score,
            'percentage': round((total_score / max_score) * 100, 2),
            'breakdown': self.score_breakdown,
            'recommendation': self._get_recommendation(total_score)
        }
    
    def _score_skills(self, profile_skills):
        """
        Score skills using keyword + fuzzy matching
        
        40 points total:
        - Required skills: 30 points
        - Preferred skills: 10 points
        """
        required_skills = self.requirements.get('required_skills', {})
        preferred_skills = self.requirements.get('preferred_skills', {})
        
        # Normalize profile skills
        profile_skills_lower = [s.lower().strip() for s in profile_skills if s and s != 'N/A']
        
        # Score required skills (30 points)
        required_score = 0
        required_max = 30
        required_matches = []
        required_missing = []
        
        if required_skills:
            total_weight = sum(required_skills.values())
            
            for skill, weight in required_skills.items():
                skill_lower = skill.lower()
                match_found = False
                best_match_ratio = 0
                best_match_skill = None
                
                # Check exact or fuzzy match
                for profile_skill in profile_skills_lower:
                    ratio = fuzz.ratio(skill_lower, profile_skill)
                    
                    if ratio >= 80:  # 80% similarity threshold
                        if ratio > best_match_ratio:
                            best_match_ratio = ratio
                            best_match_skill = profile_skill
                            match_found = True
                
                if match_found:
                    # Award points based on weight and match quality
                    points = (weight / total_weight) * required_max * (best_match_ratio / 100)
                    required_score += points
                    required_matches.append({
                        'skill': skill,
                        'matched_with': best_match_skill,
                        'similarity': best_match_ratio,
                        'points': round(points, 2)
                    })
                else:
                    required_missing.append(skill)
        
        # Score preferred skills (10 points)
        preferred_score = 0
        preferred_max = 10
        preferred_matches = []
        
        if preferred_skills:
            total_weight = sum(preferred_skills.values())
            
            for skill, weight in preferred_skills.items():
                skill_lower = skill.lower()
                match_found = False
                best_match_ratio = 0
                best_match_skill = None
                
                for profile_skill in profile_skills_lower:
                    ratio = fuzz.ratio(skill_lower, profile_skill)
                    
                    if ratio >= 80:
                        if ratio > best_match_ratio:
                            best_match_ratio = ratio
                            best_match_skill = profile_skill
                            match_found = True
                
                if match_found:
                    points = (weight / total_weight) * preferred_max * (best_match_ratio / 100)
                    preferred_score += points
                    preferred_matches.append({
                        'skill': skill,
                        'matched_with': best_match_skill,
                        'similarity': best_match_ratio,
                        'points': round(points, 2)
                    })
        
        total_skills_score = required_score + preferred_score
        
        self.score_breakdown['skills'] = {
            'score': round(total_skills_score, 2),
            'max_score': 40,
            'required': {
                'score': round(required_score, 2),
                'max_score': required_max,
                'matches': required_matches,
                'missing': required_missing
            },
            'preferred': {
                'score': round(preferred_score, 2),
                'max_score': preferred_max,
                'matches': preferred_matches
            }
        }
        
        return total_skills_score
    
    def _score_text_similarity(self, profile_data):
        """
        Score using TF-IDF + Cosine Similarity
        Compare job description with profile about + experience descriptions
        
        30 points total
        """
        job_description = self.requirements.get('job_description', '')
        
        if not job_description or job_description == 'N/A':
            self.score_breakdown['text_similarity'] = {
                'score': 0,
                'max_score': 30,
                'note': 'No job description provided'
            }
            return 0
        
        # Collect profile text
        profile_text = []
        
        # Add about section
        about = profile_data.get('about', '')
        if about and about != 'N/A':
            profile_text.append(about)
        
        # Add experience descriptions
        experiences = profile_data.get('experiences', [])
        for exp in experiences:
            if isinstance(exp, dict):
                title = exp.get('title', '')
                company = exp.get('company', '')
                if title:
                    profile_text.append(title)
                if company:
                    profile_text.append(company)
        
        # Add projects
        projects = profile_data.get('projects', [])
        for proj in projects:
            if isinstance(proj, dict):
                name = proj.get('name', '')
                desc = proj.get('description', '')
                if name:
                    profile_text.append(name)
                if desc and desc != 'N/A':
                    profile_text.append(desc)
        
        if not profile_text:
            self.score_breakdown['text_similarity'] = {
                'score': 0,
                'max_score': 30,
                'note': 'No profile text available'
            }
            return 0
        
        # Combine profile text
        combined_profile_text = ' '.join(profile_text)
        
        # Calculate TF-IDF similarity
        try:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
            tfidf_matrix = vectorizer.fit_transform([job_description, combined_profile_text])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Convert similarity (0-1) to score (0-30)
            score = similarity * 30
            
            self.score_breakdown['text_similarity'] = {
                'score': round(score, 2),
                'max_score': 30,
                'similarity_percentage': round(similarity * 100, 2)
            }
            
            return score
        
        except Exception as e:
            self.score_breakdown['text_similarity'] = {
                'score': 0,
                'max_score': 30,
                'error': str(e)
            }
            return 0
    
    def _score_experience(self, experiences):
        """
        Score based on years of experience
        
        20 points total
        """
        min_years = self.requirements.get('min_experience_years', 0)
        
        if not experiences:
            self.score_breakdown['experience'] = {
                'score': 0,
                'max_score': 20,
                'total_years': 0,
                'required_years': min_years
            }
            return 0
        
        # Calculate total years
        total_months = 0
        
        for exp in experiences:
            if not isinstance(exp, dict):
                continue
            
            duration = exp.get('duration', '')
            if not duration or duration == 'N/A':
                continue
            
            # Parse duration (e.g., "2 yrs 3 mos", "6 mos", "1 yr")
            years = 0
            months = 0
            
            # Extract years
            year_match = re.search(r'(\d+)\s*yr', duration)
            if year_match:
                years = int(year_match.group(1))
            
            # Extract months
            month_match = re.search(r'(\d+)\s*mo', duration)
            if month_match:
                months = int(month_match.group(1))
            
            total_months += (years * 12) + months
        
        total_years = total_months / 12
        
        # Calculate score
        if total_years >= min_years:
            # Full points if meets requirement
            score = 20
        else:
            # Partial points based on percentage
            score = (total_years / min_years) * 20 if min_years > 0 else 0
        
        self.score_breakdown['experience'] = {
            'score': round(score, 2),
            'max_score': 20,
            'total_years': round(total_years, 1),
            'required_years': min_years,
            'meets_requirement': total_years >= min_years
        }
        
        return score
    
    def _score_education(self, education):
        """
        Score based on education level
        
        10 points total
        """
        required_levels = self.requirements.get('education_level', [])
        
        if not required_levels:
            self.score_breakdown['education'] = {
                'score': 10,
                'max_score': 10,
                'note': 'No education requirement'
            }
            return 10
        
        if not education:
            self.score_breakdown['education'] = {
                'score': 0,
                'max_score': 10,
                'profile_education': [],
                'required_levels': required_levels
            }
            return 0
        
        # Education level hierarchy
        level_hierarchy = {
            'high school': 1,
            'diploma': 2,
            'associate': 2,
            'bachelor': 3,
            'master': 4,
            'mba': 4,
            'doctoral': 5,
            'phd': 5
        }
        
        # Get highest education level from profile
        highest_profile_level = 0
        profile_degrees = []
        
        for edu in education:
            if not isinstance(edu, dict):
                continue
            
            degree = edu.get('degree', '').lower()
            if not degree or degree == 'n/a':
                continue
            
            profile_degrees.append(degree)
            
            for level_name, level_value in level_hierarchy.items():
                if level_name in degree:
                    if level_value > highest_profile_level:
                        highest_profile_level = level_value
        
        # Get required level
        required_level = 0
        for req_level in required_levels:
            req_level_lower = req_level.lower()
            for level_name, level_value in level_hierarchy.items():
                if level_name in req_level_lower:
                    if level_value > required_level:
                        required_level = level_value
        
        # Calculate score
        if highest_profile_level >= required_level:
            score = 10
        elif highest_profile_level > 0:
            # Partial points
            score = (highest_profile_level / required_level) * 10 if required_level > 0 else 0
        else:
            score = 0
        
        self.score_breakdown['education'] = {
            'score': round(score, 2),
            'max_score': 10,
            'profile_degrees': profile_degrees,
            'required_levels': required_levels,
            'meets_requirement': highest_profile_level >= required_level
        }
        
        return score
    
    def _get_recommendation(self, total_score):
        """Get hiring recommendation based on score"""
        if total_score >= 80:
            return "Highly Recommended - Strong match"
        elif total_score >= 60:
            return "Recommended - Good match"
        elif total_score >= 40:
            return "Consider - Moderate match"
        else:
            return "Not Recommended - Weak match"

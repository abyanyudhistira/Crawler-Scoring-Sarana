"""LinkedIn profile data extractor - extraction logic only"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from helper.browser_helper import human_delay, smooth_scroll, scroll_page_to_load, create_driver
from helper.auth_helper import login
from helper.extraction_helper import click_show_all, click_back_arrow, extract_items_from_detail_page


class LinkedInCrawler:
    def __init__(self):
        """Initialize crawler with browser"""
        self.driver = create_driver()
        self.wait = WebDriverWait(self.driver, 10)
    
    def login(self):
        """Login to LinkedIn"""
        login(self.driver)
    
    def get_profile(self, url):
        """Main method to scrape a LinkedIn profile"""
        print(f"\nScraping profile: {url}")
        self.driver.get(url)
        human_delay(3, 5)
        
        # Scroll to load all sections
        scroll_page_to_load(self.driver)
        
        data = {}
        
        print("\n" + "="*60)
        print("EXTRACTING PROFILE DATA")
        print("="*60)
        
        print("\n[1/6] Extracting name...")
        data['name'] = self.extract_name()
        print(f"→ {data['name']}")
        
        print("\n[2/6] Extracting about...")
        data['about'] = self.extract_about()
        print(f"→ {len(data['about'])} characters")
        
        print("\n[3/6] Extracting experiences...")
        data['experiences'] = self.extract_experiences()
        print(f"→ Found {len(data['experiences'])} experiences")
        
        print("\n[4/6] Extracting education...")
        data['education'] = self.extract_education()
        print(f"→ Found {len(data['education'])} education entries")
        
        print("\n[5/6] Extracting skills...")
        data['skills'] = self.extract_skills()
        print(f"→ Found {len(data['skills'])} skills")
        
        print("\n[6/7] Extracting projects...")
        data['projects'] = self.extract_projects()
        print(f"→ Found {len(data['projects'])} projects")
        
        print("\n[7/7] Extracting languages...")
        data['languages'] = self.extract_languages()
        print(f"→ Found {len(data['languages'])} languages")
        
        print("\n" + "="*60)
        print("PROFILE EXTRACTION COMPLETE!")
        print("="*60)
        
        return data
    
    def extract_name(self):
        """Extract profile name"""
        selectors = [
            (By.CSS_SELECTOR, "h1.text-heading-xlarge"),
            (By.XPATH, "//h1[contains(@class, 'inline')]"),
            (By.XPATH, "//h1[contains(@class, 'text-heading')]"),
        ]
        
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                return element.text.strip()
            except NoSuchElementException:
                continue
        return "N/A"
    
    def extract_about(self):
        """Extract about section"""
        try:
            about_section = self.driver.find_element(
                By.XPATH, 
                "//section[contains(@id, 'about') or .//h2[contains(., 'About')]]"
            )
            
            smooth_scroll(self.driver, about_section)
            
            # Click see more if exists
            try:
                see_more = about_section.find_element(By.XPATH, ".//button[contains(., 'more')]")
                see_more.click()
                human_delay(1, 1.5)
            except:
                pass
            
            text_selectors = [
                ".//div[contains(@class, 'display-flex')]//span[@aria-hidden='true']",
                ".//div[contains(@class, 'inline-show-more-text')]//span",
                ".//span[@aria-hidden='true']",
            ]
            
            for selector in text_selectors:
                try:
                    text_element = about_section.find_element(By.XPATH, selector)
                    text = text_element.text.strip()
                    if text and len(text) > 20:
                        return text
                except NoSuchElementException:
                    continue
            
            return "N/A"
        except Exception:
            return "N/A"
    
    def extract_experiences(self):
        """Extract experience section with show all flow"""
        experiences = []
        try:
            print("Looking for experience section...")
            
            # Find section
            exp_section = None
            selectors = [
                "//section[contains(@id, 'experience')]",
                "//section[.//div[@id='experience']]",
                "//section[.//h2[contains(text(), 'Experience')]]",
            ]
            
            for selector in selectors:
                try:
                    exp_section = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print("✓ Found section")
                    break
                except TimeoutException:
                    continue
            
            if not exp_section:
                print("⚠ Experience section not found")
                return experiences
            
            # Click "Show all"
            clicked = click_show_all(self.driver, exp_section)
            
            if clicked:
                # Extract from detail page
                items = extract_items_from_detail_page(self.driver)
                print(f"Processing {len(items)} items...")
                
                # Debug: print raw item count
                if len(items) < 9:
                    print(f"  ⚠ WARNING: Expected 9 experiences but found {len(items)} items")
                    print(f"  This might mean:")
                    print(f"    - Page didn't scroll enough to load all items")
                    print(f"    - Items selector is not matching all elements")
                    print(f"    - Some items are nested/grouped differently")
                
                for idx, item in enumerate(items):
                    try:
                        text = item.text.strip()
                        if not text or len(text) < 20:
                            continue
                        
                        print(f"\n  === Item {idx + 1}/{len(items)} ===")
                        print(f"  Raw text length: {len(text)} chars")
                        print(f"  First 150 chars: {text[:150]}...")
                        
                        # Skip nested items (Skills:, etc)
                        if text.startswith('Skills:') or text.startswith('Skill'):
                            print(f"  → SKIP: Nested skills item")
                            continue
                        
                        # Must have company indicator
                        if ' · ' not in text:
                            print(f"  → SKIP: No company indicator (·)")
                            continue
                        
                        # Split by newlines and remove duplicates (LinkedIn has duplicate lines)
                        all_lines = [l.strip() for l in text.split('\n') if l.strip()]
                        
                        # Remove consecutive duplicates
                        lines = []
                        prev = None
                        for line in all_lines:
                            if line != prev:
                                lines.append(line)
                                prev = line
                        
                        print(f"  Total unique lines: {len(lines)}")
                        for i, line in enumerate(lines[:10]):  # Show first 10
                            print(f"    [{i}] {line[:80]}")
                        
                        # LinkedIn structure after deduplication:
                        # 0: Title
                        # 1: Company (with or without · Type)
                        # 2: Date range (e.g., "Aug 2024 - Present · 6 mos")
                        # 3: Date range again (e.g., "Aug 2024 to Present · 6 mos") 
                        # 4: Location (if exists)
                        # 5+: Description/Skills (skip these)
                        
                        if len(lines) >= 3:
                            # Find location: it's after the duplicate date line
                            location = ""
                            if len(lines) > 4:
                                potential_location = lines[4]
                                # Location is short and doesn't look like description
                                is_location = (
                                    len(potential_location) < 80 and
                                    ' to ' not in potential_location and
                                    '·' not in potential_location and
                                    'http' not in potential_location.lower() and
                                    'www.' not in potential_location.lower() and
                                    not (len(potential_location) > 50 and ' is ' in potential_location)
                                )
                                
                                if is_location:
                                    location = potential_location
                            
                            exp_data = {
                                'title': lines[0],
                                'company': lines[1],
                                'duration': lines[2],
                                'location': location
                            }
                            
                            experiences.append(exp_data)
                            print(f"  ✓ ADDED {len(experiences)}. {exp_data['title']} at {exp_data['company'][:30]}")
                        else:
                            print(f"  → SKIP: Not enough lines ({len(lines)})")
                    
                    except Exception as e:
                        print(f"  Error parsing item {idx}: {e}")
                        continue
                
                # Click back
                click_back_arrow(self.driver)
            
            else:
                # No "Show all" button - extract from main page
                print("  Extracting from main page...")
                items = exp_section.find_elements(By.XPATH, ".//ul/li")
                print(f"  Found {len(items)} items on main page")
                
                for idx, item in enumerate(items):
                    try:
                        text = item.text.strip()
                        if not text or len(text) < 20:
                            continue
                        
                        print(f"\n  === Item {idx + 1}/{len(items)} ===")
                        
                        # Check if this is a GROUPED experience (multiple roles at same company)
                        # Pattern: Company name first (no ·), then multiple roles with ·
                        all_lines = [l.strip() for l in text.split('\n') if l.strip()]
                        lines = []
                        prev = None
                        for line in all_lines:
                            if line != prev:
                                lines.append(line)
                                prev = line
                        
                        print(f"  Lines: {len(lines)}")
                        for i, line in enumerate(lines[:8]):
                            print(f"    [{i}] {line[:80]}")
                        
                        # Detect grouped: 
                        # Grouped = Line 0 is company (no ·), Line 1 is duration (has ·), Line 2+ are roles
                        # Normal = Line 0 is title (no ·), Line 1 is company (has ·)
                        is_grouped = False
                        if len(lines) > 2 and '·' not in lines[0]:
                            # Check line 1: if it's duration format (has · and looks like "Full-time · X yrs")
                            # then line 0 is company name = GROUPED
                            line1_is_duration = (
                                '·' in lines[1] and 
                                ('yr' in lines[1] or 'mo' in lines[1] or 'Full-time' in lines[1] or 'Part-time' in lines[1] or 'Contract' in lines[1])
                            )
                            
                            if line1_is_duration:
                                # Line 0 = Company, Line 1 = Total duration, Line 2+ = Roles
                                is_grouped = True
                        
                        if is_grouped:
                            print(f"  → GROUPED experience detected")
                            # Handle grouped: multiple roles at same company
                            # Structure: Company, Total Duration, Role1 Title, Role1 Duration, Role1 Duration Dup, Role1 Location, Role2 Title...
                            
                            company = lines[0]
                            # total_duration = lines[1]  # Not used per role
                            
                            # Parse roles starting from line 2
                            i = 2
                            while i < len(lines):
                                # Each role: Title, Duration, Duration Dup, Location (optional), Skills (skip)
                                if i >= len(lines):
                                    break
                                
                                role_title = lines[i]
                                
                                # Check if next line is duration (has - or Present)
                                if i + 1 < len(lines) and ('-' in lines[i + 1] or 'Present' in lines[i + 1]):
                                    role_duration = lines[i + 1]
                                    
                                    # Skip duplicate duration line (line i+2)
                                    # Location is at i+3 (if exists and doesn't look like next role title)
                                    role_location = ""
                                    if i + 3 < len(lines):
                                        potential_location = lines[i + 3]
                                        # Check if it's location (not a job title, not skills)
                                        is_location = (
                                            len(potential_location) < 100 and
                                            '·' in potential_location and  # Location usually has · (e.g., "Indonesia · On-site")
                                            not ('-' in potential_location and ('Present' in potential_location or '20' in potential_location)) and  # Not duration
                                            'skill' not in potential_location.lower()  # Not skills line
                                        )
                                        if is_location:
                                            role_location = potential_location
                                            i += 4  # Move to next role (skip title, duration, dup, location)
                                        else:
                                            i += 3  # Move to next role (skip title, duration, dup)
                                    else:
                                        i += 3
                                    
                                    # Add this role as separate experience
                                    exp_data = {
                                        'title': role_title,
                                        'company': company,
                                        'duration': role_duration,
                                        'location': role_location
                                    }
                                    experiences.append(exp_data)
                                    print(f"  ✓ ADDED {len(experiences)}. {exp_data['title']} at {company}")
                                else:
                                    # Not a valid role, skip
                                    i += 1
                            
                            continue
                        
                        # Normal single experience
                        # Line 0 = Title, Line 1 = Company (has ·)
                        if len(lines) >= 2 and '·' in lines[1]:
                            location = ""
                            # Duration is at line 2, duplicate at line 3, location at line 4
                            if len(lines) > 4:
                                potential_location = lines[4]
                                is_location = (
                                    len(potential_location) < 80 and
                                    ' to ' not in potential_location and
                                    'http' not in potential_location.lower() and
                                    'www.' not in potential_location.lower() and
                                    not (len(potential_location) > 50 and ' is ' in potential_location)
                                )
                                if is_location:
                                    location = potential_location
                            
                            exp_data = {
                                'title': lines[0],
                                'company': lines[1],
                                'duration': lines[2] if len(lines) > 2 else "",
                                'location': location
                            }
                            experiences.append(exp_data)
                            print(f"  ✓ ADDED {len(experiences)}. {exp_data['title']}")
                    
                    except Exception as e:
                        print(f"  Error: {e}")
                        continue
        
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        return experiences
    
    def extract_education(self):
        """Extract education section with show all flow"""
        education = []
        try:
            print("Looking for education section...")
            
            edu_section = None
            selectors = [
                "//section[contains(@id, 'education')]",
                "//section[.//div[@id='education']]",
                "//section[.//h2[contains(text(), 'Education')]]",
            ]
            
            for selector in selectors:
                try:
                    edu_section = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print("✓ Found section")
                    break
                except TimeoutException:
                    continue
            
            if not edu_section:
                print("⚠ Education section not found")
                return education
            
            # Click "Show all"
            clicked = click_show_all(self.driver, edu_section)
            
            if clicked:
                items = extract_items_from_detail_page(self.driver)
                
                for item in items:
                    try:
                        text = item.text.strip()
                        if not text or len(text) < 5:
                            continue
                        
                        # Remove consecutive duplicates
                        all_lines = [l.strip() for l in text.split('\n') if l.strip()]
                        lines = []
                        prev = None
                        for line in all_lines:
                            if line != prev:
                                lines.append(line)
                                prev = line
                        
                        print(f"  Education item lines: {len(lines)}")
                        for i, line in enumerate(lines[:6]):
                            print(f"    {i}: {line[:80]}")
                        
                        # LinkedIn structure after deduplication varies:
                        # Sometimes: School, School (dup), Degree, Year
                        # Sometimes: School, Degree, Year
                        # Need to detect which format
                        
                        if len(lines) >= 2:
                            school = lines[0]
                            degree = ""
                            year = ""
                            
                            # Check if line 1 is duplicate of line 0
                            if len(lines) > 1 and lines[1] == lines[0]:
                                # Format: School, School, Degree, Year
                                degree = lines[2] if len(lines) > 2 else ""
                                year_line = lines[3] if len(lines) > 3 else ""
                            else:
                                # Format: School, Degree, Year
                                degree = lines[1] if len(lines) > 1 else ""
                                year_line = lines[2] if len(lines) > 2 else ""
                            
                            # Extract just the end year from year range
                            if year_line:
                                if '-' in year_line or '–' in year_line:
                                    # Split by dash and get last part
                                    parts = year_line.replace('–', '-').split('-')
                                    year = parts[-1].strip()
                                else:
                                    year = year_line.strip()
                            
                            edu_data = {
                                'school': school,
                                'degree': degree,
                                'year': year
                            }
                            education.append(edu_data)
                            print(f"  ✓ {len(education)}. {edu_data['school']}")
                    except Exception as e:
                        print(f"  Error parsing education: {e}")
                        continue
                
                click_back_arrow(self.driver)
            else:
                # No show all, extract from main page
                print("  Extracting from main page...")
                items = edu_section.find_elements(By.XPATH, ".//ul/li")
                
                for item in items:
                    try:
                        text = item.text.strip()
                        if not text or len(text) < 5:
                            continue
                        
                        # Remove consecutive duplicates
                        all_lines = [l.strip() for l in text.split('\n') if l.strip()]
                        lines = []
                        prev = None
                        for line in all_lines:
                            if line != prev:
                                lines.append(line)
                                prev = line
                        
                        print(f"  Education lines ({len(lines)}):")
                        for i, line in enumerate(lines[:6]):
                            print(f"    [{i}] {line[:80]}")
                        
                        if len(lines) >= 2:
                            school = lines[0]
                            degree = ""
                            year = ""
                            
                            # Check if line 1 is duplicate of line 0
                            if len(lines) > 1 and lines[1] == lines[0]:
                                # Format: School, School, Degree, Year
                                degree = lines[2] if len(lines) > 2 else ""
                                year_line = lines[3] if len(lines) > 3 else ""
                            else:
                                # Format: School, Degree, Year
                                degree = lines[1] if len(lines) > 1 else ""
                                year_line = lines[2] if len(lines) > 2 else ""
                            
                            # Extract just the end year from year range
                            if year_line:
                                if '-' in year_line or '–' in year_line:
                                    # Split by dash and get last part
                                    parts = year_line.replace('–', '-').split('-')
                                    year = parts[-1].strip()
                                else:
                                    year = year_line.strip()
                            
                            edu_data = {
                                'school': school,
                                'degree': degree,
                                'year': year
                            }
                            education.append(edu_data)
                            print(f"  ✓ {len(education)}. {edu_data['school']}")
                    except Exception as e:
                        print(f"  Error: {e}")
                        continue
        
        except Exception as e:
            print(f"Error: {e}")
        
        return education
    
    def extract_skills(self):
        """Extract skills section with details"""
        skills = []
        try:
            print("Looking for skills section...")
            
            skills_section = None
            selectors = [
                "//section[contains(@id, 'skills')]",
                "//section[.//div[@id='skills']]",
                "//section[.//h2[contains(text(), 'Skills')]]",
            ]
            
            for selector in selectors:
                try:
                    skills_section = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print("✓ Found section")
                    break
                except TimeoutException:
                    continue
            
            if not skills_section:
                print("⚠ Skills section not found")
                return skills
            
            # Click "Show all skills"
            clicked = click_show_all(self.driver, skills_section)
            
            if clicked:
                items = extract_items_from_detail_page(self.driver)
                print(f"Found {len(items)} skill items")
                
                for idx, item in enumerate(items):
                    try:
                        # Get skill name from first span
                        skill_spans = item.find_elements(By.XPATH, ".//span[@aria-hidden='true']")
                        
                        if not skill_spans:
                            continue
                        
                        skill_name = skill_spans[0].text.strip()
                        
                        if not skill_name:
                            continue
                        
                        # Filter junk
                        skip_if_contains = [
                            'Passed LinkedIn', 
                            'LinkedIn Skill Assessment',
                            ' endorsement',      # "6 endorsements", "1 endorsement"
                        ]
                        skip_if_starts_with = ['Show ', 'See ']
                        
                        # Additional check: skip if it's experience/endorsement count pattern
                        # Pattern: starts with number + "experience" or "endorsement"
                        is_count_pattern = False
                        if skill_name and len(skill_name) > 0:
                            first_word = skill_name.split()[0] if ' ' in skill_name else skill_name
                            if first_word.isdigit() and ('experience' in skill_name.lower() or 'endorsement' in skill_name.lower()):
                                is_count_pattern = True
                        
                        should_skip = (
                            any(pattern in skill_name for pattern in skip_if_contains) or
                            any(skill_name.startswith(pattern) for pattern in skip_if_starts_with) or
                            len(skill_name) > 100 or
                            is_count_pattern
                        )
                        
                        if should_skip:
                            print(f"  [{idx+1}] Skip: {skill_name[:60]}")
                            continue
                        
                        print(f"\n  [{idx+1}] Processing: {skill_name}")
                        
                        details = []
                        
                        # Step 1: Extract details yang langsung tampil (tanpa click)
                        # Details ada di nested <ul> setelah skill name, tapi bukan endorsement count
                        try:
                            # Ambil semua text lines dari item
                            item_text = item.text.strip()
                            if item_text:
                                lines = [l.strip() for l in item_text.split('\n') if l.strip()]
                                
                                # Remove consecutive duplicates
                                unique_lines = []
                                prev = None
                                for line in lines:
                                    if line != prev:
                                        unique_lines.append(line)
                                        prev = line
                                
                                # Line 0 = skill name
                                # Lines after that could be details or endorsement counts
                                # Filter: skip endorsements, experiences count, skill name itself
                                for line in unique_lines[1:]:  # Skip first line (skill name)
                                    # Skip if it's endorsement/experience count
                                    if 'endorsement' in line.lower():
                                        continue
                                    if 'experience' in line.lower() and ' at ' in line:
                                        # "2 experiences at Company" is not a real detail
                                        continue
                                    # Skip Passed LinkedIn badge
                                    if 'Passed LinkedIn' in line or 'LinkedIn Skill Assessment' in line:
                                        continue
                                    # Skip if it's the skill name again
                                    if line == skill_name:
                                        continue
                                    # Skip if too short
                                    if len(line) < 5:
                                        continue
                                    
                                    # This is a valid detail
                                    if line not in details:
                                        details.append(line)
                                        print(f"      • {line[:60]}")
                        except Exception as e:
                            print(f"    Error extracting visible details: {e}")
                        
                        # Step 2: Check if there's "Show all X details" button
                        try:
                            show_details_btn = item.find_element(By.XPATH, 
                                ".//button[contains(., 'Show all') and contains(., 'detail')] | " +
                                ".//a[contains(., 'Show all') and contains(., 'detail')]"
                            )
                            
                            if show_details_btn:
                                print(f"    → Found 'Show all details' button")
                                
                                # Scroll to button
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", show_details_btn)
                                human_delay(0.5, 1)
                                
                                # Click to open modal
                                self.driver.execute_script("arguments[0].click();", show_details_btn)
                                print(f"    → Clicked 'Show all details'")
                                human_delay(2, 3)
                                
                                # Extract details from modal
                                modal_items = self.driver.find_elements(By.XPATH, 
                                    "//div[contains(@role, 'dialog')]//ul/li | " +
                                    "//div[@data-test-modal]//ul/li | " +
                                    "//div[contains(@class, 'artdeco-modal')]//ul/li"
                                )
                                
                                if modal_items:
                                    print(f"    → Found {len(modal_items)} detail items in modal")
                                    # Clear previous details, use modal data instead
                                    details = []
                                    for modal_item in modal_items:
                                        detail_text = modal_item.text.strip()
                                        if detail_text and len(detail_text) > 5:
                                            # Get first line only (title/name)
                                            first_line = detail_text.split('\n')[0].strip()
                                            if first_line and first_line not in details:
                                                details.append(first_line)
                                                print(f"      • {first_line[:60]}")
                                else:
                                    print(f"    → No detail items found in modal")
                                
                                # Close modal - click X button
                                close_selectors = [
                                    "//button[@aria-label='Dismiss']",
                                    "//button[contains(@aria-label, 'Close')]",
                                    "//button[contains(@class, 'artdeco-modal__dismiss')]",
                                    "//button[@data-test-modal-close-btn]",
                                ]
                                
                                for close_selector in close_selectors:
                                    try:
                                        close_btn = self.driver.find_element(By.XPATH, close_selector)
                                        self.driver.execute_script("arguments[0].click();", close_btn)
                                        print(f"    → Closed modal")
                                        human_delay(1, 1.5)
                                        break
                                    except:
                                        continue
                        
                        except NoSuchElementException:
                            # No "Show all details" button - use details from step 1
                            if details:
                                print(f"    → No 'Show all details' button, using visible details")
                            else:
                                print(f"    → No details available")
                        
                        # Add skill with details
                        skill_data = {
                            "name": skill_name,
                            "details": details
                        }
                        skills.append(skill_data)
                        print(f"  ✓ Added: {skill_name} ({len(details)} details)")
                        
                    except Exception as e:
                        print(f"  Error processing skill {idx+1}: {e}")
                        continue
                
                # Click back arrow to return to profile (once at the end)
                click_back_arrow(self.driver)
            
            else:
                # No "Show all skills" button - extract from main page (simplified)
                print("  No 'Show all' button, extracting from main page...")
                items = skills_section.find_elements(By.XPATH, ".//ul/li")
                
                for item in items:
                    try:
                        skill_spans = item.find_elements(By.XPATH, ".//span[@aria-hidden='true']")
                        if skill_spans:
                            skill_name = skill_spans[0].text.strip()
                            if skill_name and len(skill_name) < 100:
                                skill_data = {
                                    "name": skill_name,
                                    "details": []
                                }
                                skills.append(skill_data)
                                print(f"✓ {len(skills)}. {skill_name}")
                    except:
                        continue
        
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        return skills
    
    def extract_projects(self):
        """Extract projects section with show all flow"""
        projects = []
        try:
            print("Looking for projects section...")
            
            proj_section = None
            selectors = [
                "//section[contains(@id, 'projects')]",
                "//section[.//div[@id='projects']]",
                "//section[.//h2[contains(text(), 'Projects')]]",
            ]
            
            for selector in selectors:
                try:
                    proj_section = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print("✓ Found section")
                    break
                except TimeoutException:
                    continue
            
            if not proj_section:
                print("⚠ Projects section not found")
                return projects
            
            # Click "Show all"
            clicked = click_show_all(self.driver, proj_section)
            
            if clicked:
                items = extract_items_from_detail_page(self.driver)
                
                for item in items:
                    try:
                        text = item.text.strip()
                        if not text or len(text) < 10:
                            continue
                        
                        # Remove consecutive duplicates
                        all_lines = [l.strip() for l in text.split('\n') if l.strip()]
                        lines = []
                        prev = None
                        for line in all_lines:
                            if line != prev:
                                lines.append(line)
                                prev = line
                        
                        print(f"  Project item lines: {len(lines)}")
                        for i, line in enumerate(lines[:8]):
                            print(f"    [{i}] {line[:80]}")
                        
                        # Structure after deduplication:
                        # 0: Title
                        # 1: Duration
                        # 2: Associated with Company (skip this)
                        # 3: "Show project" link (skip this)
                        # 4+: Detail/Description
                        
                        if len(lines) >= 2:
                            title = lines[0]
                            duration = lines[1]
                            detail = ""
                            
                            # Find detail: skip "Associated with", "Show project", "Other contributors"
                            for line in lines[2:]:
                                if 'Associated with' in line:
                                    continue
                                if 'Show project' in line:
                                    continue
                                if 'Other contributors' in line:
                                    break  # Stop here, rest is contributor info
                                
                                # This is the detail/description
                                if len(line) > 10:
                                    detail = line
                                    break
                            
                            proj_data = {
                                'title': title,
                                'duration': duration,
                                'detail': detail
                            }
                            projects.append(proj_data)
                            print(f"  ✓ {len(projects)}. {proj_data['title']}")
                    except Exception as e:
                        print(f"  Error parsing project: {e}")
                        continue
                
                click_back_arrow(self.driver)
            else:
                # No show all, extract from main page
                print("  Extracting from main page...")
                items = proj_section.find_elements(By.XPATH, ".//ul/li")
                
                for item in items:
                    try:
                        text = item.text.strip()
                        if not text or len(text) < 10:
                            continue
                        
                        # Remove consecutive duplicates
                        all_lines = [l.strip() for l in text.split('\n') if l.strip()]
                        lines = []
                        prev = None
                        for line in all_lines:
                            if line != prev:
                                lines.append(line)
                                prev = line
                        
                        if len(lines) >= 2:
                            title = lines[0]
                            duration = lines[1]
                            detail = ""
                            
                            for line in lines[2:]:
                                if 'Associated with' in line or 'Show project' in line:
                                    continue
                                if 'Other contributors' in line:
                                    break
                                if len(line) > 10:
                                    detail = line
                                    break
                            
                            proj_data = {
                                'title': title,
                                'duration': duration,
                                'detail': detail
                            }
                            projects.append(proj_data)
                            print(f"  ✓ {len(projects)}. {proj_data['title']}")
                    except Exception as e:
                        print(f"  Error: {e}")
                        continue
        
        except Exception as e:
            print(f"Error: {e}")
        
        return projects
    
    def extract_languages(self):
        """Extract languages section"""
        languages = []
        try:
            print("Looking for languages section...")
            
            lang_section = None
            selectors = [
                "//section[contains(@id, 'languages')]",
                "//section[.//div[@id='languages']]",
                "//section[.//h2[contains(text(), 'Languages')]]",
            ]
            
            for selector in selectors:
                try:
                    lang_section = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print(f"✓ Found section")
                    break
                except TimeoutException:
                    continue
            
            if not lang_section:
                print("⚠ Languages section not found")
                return languages
            
            smooth_scroll(self.driver, lang_section)
            human_delay(1, 2)
            
            items = lang_section.find_elements(By.XPATH, ".//ul/li")
            
            for item in items:
                try:
                    spans = item.find_elements(By.XPATH, ".//span[@aria-hidden='true']")
                    if spans:
                        lang_name = spans[0].text.strip()
                        proficiency = spans[1].text.strip() if len(spans) > 1 else ""
                        
                        if lang_name:
                            if proficiency and proficiency != lang_name:
                                languages.append(f"{lang_name} - {proficiency}")
                            else:
                                languages.append(lang_name)
                            print(f"✓ {len(languages)}. {lang_name}")
                except:
                    continue
        
        except Exception as e:
            print(f"Languages section not found")
        
        return languages
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

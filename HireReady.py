"""
HireReady.py

MV pipline: takes in resume + job posting, uses Claude to pull info out of both,
computes a match score, then asks Clause to give a blunt-personable reponse
grounded in that scoring.

Basic flow:
Extraction (unstructured text -> structures JSON) LLM task.
Scoring (comparing the two inputs) calculated using .py not LLM guessing.
Result LLM call only explains the score 

Run with HireReady.py
Requires: pip install anthropic
          export ANTHROPIC_API_KEY="your-key-here" (or use a .env file, see README)
# (Never hardcode API keys directly in a script you might share or commit.)
Other ideas: Implement with Gemini api key con:has limit on usage, not as strong
"""
import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv
#anyone who clones this repo creates their own .env file (see .env.example)
#instead of running 'export' every terminal session
#.env is gitignored, so NO keys can be committed to version control
load_dotenv()
client = Anthropic()
MODEL ="claude-sonnet-4-6"

#Resume Extraction
def extract_resume(resume_text: str) -> dict:
    system_prompt = """You will extract structures data from resumes. Respond with 
    only a raw JSON object with no markdown code fences, no preample, no explanation text before or after.
    If a fiels is not present, use an empty list or empty string rather than creating information.
Important note: Normalize skill names to common, widely-recognized forms so they can be matched against job postings
    later, and infer underlying technical skills from descriptions, not just explicitly names tools. An example is
    a bullet point describing "a Java application using object-oriented principles" means that the applicant has "object-oriented
    programming" as a skill even though it does not match the exact wording. Do not invent skills with no textual basis, but do 
    surface the skill as described accomplishment demonstrates.

Return JSON in this format:
    {
    "skills": ["list", "of", "tehcnical skills/languages/tools"],
    "years_experience_estimate": <numberm, your best estimate from dates/rols>,
    "titles": ["list of job titles held"],
    "leadership_experience": true/false,
    "degree_status": "e.g. 'in progress - B.S. Software Engineering'"
    } """
    response = client.messages.create(
        model=MODEL,
        max_tokens= 1000,
        temperature = 0, #check this 
        system = system_prompt,
        messages=[{"role": "user", "content": resume_text}],
    )

    #Parse as JSON
    raw_text = response.content[0].text
    return json.loads(raw_text)

#Job posting
#Keeps required skills and nice to have skills seperate, determines hierarchy: REQUIRED then NICE TO HAVES since lower priority.
def extract_job(job_text: str) -> dict:
    #soft skills is lumped in own field and excluded from scoring
    system_prompt ="""You extract structured requirements from job postings. Respond
    with only a raw JSON object with no markdown code fences, no preamble, no explanation text
    before or after.
Important note: "required_skills" must only contain concrete, verifiable technical items: programming languages,
    frameworks, tools, platforms, databases, or specific technical methodologies (e.g. "Python", "SQL", "Git", "Agile", "OOP").
    Do not put soft skills or generic traits in required skills. Things like "communication skills", "problem-solving", "ability to work in
    a team," or "analytical skills" are NOT technical skills - place these in "soft_skills_mentioned" instead.
    They are not resume-matchable and should never affect a technical fit score.
    Normalize skill namees to common, widely-recognized forms so they can be matched against a resume later.
    For example, write "object-oriented programming" (not OOP or "object-oriented design") and "SQL" (not "structured query language")
    
Return JSON in exactly this shape:
    {
    "required_skills": ["list of MUST-HAVE technical skills/tools/languages only"],
    "nice_to_have_skills": ["list of technical skills mentioned as plus"],
    "soft_skills_mentioned": ["list of soft skills and traits - NOT scored"],
    "seniority_level": "e.g. 'intern', 'entry-level', 'senior'",
    "degree_requirement": "e.g, 'pursuing bachelor's in CS or related field'",
    "role-summary": "one sentence describing what the role actually does"
    }"""

    response = client.messages.create(
        model = MODEL,
        max_tokens = 1000, 
        temperature = 0,
        system = system_prompt,
        messages = [{"role": "user", "content": job_text}],
    )
    raw_text = response.content[0].text
    return json.loads(raw_text)

    #Scoring for accuracy
SKILL_ALIASES = {
    "oop": "object-oriented programming",
    "object-oriented design": "object-oriented programming",
    "object oriented programming": "object-oriented programming",
    "sql server": "sql",
    "mysql": "sql",
    "postgres": "sql",
    "postgresql": "sql",
    "git": "version control",
    "github": "version control",
}

def normalize_skill(skill: str) -> str:
    skill = skill.lower().strip()
    return SKILL_ALIASES.get(skill, skill)

def calculate_match(resume_data: dict, job_data: dict) -> dict:
    resume_skills = {normalize_skill(s) for s in resume_data.get("skills", [])}
    required = {normalize_skill(s) for s in job_data.get("required_skills", [])}
    nice_to_have = {normalize_skill(s) for s in job_data.get("nice_to_have_skills", [])}

    def skill_is_matched(skill, skill_set):
        return any(skill in rs or rs in skill for rs in skill_set)

    matched_required = {s for s in required if skill_is_matched(s, resume_skills)}
    missing_required = required - matched_required

    matched_nice = {s for s in nice_to_have if skill_is_matched(s, resume_skills)}

    #hierarchy
    required_score = (len(matched_required) / len(required) * 80) if required else 80
    nice_score = (len(matched_nice) / len(nice_to_have) * 20) if nice_to_have else 20

    total_score = round (required_score + nice_score)

    return {
        "total_score": total_score, 
        "matched_required": sorted (matched_required),
        "missing_required": sorted (missing_required),
        "matched_nice_to_have": sorted(matched_nice),
    }

SKILL_RESOURCES = {
    "sql": {
        # considers courses that vary in name, but similar concepts
        "unc_course": "CS 216 - Database Concepts (Computer Science majors) OR BACS 485 - Database Management Systems (Software Engineering/CIS majors)",
        "unc_prerequisite": "CS 216: CS 160 (minimum grade C). BACS 485: BACS 287 and BACS 300 (minimum grade D-), Senior standing.",
        "youtube": "freeCodeCamp.org - 'SQL Tutorial - Full Database Course for Beginners' - https://www.youtube.com/watch?v=HXV3zeQKqGY",
        "coursera": "'SQL for Data Science' (UC Davis) - https://www.coursera.org/learn/sql-for-data-science",
    },
    "object-oriented programming": {
        "unc_course": "CS 200 - Object-Oriented Analysis, Design, and Programming",
        "unc_prerequisite": "CS 160 (minimum grade C)",
        "youtube": "freeCodeCamp.org - 'Object Oriented Programming in Python - Full Course' - https://youtu.be/Ej_02ICOIgs",
        "coursera": "'Object Oriented Java Programming: Data Structures and Beyond' Specialization (UC San Diego) - https://www.coursera.org/specializations/java-object-oriented",
    },
    "data structures": {
        "unc_course": "CS 301 - Algorithms and Data Structures",
        "unc_prerequisite": "CS 200 (CONCURRENT prerequisite - take together with or before CS 301)",
        "youtube": "freeCodeCamp.org - 'Data Structures Easy to Advanced Course' - https://www.youtube.com/watch?v=RBSGKlAvoiM",
        "coursera": "'Data Structures and Algorithms' Specialization (UC San Diego / HSE) - https://www.coursera.org/specializations/data-structures-algorithms",
    },
    "algorithms": {
        "unc_course": "CS 301 - Algorithms and Data Structures",
        "unc_prerequisite": "CS 200 (CONCURRENT prerequisite - take together with or before CS 301)",
        "youtube": "freeCodeCamp.org - 'Algorithms and Data Structures Tutorial - Full Course for Beginners' - https://www.youtube.com/watch?v=8hly31xKli0",
        "coursera": "'Algorithms, Part I' (Princeton) - https://www.coursera.org/learn/algorithms-part1",
    },
    "power bi": {
        "unc_course": "BACS 287 - Introduction to Business Intelligence and Workflow Design (no-code platforms progressing to Python; explicitly designed for students with no technical background)",
        "unc_prerequisite": "None listed. Restricted to Business Administration, Software Engineering, or Computer Information Systems majors/minors.",
        "youtube": "Luke Barousse - 'Power BI for Data Analytics - Full Course for Beginners' - https://www.youtube.com/watch?v=FwjaHCVNBWA",
        "coursera": "'Data Visualization & Business Intelligence' Specialization (Starweaver) - https://www.coursera.org/specializations/data-visualization-business-intelligence",
    },
    "project management": {
        "unc_course": "BACS 385 - Fundamentals of Project Management (IT project management practices, industry-standard PM software tools)",
        "unc_prerequisite": "None listed. Junior/Senior standing required.",
        "youtube": "Search YouTube for 'project management fundamentals tutorial' - https://www.youtube.com/results?search_query=project+management+fundamentals+tutorial",
        "coursera": "'Google Project Management' Professional Certificate - https://www.coursera.org/professional-certificates/google-project-management",
    },
    "web development": {
        "unc_course": "BACS 200 - Web Design and Development for Small Business (intro) -> BACS 350 - Intermediate Web Development (data-driven, e-commerce sites)",
        "unc_prerequisite": "BACS 200: none listed beyond computer literacy. BACS 350: BACS 200 (minimum grade D-).",
        "youtube": "freeCodeCamp.org - 'Responsive Web Design Course' - https://www.youtube.com/watch?v=srvUrASNj0s",
        "coursera": "'Meta Front-End Developer' Professional Certificate - https://www.coursera.org/professional-certificates/meta-front-end-developer",
    },
    "systems analysis": {
        "unc_course": "BACS 487 - Systems Analysis and Design (investigation, analysis/design techniques and tools)",
        "unc_prerequisite": "BACS 287 and BACS 300 (minimum grade D-). Senior standing required.",
        "youtube": "Search YouTube for 'systems analysis and design tutorial' - https://www.youtube.com/results?search_query=systems+analysis+and+design+tutorial",
        "coursera": "Search Coursera for 'systems analysis and design' - https://www.coursera.org/search?query=systems+analysis+and+design",
    },
    "business analytics": {
        "unc_course": "BACS 301 - Business Analytics Techniques and Applications",
        "unc_prerequisite": "BACS 101 (minimum grade D-). Sophomore standing or higher.",
        "youtube": "Search YouTube for 'business analytics tutorial' - https://www.youtube.com/results?search_query=business+analytics+tutorial",
        "coursera": "'Business Analytics' Specialization (Wharton) - https://www.coursera.org/specializations/business-analytics",
    },
    "computer forensics": {
        # Confirmed via UNC's Business Administration - Computer
        # Information Systems concentration requirements (required elective).
        "unc_course": "BACS 371 - Introduction to Computer Forensics (identification, preservation, extraction, interpretation, and presentation of computer-related evidence)",
        "unc_prerequisite": "None listed.",
        "youtube": "Search YouTube for 'digital forensics fundamentals tutorial' - https://www.youtube.com/results?search_query=digital+forensics+fundamentals+tutorial",
        "coursera": "Search Coursera for 'digital forensics' - https://www.coursera.org/search?query=digital+forensics",
    },
}
import urllib.parse

def _coursera_search(query: str) -> str:
    return f"Search Coursera for '{query}' - https://www.coursera.org/search?query={urllib.parse.quote_plus(query)}"

def _youtube_search(query: str) -> str:
    return f"Search YouTube for '{query} tutorial' - https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query + ' tutorial')}"

CS_CATALOG_SKILLS = {
    "python": ("CS 130 - Fundamentals of Computer Science (Python-based intro course)", "None (or appropriate math placement score)"),
    "linux": ("CS 312 - Systems Programming (Linux/Unix, shell commands, shell scripting)", "CS 200 and CS 216 (minimum grade C)"),
    "computer architecture": ("CS 225 - Computer Organization and Architecture", "CS 160 (minimum grade C)"),
    "cybersecurity": ("CS 232 - Introduction to Cybersecurity or CS 432 - Fundamentals of Cybersecurity (CS majors); BACS 370 - Organizational Cybersecurity and Risk Management or BACS 382 - Information Security (Business/SE/CIS majors)", "CS 232: CS 120 or CS 130. CS 432: CS 200. BACS 370: BACS 101 (minimum grade D-), Sophomore+ standing. BACS 382: none listed. All minimum grade C unless noted."),
    "networking": ("CS 442 - Networking", "CS 301 (minimum grade C)"),
    "operating systems": ("CS 440 - Operating Systems", "CS 301 (minimum grade C)"),
    "machine learning": ("CS 454 - Data Mining and Machine Learning", "MATH 221 and (STAT 150 or STAT 160 or STAT 250 or MATH 350 or STAT 355), minimum grade C"),
    "deep learning": ("CS 456 - Neural Networks and Deep Learning", "CS 120, MATH 221, and MATH 233 (minimum grade C)"),
    "software engineering": ("CS 350 - Software Engineering I", "CS 200 (minimum grade C)"),
    "mobile development": ("CS 330 - Mobile Computing", "CS 200 and CS 216 (minimum grade C)"),
    "human-computer interaction": ("CS 325 - Introduction to Human Computer Interaction (CS majors); BACS 383 - Designing User Experiences (Business/SE majors, no HCI-specific course prerequisite)", "CS 325: CS 130 (minimum grade C). BACS 383: none listed beyond Junior/Senior standing."),
    "data science": ("CS 489 - Project in Data Science", "STAT 411 (minimum grade C)"),
}

for _skill_name, (_course, _prerep) in CS_CATALOG_SKILLS.items():
    SKILL_RESOURCES[_skill_name] = {
        "unc_course": _course,
        "unc_prerequisite": _prerep,
        "youtube": _youtube_search(_skill_name),
        "coursera": _coursera_search(_skill_name),
    }
#word hits
SKILL_ALIASES.update({
    "unix": "linux",
    "shell scripting": "linux",
    "bash": "linux",
    "computer organization": "computer architecture",
    "information security": "cybersecurity",
    "network administration": "networking",
    "ml": "machine learning",
    "neural networks": "deep learning",
    "os": "operating systems",
    "ux/ui design": "human-computer interaction",
    "ui/ux": "human-computer interaction",
    "user experience design": "human-computer interaction",
    "hci": "human-computer interaction",
    "mobile computing": "mobile development",
    "android development": "mobile development",
    "ios development": "mobile development",
    "business intelligence": "power bi",
    "workflow design": "power bi",
    "it project management": "project management",
    "web design": "web development",
    "front-end development": "web development",
    "frontend development": "web development",
    "requirements analysis": "systems analysis",
    "ux design": "human-computer interaction",
    "user experience": "human-computer interaction",
})
RESOURCE_DISCLAIMER = (
    "These are only suggested starting points on your journey to close the skill gap, this " \
    "is not a guarantee of any outcome, an official UNC advising is recommended, confirm with advising " \
    "before enrolling, courses are subjected to change. Some of these recommendations will have pricings visit" \
    "their websites for answers."
)

def generate_resources(missing_required: list, resume_skills: list = None) -> dict:
    """For each missing required skill, first check the curated
    SKILL_RESOURCES table (fast, free, hand-verified). If a skill isn't in
    there, fall back to a LIVE web search via generate_resources_dynamic()
    instead of giving up.
 
    If resume_skills is provided and shows NO programming background at
    all, a "start here first" entry for intro-level courses is inserted at
    the FRONT of the results - see is_coding_beginner() below. Someone with
    zero coding background applying to a software/computing role needs
    CS 120/130 or BACS 101 before SQL, algorithms, or anything else on this
    list means much - treating every missing skill as equally urgent would
    bury the one thing that actually matters most for them.
    """
    resources = {}
 
    if resume_skills is not None and is_coding_beginner(resume_skills):
        resources["programming fundamentals (start here first)"] = {
            "unc_course": "CS 130 - Fundamentals of Computer Science (Python-based intro, recommended for CS/SE-track students) OR BACS 101 - Business Computing (for a general business-computing foundation)",
            "unc_prerequisite": "CS 130: none listed (or appropriate math placement). BACS 101: none listed.",
            "youtube": "freeCodeCamp.org - 'Python for Beginners - Full Course' - https://www.youtube.com/watch?v=eWRfhZUzrAc",
            "coursera": "'Python for Everybody' Specialization (University of Michigan) - https://www.coursera.org/specializations/python",
            "note": "Your resume doesn't show any programming language or coding tool yet. Since this job posting is a software/computing role, this is the single most important gap to close before the specific skills listed below - they all build on having some coding foundation first.",
        }

    for skill in missing_required:
        normalized = normalize_skill(skill)
        if normalized in SKILL_RESOURCES:
            resources[skill] = SKILL_RESOURCES[normalized]
        else:
            resources[skill] = generate_resources_dynamic(skill)
    return resources

#some background exist (tools and languages)
CODING_BACKGROUND_SIGNALS = {
    "python", "java", "c++", "c#", "javascript", "typescript", "html", "css",
    "sql", "r", "matlab", "swift", "kotlin", "php", "ruby", "go", "rust",
    "scala", "bash", "shell scripting", "vba",
}
def is_coding_beginner(resume_skills: list) -> bool:
    """True if the resume's skill list has no overlap at all with any
    recognized programming language or coding tool. Uses the same
    normalized_skill() aliasing as the rest of the matching logic, so
    'Structured Query Language' or 'C Sharp' style variants still count."""
    normalized_resume_skills = {normalize_skill(s) for s in resume_skills}
    return normalized_resume_skills.isdisjoint(CODING_BACKGROUND_SIGNALS)

def generate_resources_dynamic(skill: str) -> dict:
    """Runs THREE SEPARATE, domain-restricted searches for a skill that
    isn't in our curated table - one locked to UNC's real catalog domain,
    one to Coursera, one to YouTube. Restricting each search's allowed
    domain (via the web_search tool's own allowed_domains setting, not just
    an instruction in the prompt) is what makes "trusted courses" an
    enforced guarantee rather than a suggestion the model could ignore.
    """
    unc_result = _search_one_domain(
        skill=skill,
        domain="unco.smartcatalogiq.com",
        instructions="Find a real University of Northern Colorado undergraduate course (course code + name) that teaches this skill, and its prerequisite if the course page lists one.",
        output_field="unc_course",
        not_found_text="No verified UNC course found for this skill - check with an academic advisor.",
    )
    coursera_result = _search_one_domain(
        skill=skill,
        domain="coursera.org",
        instructions="Find a real, currently listed Coursera course or specialization that teaches this skill.",
        output_field="coursera",
        not_found_text="No verified Coursera course found for this skill.",
    )
    youtube_result = _search_one_domain(
        skill=skill,
        domain="youtube.com",
        instructions="Find a real, currently available YouTube tutorial or full course for this skill, preferring well-established educational channels.",
        output_field="youtube",
        not_found_text="No verified YouTube resource found for this skill.",
    )
 
    return {
        "unc_course": unc_result.get("unc_course", "Search error - try again"),
        "unc_prerequisite": unc_result.get("prerequisite", "N/A"),
        "coursera": coursera_result.get("coursera", "Search error - try again"),
        "youtube": youtube_result.get("youtube", "Search error - try again"),
    }
def _search_one_domain(skill: str, domain: str, instructions: str, output_field: str, not_found_text: str) -> dict:
    """Runs one domain-restricted web search for one resource category.
    allowed_domains on the tool itself (not just prompt instructions)
    prevents Claude from citing a result from anywhere
    else, this is enforced by the API"""
    system_prompt = f"""{instructions}
 
Use the web_search tool - you only have access to {domain}, so any result
you cite is guaranteed to be from that trusted source.
 
CRITICAL: only report a resource if a search result actually confirms it
exists right now. If nothing relevant turns up, say so explicitly using
this exact text: "{not_found_text}"
Never invent a course code, title, or URL - every fact must trace back to
an actual search result.
 
Respond with ONLY a raw JSON object, no markdown fences, no preamble.
Return JSON in exactly this shape:
{{
  "{output_field}": "name/title + real URL, or the not-found text above",
  "prerequisite": "prerequisite if stated on the page, else 'N/A' (omit this key entirely if not relevant to this search)"
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        temperature=0,
        system=system_prompt,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 2,  # small cap - one domain, shouldn't need many tries
            "allowed_domains": [domain],
        }],
        messages=[{"role": "user", "content": f"Skill: {skill}"}],
    )
 
    for block in reversed(response.content):
        if block.type == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                return {output_field: not_found_text}
 
    return {output_field: not_found_text}

def generate_verdict(resume_data: dict, job_data: dict, match: dict) -> str:
    system_prompt = """You write a short, blunt-but-personable job-fit verdicts for a job seeker, "Blunk but 
    personable" means: direct, no corporate or language fluff, but still is in a warma and encouraging tone
    - like a mentor being honest with you, not a rejection letter.

    Important Note: Do no invent or restate different match score. Use the exact match_score number you're given. You job is to
    explain WHY that score is what it is, in 3-5 sentences, referencing specific matched and missing skills by name. 
    End with one concrete, actionable suggestion (e.g. what to add to resume or highlight in cover letter)."""

    user_message = f"""
Match score: {match['total_score']}/100
Matched required skills: {match['matched_required']}
Missing required skills: {match['missing_required']}
Matched nice-to-have skills: {match['matched_nice_to_have']}
Role: {job_data.get('role_summary', 'N/A')}
Seniority level: {job_data.get('seniority_level', 'N/A')}
Candidate's current titles: {resume_data.get('titles', [])}
Candidate's leadership experience: {resume_data.get('leadership_experience')}
"""

    response = client.messages.create(
        model = MODEL,
        max_tokens = 500,
        system = system_prompt,
        messages= [{"role": "user", "content": user_message}],
    )
    return response.content[0].text


#Pipeline
def run_pipeline(resume_text: str, job_text: str) -> dict:
    resume_data = extract_resume(resume_text)
    job_data = extract_job(job_text)
    match = calculate_match(resume_data, job_data)
    verdict = generate_verdict(resume_data, job_data, match)

    resume_skills = resume_data.get("skills", [])
    need_resources = bool(match["missing_required"]) or is_coding_beginner(resume_skills)
    resources = generate_resources(match["missing_required"], resume_skills) if need_resources else {}

    return {
        "resume_data": resume_data,
        "job_data": job_data,
        "match": match,
        "verdict": verdict,
        "resources": resources,
        "disclaimer": RESOURCE_DISCLAIMER if resources else None,
    }
RESUME_TEXT = """ """
JOB_TEXT = """ """

if __name__ == "__main__":
    print("Running pipeline...\n")
    result = run_pipeline(RESUME_TEXT, JOB_TEXT)

    print("Extracted resume data:")
    print(json.dumps(result["resume_data"], indent=2))
    print("\nExtracted job data:")
    print(json.dumps(result["job_data"], indent =2))
    print("\nMatch score:")
    print(json.dumps(result["match"], indent =2))

    print("\nVerdict:\n")
    print(result["verdict"])

    if result["resources"]:
        print("\nResources to clode your skill gaps:\n")
        for skill, res in result["resources"].items():
            print(f" - {skill}:")
            for key, value in res.items():
                print(f"    {key}: {value}")
        print(f"\nDisclaimer: {result['disclaimer']}")
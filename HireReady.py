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
Model ="claude-sonnet-4-6"

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
        model=MODEL;
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
        message = [{"role": "user", "content": job_text}],
    )
    raw_text = response.contect[0].text
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
        required = {normalized_skill(s) for s in job_data.get("required_skills", [])}
        nice_to_have = {normalized_skill(s) for s in job_data.get("nice_to_have_skills", [])}

#TODO match skills 
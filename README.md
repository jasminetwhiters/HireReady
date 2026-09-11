# HireReady
 This is an AI integrated full-stack web app to be used by computer students at UNC. 
 **Computer Science, Software Engineering, and Computer Information Systems programs** 
 **Anthropic API key needed**
 
 It compares a resume against a job posting. It then scores the technical fit and recommends real learning resources to "close the gap". These resources include: verfied UNC computer courses, Youtube tutorials, and Coursera courses - for any of the skill gaps found.
 This is a learning project to explore LLM API inegration, prompt engineering, and full-stack Python web development.

 # Problem
 "As a current SWE student applying for internships and part-time jobs has been tough. With the increase of AI applicant tracking systems, some resumes get swept under the rug due to compatibility of the job posting or even employer fit. I would ask AI if my resume was fit and go further in analysis using AI as to why things were not picking up. Thus the idea of streamlining the gap between resume and job postings came about."

 # Goal
 Mission: "Don't check if I am hireReady. Make me hireReady."
 
 Result: Personalized rubric to close gap between applicant to hired.
 

 ## Features
 - Resume analysis
 - Job posting analysis
 - Resume-to-job compatibility score
 - Skill gap identification
 - Personalized learning resources
 - Actionable recommendations

 ## Tech
Python          |Backend
Flask           | Web application
HTML            | Frontend
CSS             | Styling
JavaScript      |Interactivity
LLM Claude API  | AI-powered analysis

## HowTo
1. Upload your resume
2. Paste desired job posting
3. HireReady analyzes both
4. Review your compatibility score
5. Identify missing skills and qualifications
6. Use recommended resources to close the gaps

## Installation

git clone git@github.com:jasminetwhiters/HireReady.git
cd HireReady
pip install -r requirements.txt 

## API Key Setup
HireReady requires an Anthropic API key to perform AI-powered resume and job posting analysis.

1. Create a '.env' file in teh project root
2. Copy the contents of the .'env.example'
3. Replace 'your_api_key_here' with YOUR OWN API KEY

ex. ANTHROPIC_API_KEY=your_api_key_here
## Never commit your .env file or expose your API key publicly.
# User Acceptance Testing (UAT) Questionnaire

**Project:** Second Brain — Graph-Based Multi-Agent System  
**Student:** Wong Yan Hao (TP068819)  
**Target participants:** 5–8 knowledge workers or students  
**Duration:** ~20 minutes per session

---

## Pre-test (1 min)

1. Have you used AI tools for research or note-taking before? (Yes / No)
2. Briefly describe your main use case (student / developer / researcher / other):

---

## Task 1: Document Query (5 min)

**Instructions:** Open the **Quick Query** tab. Ask: *"What are servlets in Java?"*

| # | Statement | Strongly Disagree (1) | Disagree (2) | Neutral (3) | Agree (4) | Strongly Agree (5) |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q1 | The answer was relevant to my question | | | | | |
| Q2 | The sources shown helped me trust the answer | | | | | |
| Q3 | The response time was acceptable | | | | | |

---

## Task 2: Autonomous Research (10 min)

**Instructions:** Open the **Research** tab. Ask: *"What are servlets in Java and how do they compare to modern web frameworks?"*

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q4 | The report was well-structured and easy to read | | | | | |
| Q5 | Citations were present and useful | | | | | |
| Q6 | The "Identified Gaps" section was honest and helpful | | | | | |
| Q7 | The system found information I would not have found manually | | | | | |
| Q8 | I would use this instead of a single ChatGPT/Grok query for research | | | | | |

---

## Task 3: Document Ingestion (3 min)

**Instructions:** Open the **Documents** tab. Ingest a folder of your choice (or the sample `data/documents/` folder).

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q9 | Ingestion was straightforward | | | | | |
| Q10 | The folder picker / path input was clear | | | | | |

---

## Post-test (2 min)

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|:---:|:---:|:---:|:---:|:---:|
| Q11 | Overall, I am satisfied with Second Brain | | | | | |
| Q12 | I would recommend this tool to a colleague | | | | | |

**Open feedback:**
- What did you like most?
- What frustrated you?
- One feature you would add:

---

## Scoring Guide (for report)

- **Acceptance threshold:** Mean score ≥ 3.5 on Q11 (overall satisfaction)
- **Minimum sample:** 5 participants
- Export responses to CSV and use `scripts/generate_uat_charts.py` (optional) for figures
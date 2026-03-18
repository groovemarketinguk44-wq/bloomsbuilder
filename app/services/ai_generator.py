"""
AI Generation Service
---------------------
Generates structured educational resources.
Uses the Anthropic Claude API when AI_API_KEY is set; falls back to
high-quality mock data otherwise so the app is fully usable offline.
"""

import os
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

KEY_STAGE_LABELS = {
    "EYFS": "Early Years Foundation Stage (EYFS)",
    "KS1": "Key Stage 1 (Years 1–2)",
    "KS2": "Key Stage 2 (Years 3–6)",
    "KS3": "Key Stage 3 (Years 7–9)",
    "KS4 (GCSE)": "Key Stage 4 (Years 10–11, GCSE)",
    "A Level": "A Level (Years 12–13)",
    "BTEC": "BTEC",
    "T Level": "T Level",
}


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _base_context(subject: str, key_stage: str, topic: str, additional: str) -> str:
    ks_label = KEY_STAGE_LABELS.get(key_stage, key_stage)
    extra = f"\nAdditional instructions: {additional}" if additional.strip() else ""
    return (
        f"Subject: {subject}\n"
        f"Key Stage: {ks_label}\n"
        f"Topic: {topic}"
        f"{extra}"
    )


def _lesson_prompt(subject: str, key_stage: str, topic: str, additional: str) -> str:
    ctx = _base_context(subject, key_stage, topic, additional)
    return f"""You are an expert UK curriculum educational resource designer.
Create a detailed, classroom-ready lesson plan as a JSON object.
Return ONLY valid JSON with no markdown fences, explanation, or extra text.

{ctx}

Return JSON with exactly this structure:
{{
  "title": "Engaging lesson title",
  "duration": "60 minutes",
  "learning_objectives": [
    "By the end of the lesson pupils will be able to ...",
    "By the end of the lesson pupils will be able to ...",
    "By the end of the lesson pupils will be able to ..."
  ],
  "sections": [
    {{
      "title": "Starter",
      "duration": "10 mins",
      "activity": "Detailed description of the starter activity",
      "teacher_notes": "Practical tip or differentiation note for the teacher"
    }},
    {{
      "title": "Main Activity 1",
      "duration": "15 mins",
      "activity": "Detailed description",
      "teacher_notes": "..."
    }},
    {{
      "title": "Main Activity 2",
      "duration": "15 mins",
      "activity": "Detailed description",
      "teacher_notes": "..."
    }},
    {{
      "title": "Group Task",
      "duration": "10 mins",
      "activity": "Collaborative activity description",
      "teacher_notes": "..."
    }},
    {{
      "title": "Plenary",
      "duration": "10 mins",
      "activity": "Exit activity or summary task",
      "teacher_notes": "..."
    }}
  ],
  "resources_needed": ["Resource 1", "Resource 2", "Resource 3"],
  "differentiation": {{
    "support": "How to support lower-attaining pupils",
    "extension": "Challenge task for higher-attaining pupils"
  }},
  "assessment": "Description of how learning will be assessed in this lesson"
}}"""


def _worksheet_prompt(subject: str, key_stage: str, topic: str, additional: str) -> str:
    ctx = _base_context(subject, key_stage, topic, additional)
    return f"""You are an expert UK curriculum educational resource designer.
Create a classroom-ready pupil worksheet as a JSON object.
Return ONLY valid JSON with no markdown fences, explanation, or extra text.

{ctx}

Return JSON with exactly this structure:
{{
  "title": "Worksheet title",
  "instructions": "Overall instructions for the pupil",
  "sections": [
    {{
      "title": "Section A – Knowledge",
      "questions": [
        {{"number": 1, "question": "Question text here", "marks": 1, "answer_lines": 2}},
        {{"number": 2, "question": "Question text here", "marks": 1, "answer_lines": 2}},
        {{"number": 3, "question": "Question text here", "marks": 2, "answer_lines": 3}}
      ]
    }},
    {{
      "title": "Section B – Understanding",
      "questions": [
        {{"number": 4, "question": "Explain question here", "marks": 3, "answer_lines": 5}},
        {{"number": 5, "question": "Describe question here", "marks": 3, "answer_lines": 5}}
      ]
    }},
    {{
      "title": "Section C – Application",
      "questions": [
        {{"number": 6, "question": "Higher-order question 1", "marks": 4, "answer_lines": 6}},
        {{"number": 7, "question": "Higher-order question 2", "marks": 5, "answer_lines": 8}},
        {{"number": 8, "question": "Extended response question", "marks": 6, "answer_lines": 10}}
      ]
    }}
  ]
}}"""


def _scheme_prompt(subject: str, key_stage: str, topic: str, additional: str) -> str:
    ctx = _base_context(subject, key_stage, topic, additional)
    return f"""You are an expert UK curriculum educational resource designer.
Create a 6-week Scheme of Work as a JSON object.
Return ONLY valid JSON with no markdown fences, explanation, or extra text.

{ctx}

Return JSON with exactly this structure:
{{
  "title": "Scheme of Work title",
  "duration": "6 weeks",
  "overview": "Brief overview of the scheme",
  "weeks": [
    {{
      "week": 1,
      "topic": "Week topic title",
      "objectives": ["Objective 1", "Objective 2"],
      "key_activities": ["Activity 1", "Activity 2"],
      "resources": ["Resource 1", "Resource 2"],
      "assessment": "Formative or summative assessment for this week"
    }},
    {{
      "week": 2,
      "topic": "Week topic title",
      "objectives": ["Objective 1", "Objective 2"],
      "key_activities": ["Activity 1", "Activity 2"],
      "resources": ["Resource 1"],
      "assessment": "Assessment description"
    }},
    {{
      "week": 3,
      "topic": "Week topic title",
      "objectives": ["Objective 1", "Objective 2"],
      "key_activities": ["Activity 1", "Activity 2"],
      "resources": ["Resource 1"],
      "assessment": "Assessment description"
    }},
    {{
      "week": 4,
      "topic": "Week topic title",
      "objectives": ["Objective 1", "Objective 2"],
      "key_activities": ["Activity 1", "Activity 2"],
      "resources": ["Resource 1"],
      "assessment": "Assessment description"
    }},
    {{
      "week": 5,
      "topic": "Week topic title",
      "objectives": ["Objective 1", "Objective 2"],
      "key_activities": ["Activity 1", "Activity 2"],
      "resources": ["Resource 1"],
      "assessment": "Assessment description"
    }},
    {{
      "week": 6,
      "topic": "Review and Assessment",
      "objectives": ["Consolidate learning", "Demonstrate understanding"],
      "key_activities": ["Revision activity", "Summative assessment"],
      "resources": ["Assessment materials"],
      "assessment": "End-of-unit summative assessment"
    }}
  ]
}}"""


def _slides_prompt(subject: str, key_stage: str, topic: str, additional: str) -> str:
    ctx = _base_context(subject, key_stage, topic, additional)
    return f"""You are an expert UK curriculum educational resource designer.
Create a lesson slide outline (10 slides) as a JSON object.
Return ONLY valid JSON with no markdown fences, explanation, or extra text.

{ctx}

Return JSON with exactly this structure:
{{
  "title": "Presentation title",
  "slide_count": 10,
  "slides": [
    {{
      "number": 1,
      "title": "Title slide title",
      "content_type": "title",
      "bullet_points": ["Subtitle or lesson date", "Teacher name"],
      "speaker_notes": "Welcome pupils, introduce the lesson objectives"
    }},
    {{
      "number": 2,
      "title": "Learning Objectives",
      "content_type": "objectives",
      "bullet_points": ["By the end of the lesson you will be able to...", "Objective 2", "Objective 3"],
      "speaker_notes": "Walk through each objective clearly"
    }},
    {{
      "number": 3,
      "title": "Starter Activity",
      "content_type": "activity",
      "bullet_points": ["Starter task instruction", "Time: 5 minutes", "Work individually"],
      "speaker_notes": "Give pupils 5 minutes to complete the starter before reviewing answers"
    }},
    {{
      "number": 4,
      "title": "Key Concept Introduction",
      "content_type": "content",
      "bullet_points": ["Key point 1", "Key point 2", "Key point 3", "Key vocabulary"],
      "speaker_notes": "Explain each key concept clearly, check for understanding"
    }},
    {{
      "number": 5,
      "title": "Worked Example",
      "content_type": "content",
      "bullet_points": ["Step 1", "Step 2", "Step 3", "Check your answer"],
      "speaker_notes": "Model the worked example step by step, think aloud"
    }},
    {{
      "number": 6,
      "title": "Your Turn – Practice",
      "content_type": "activity",
      "bullet_points": ["Task instruction", "Try it yourself", "Time: 8 minutes"],
      "speaker_notes": "Circulate and support as pupils attempt the task"
    }},
    {{
      "number": 7,
      "title": "Deeper Thinking",
      "content_type": "discussion",
      "bullet_points": ["Discussion question", "Consider multiple viewpoints", "Share with your partner"],
      "speaker_notes": "Facilitate discussion, draw out key ideas"
    }},
    {{
      "number": 8,
      "title": "Group Task",
      "content_type": "activity",
      "bullet_points": ["Group task instructions", "Role assignments", "Presentation guidelines"],
      "speaker_notes": "Monitor group progress, prompt with questions"
    }},
    {{
      "number": 9,
      "title": "Review and Consolidation",
      "content_type": "content",
      "bullet_points": ["Key takeaway 1", "Key takeaway 2", "Common misconceptions"],
      "speaker_notes": "Address misconceptions, link back to objectives"
    }},
    {{
      "number": 10,
      "title": "Exit Ticket",
      "content_type": "activity",
      "bullet_points": ["Exit task question", "Write your answer on a sticky note", "Hand in before leaving"],
      "speaker_notes": "Use exit tickets to assess learning and plan next lesson"
    }}
  ]
}}"""


# ---------------------------------------------------------------------------
# Mock data generators (used when AI_API_KEY is not set)
# ---------------------------------------------------------------------------

def _mock_lesson(subject: str, key_stage: str, topic: str, additional: str) -> dict[str, Any]:
    return {
        "title": f"Introduction to {topic}",
        "duration": "60 minutes",
        "learning_objectives": [
            f"Pupils will be able to describe the key concepts of {topic}",
            f"Pupils will be able to explain how {topic} relates to {subject}",
            f"Pupils will be able to apply their knowledge of {topic} in context",
        ],
        "sections": [
            {
                "title": "Starter",
                "duration": "10 mins",
                "activity": f"Quick-fire recall quiz on prior knowledge linked to {topic}. Pupils answer 5 questions on mini-whiteboards to activate prior knowledge.",
                "teacher_notes": "Use mini-whiteboards for instant feedback. Cold-call a range of pupils. Accept all reasonable answers to build confidence.",
            },
            {
                "title": "Main Activity 1 – Input",
                "duration": "15 mins",
                "activity": f"Direct instruction: introduce {topic} using visual aids and real-world examples. Pupils complete guided notes sheet as teacher explains key concepts.",
                "teacher_notes": "Pause every 3–4 minutes to check for understanding. Use 'hands up if you're unsure' to identify misconceptions early.",
            },
            {
                "title": "Main Activity 2 – Practice",
                "duration": "15 mins",
                "activity": f"Structured task: pupils work through exercises requiring them to apply their knowledge of {topic}. Differentiated task cards provided for support and extension.",
                "teacher_notes": "Circulate and use targeted questioning. Extension task: ask pupils to create their own example.",
            },
            {
                "title": "Group Task",
                "duration": "10 mins",
                "activity": f"Collaborative activity: small groups discuss a scenario related to {topic} and prepare a 1-minute verbal explanation to share with the class.",
                "teacher_notes": "Assign roles (facilitator, scribe, spokesperson). Monitor group dynamics. Prompt with questions if groups are stuck.",
            },
            {
                "title": "Plenary",
                "duration": "10 mins",
                "activity": f"Exit ticket: pupils respond to the question 'What is the most important thing you learned about {topic} today, and why?' on a sticky note.",
                "teacher_notes": "Read exit tickets before the next lesson to inform planning. Celebrate strong responses in the following lesson.",
            },
        ],
        "resources_needed": [
            f"Guided notes sheet on {topic}",
            "Mini-whiteboards and pens",
            "Differentiated task cards",
            "Sticky notes for exit tickets",
            f"Visual display / slides on {topic}",
        ],
        "differentiation": {
            "support": "Provide a word bank and sentence starters. Pre-teach key vocabulary. Pair weaker pupils with supportive partners.",
            "extension": f"Ask pupils to produce their own example of {topic} and present it to the group.",
        },
        "assessment": f"Formative: mini-whiteboard checks during starter and main activity. Summative: exit ticket responses used to assess depth of understanding of {topic}.",
    }


def _mock_worksheet(subject: str, key_stage: str, topic: str, additional: str) -> dict[str, Any]:
    return {
        "title": f"{topic} – Worksheet",
        "instructions": f"Complete all sections carefully. Show your working where required. This worksheet covers {topic} in {subject}.",
        "sections": [
            {
                "title": "Section A – Knowledge",
                "questions": [
                    {"number": 1, "question": f"What is {topic}?", "marks": 1, "answer_lines": 2},
                    {"number": 2, "question": f"List three key features of {topic}.", "marks": 3, "answer_lines": 3},
                    {"number": 3, "question": f"Define the term most closely associated with {topic}.", "marks": 2, "answer_lines": 2},
                ],
            },
            {
                "title": "Section B – Understanding",
                "questions": [
                    {"number": 4, "question": f"Explain how {topic} works in practice. Use an example in your answer.", "marks": 3, "answer_lines": 5},
                    {"number": 5, "question": f"What is the difference between the two main aspects of {topic}? Use a table or written comparison.", "marks": 4, "answer_lines": 6},
                ],
            },
            {
                "title": "Section C – Application",
                "questions": [
                    {"number": 6, "question": f"How would you apply your knowledge of {topic} in the context of {subject}?", "marks": 4, "answer_lines": 6},
                    {"number": 7, "question": f"Based on what you know about {topic}, what conclusions can you draw?", "marks": 5, "answer_lines": 8},
                    {"number": 8, "question": f"Extended response: Assess the significance of {topic} in {subject}. Use evidence and examples to support your answer. [6 marks]", "marks": 6, "answer_lines": 12},
                ],
            },
        ],
    }


def _mock_scheme(subject: str, key_stage: str, topic: str, additional: str) -> dict[str, Any]:
    week_topics = [
        f"Introduction to {topic}",
        f"Core Concepts of {topic}",
        f"Applying Knowledge of {topic}",
        f"Deeper Analysis of {topic}",
        f"Evaluating {topic} in Context",
        "Consolidation and Assessment",
    ]

    week_activities = [
        ["Flashcard recall quiz", "Annotated diagram task"],
        ["Concept mapping", "Graphic organiser completion"],
        ["Worked example practice", "Problem-solving worksheet"],
        ["Compare and contrast table", "Source analysis task"],
        ["Structured debate", "Written evaluation paragraph"],
        ["Revision activity", "Summative assessment task"],
    ]

    weeks = []
    for i in range(6):
        weeks.append({
            "week": i + 1,
            "topic": week_topics[i],
            "objectives": [
                f"Pupils will understand the key ideas in {week_topics[i]}",
                f"Pupils will be able to link this to broader {subject} concepts",
            ],
            "key_activities": week_activities[i],
            "resources": [
                f"Week {i+1} pupil workbook pages",
                "Teacher presentation slides",
                "Assessment materials" if i == 5 else "Task card set",
            ],
            "assessment": (
                "Summative end-of-unit test and self-assessment review" if i == 5
                else "Formative: targeted questioning and mini-whiteboard activity"
            ),
        })

    return {
        "title": f"{topic} – Scheme of Work ({key_stage})",
        "duration": "6 weeks",
        "overview": f"This scheme of work introduces pupils to {topic} in {subject}, progressively building knowledge and skills across 6 weeks.",
        "weeks": weeks,
    }


def _mock_slides(subject: str, key_stage: str, topic: str, additional: str) -> dict[str, Any]:
    return {
        "title": f"{topic} – {subject} Lesson",
        "slide_count": 10,
        "slides": [
            {
                "number": 1,
                "title": f"{topic}",
                "content_type": "title",
                "bullet_points": [subject, key_stage],
                "speaker_notes": f"Welcome pupils. Today we are learning about {topic}. Ask pupils what they already know.",
            },
            {
                "number": 2,
                "title": "Learning Objectives",
                "content_type": "objectives",
                "bullet_points": [
                    f"I can describe the key concepts of {topic}",
                    f"I can explain how {topic} applies to {subject}",
                    f"I can use examples of {topic} in real contexts",
                ],
                "speaker_notes": "Read objectives together. Ask: which do you think will be most challenging and why?",
            },
            {
                "number": 3,
                "title": "Starter – What Do You Know?",
                "content_type": "activity",
                "bullet_points": [
                    f"Write down everything you already know about {topic}",
                    "You have 3 minutes",
                    "Work in silence",
                ],
                "speaker_notes": "Cold-call pupils for answers. Build a class mind-map on the board. Praise all contributions.",
            },
            {
                "number": 4,
                "title": f"What is {topic}?",
                "content_type": "content",
                "bullet_points": [
                    f"Key definition: {topic} refers to…",
                    "Main components / features",
                    "Why it matters in " + subject,
                    "Key vocabulary to know",
                ],
                "speaker_notes": "Explain each bullet clearly. Ask comprehension questions. Use the visual on the next slide to support understanding.",
            },
            {
                "number": 5,
                "title": "Key Concepts Explained",
                "content_type": "content",
                "bullet_points": [
                    "Concept 1 – explanation",
                    "Concept 2 – explanation",
                    "Concept 3 – real-world example",
                    "Common misconception to avoid",
                ],
                "speaker_notes": "Pause after each concept. Use 'Think-Pair-Share' to check understanding before moving on.",
            },
            {
                "number": 6,
                "title": "Worked Example",
                "content_type": "content",
                "bullet_points": [
                    "Step 1: Read the question carefully",
                    "Step 2: Identify key information",
                    "Step 3: Apply your knowledge",
                    "Step 4: Check your answer",
                ],
                "speaker_notes": "Model thinking aloud. Demonstrate the process fully before asking pupils to attempt independently.",
            },
            {
                "number": 7,
                "title": "Your Turn – Practice Task",
                "content_type": "activity",
                "bullet_points": [
                    "Complete the practice task",
                    "Time: 8 minutes",
                    "Work independently first, then check with a partner",
                    "Extension: attempt the challenge box",
                ],
                "speaker_notes": "Circulate and support. Use targeted questions rather than giving answers. Note common errors to address in review.",
            },
            {
                "number": 8,
                "title": "Discussion – Think Deeper",
                "content_type": "discussion",
                "bullet_points": [
                    f"Discussion question: To what extent does {topic} affect {subject}?",
                    "Consider evidence for and against",
                    "Be prepared to justify your view",
                ],
                "speaker_notes": "Give 2 minutes for paired discussion. Take feedback from 3–4 pairs. Challenge pupils to use subject-specific vocabulary.",
            },
            {
                "number": 9,
                "title": "Key Takeaways",
                "content_type": "content",
                "bullet_points": [
                    f"1. {topic} is important because…",
                    "2. The key concepts to remember are…",
                    "3. A common mistake to avoid is…",
                    "4. This links to…",
                ],
                "speaker_notes": "Revisit the learning objectives. Ask pupils to self-assess their confidence with a thumbs up/middle/down.",
            },
            {
                "number": 10,
                "title": "Exit Ticket",
                "content_type": "activity",
                "bullet_points": [
                    f"In one sentence, describe what you have learned today.",
                    "Rate your confidence: 1 (not sure) – 5 (very confident)",
                    "Write one question you still have.",
                    "Hand to teacher as you leave.",
                ],
                "speaker_notes": "Collect exit tickets. Review before the next lesson to address misconceptions and plan support.",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Real AI API call
# ---------------------------------------------------------------------------

async def _call_ai_api(prompt: str) -> dict[str, Any]:
    """Call OpenAI API and parse JSON response."""
    from openai import AsyncOpenAI  # imported here so missing package doesn't break mock mode

    client = AsyncOpenAI(api_key=AI_API_KEY)
    response = await client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert UK curriculum educational resource designer. "
                    "Always return valid JSON only, with no markdown fences, no explanation, "
                    "and no text outside the JSON object."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    text = response.choices[0].message.content.strip()
    # Strip accidental markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public generator functions
# ---------------------------------------------------------------------------

async def generate_lesson(
    subject: str, key_stage: str, topic: str, additional_instructions: str = ""
) -> dict[str, Any]:
    if AI_API_KEY:
        try:
            prompt = _lesson_prompt(subject, key_stage, topic, additional_instructions)
            return await _call_ai_api(prompt)
        except Exception as exc:
            logger.warning("AI API call failed, using mock data: %s", exc)
    return _mock_lesson(subject, key_stage, topic, additional_instructions)


async def generate_worksheet(
    subject: str, key_stage: str, topic: str, additional_instructions: str = ""
) -> dict[str, Any]:
    if AI_API_KEY:
        try:
            prompt = _worksheet_prompt(subject, key_stage, topic, additional_instructions)
            return await _call_ai_api(prompt)
        except Exception as exc:
            logger.warning("AI API call failed, using mock data: %s", exc)
    return _mock_worksheet(subject, key_stage, topic, additional_instructions)


async def generate_scheme(
    subject: str, key_stage: str, topic: str, additional_instructions: str = ""
) -> dict[str, Any]:
    if AI_API_KEY:
        try:
            prompt = _scheme_prompt(subject, key_stage, topic, additional_instructions)
            return await _call_ai_api(prompt)
        except Exception as exc:
            logger.warning("AI API call failed, using mock data: %s", exc)
    return _mock_scheme(subject, key_stage, topic, additional_instructions)


async def generate_slides(
    subject: str, key_stage: str, topic: str, additional_instructions: str = ""
) -> dict[str, Any]:
    if AI_API_KEY:
        try:
            prompt = _slides_prompt(subject, key_stage, topic, additional_instructions)
            return await _call_ai_api(prompt)
        except Exception as exc:
            logger.warning("AI API call failed, using mock data: %s", exc)
    return _mock_slides(subject, key_stage, topic, additional_instructions)


# Dispatch map for router convenience
GENERATORS = {
    "lesson": generate_lesson,
    "worksheet": generate_worksheet,
    "scheme": generate_scheme,
    "slides": generate_slides,
}

#This file connects to the Groq AI api
#it sends user data to AI and gets back smart study suggestions

#HOW IT WORKS:
# We built a prompt (a message to AI) with user's data
#We  send it to groq API
#Groq returns a smart study plan as text
#We display that text in the app


from groq import Groq


def configure_ai(api_key):
    """
    Set up the Groq API with your API key.
    Call this once before using any AI features.

    """
    global client
    client = Groq(api_key=api_key)


def get_ai_study_plan(subjects, hours_per_day, num_days, exam_dates=None, student_type="College", routine_info=None):
    """
    Ask Groq AI to create a personalized study plan.

    Args:
        subjects:list of subject names
        hours_per_day:float
        num_days:int
        exam_dates:dict {subject:days_until_exam} or None
        student_tye: "School","College" or "Self-Study

    Returns:
         String with AI-generated study plan
    """

    # Build a descriptive prompt for the AI

    prompt = _build_prompt(subjects, hours_per_day, num_days, exam_dates, student_type, routine_info)

    try:
        #creates model

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5000
        )

        return response.choices[0].message.content

    except Exception as e:
        #If something goes wrong, return a helpful error message
        return f"❌ AI Error: {str(e)}\n\nMake sure your API key is correct."


def get_ai_priority_advice(subjects, exam_dates):
    """
    Ask AI to give priority advice for subjects with upcoming exams.

    This is the AGENTIC part -  AI makes decisions for the student.

    Returns:
    advice: string with AI suggestions
    """

    if not exam_dates:
        return "No exam dates provided. Add exam dates to get priority advice."

    #Build a short focused prompt
    exam_info = "\n".join([
        f"-{subject}:exam in {days} days"
        for subject, days in exam_dates.items()
    ])

    prompt = f"""
    You are an intelligent AI study advisor helping students prepare for exams.

You are an AI study advisor helping students prepare for exams.

Upcoming exams:
{exam_info}

Tasks:

Identify the MOST important subject to study today.
Briefly explain why it is the top priority.
Give a simple 3-step study plan for today.
Add one short motivational tip.

Rules:

Keep the response short, friendly, and encouraging.
Prioritize subjects with nearer exam dates.
Give practical and simple advice.
Use bullet points clearly.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Could not get AI advice: {str(e)}"


# ──────────────────────────────────────────────
# Private helper function
# ──────────────────────────────────────────────

def _build_prompt(subjects, hours_per_day, num_days,
                  exam_dates, student_type, routine_info=None):

    subjects_str = ", ".join(subjects)

    # Exam info
    exam_info = ""
    if exam_dates:
        exam_lines = [
            f" - {sub}: exam in {days} days"
            for sub, days in exam_dates.items()
        ]
        exam_info = "Upcoming exams:\n" + "\n".join(exam_lines)

    # Routine info
    routine_info_str = ""
    if routine_info:
        wake  = routine_info.get('wake_time',  'Not specified')
        sleep = routine_info.get('sleep_time', 'Not specified')
        free  = routine_info.get('free_hours', hours_per_day)

        # Build from USER's input — not hardcoded
        coaching_slots = routine_info.get('coaching_slots', [])

        if coaching_slots:
            coaching_lines = []
            for slot in coaching_slots:
                start      = slot.get('start', '')
                end        = slot.get('end',   '')
                start_ampm = _convert_to_ampm(start)
                end_ampm   = _convert_to_ampm(end)
                coaching_lines.append(
                    f"  - {start_ampm} to {end_ampm} → BLOCKED"
                )
            coaching_str = "\n".join(coaching_lines)
        else:
            coaching_str = "  - No coaching classes"

        routine_info_str = f"""
Student's Daily Routine:
- Wake-up time : {wake}
- Sleep time   : {sleep}
- Free hours   : {free} hrs/day

Coaching/Blocked Hours (STRICTLY DO NOT schedule study here):
{coaching_str}

STRICT RULES:
1. Start first session 30 mins after wake-up
2. NEVER schedule study during blocked hours
3. Show EXACT timings with AM/PM for every session
   Example: 6:30 AM - 8:00 AM: Math - New Topic
4. Include 30 min lunch break around 1:00 PM
5. ⛔ If a session would overlap with blocked time → move it AFTER blocked time
6. ⛔ NEVER schedule ANY session during blocked hours
7. Total study time must be equal {hours_per_day} hours
8. Schedule study sessions BEFORE and AFTER coaching blocks
9. ⛔ Give 45 mins rest/break after coaching ends before starting next study session
"""

    prompt = f"""
You are an expert AI study planner helping a {student_type} student.

Student Details:
- Subjects      : {subjects_str}
- Study hrs/day : {hours_per_day}
- Plan duration : {num_days} days
{exam_info}
{routine_info_str}

Create a COMPLETE {num_days}-day study timetable.
Show ALL {num_days} days without stopping.

After timetable add:
1. Subject Priorities
2. Revision Strategy
3. 2 Productivity Tips
4. One motivational message
"""
    return prompt


def _convert_to_ampm(time_str):
    """
    Convert 24-hour to 12-hour AM/PM format.
    Handles edge cases properly.
    """
    try:
        time_str = time_str.strip()

        # Already has AM/PM — return as is
        if "AM" in time_str.upper() or "PM" in time_str.upper():
            return time_str

        h, m = map(int, time_str.split(":"))

        if h == 0:
            return f"12:{m:02d} AM"
        elif h < 12:
            return f"{h}:{m:02d} AM"
        elif h == 12:
            return f"12:{m:02d} PM"
        else:
            return f"{h-12}:{m:02d} PM"

    except Exception:
        return time_str
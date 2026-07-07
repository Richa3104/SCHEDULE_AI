# utils.py
# Utility / helper functions used across the project.
# Think of this as a toolbox — small reusable tools.

def sort_subjects_by_priority(subjects, exam_dates=None):
    """
    Sort subjects so that the most urgent ones come first.
    If no exam dates are given, keep original order.

    Args:
        subjects: list of subject names
        exam_dates:dict {subject: days_until_exam} or None

    Returns:
        sorted list of subject names
    """

    if not exam_dates:
        return subjects # no sorting needed

    def urgency_key(subject):
        #lower days =  more urgent = sort first
        #Subjects without a date get a high number (low priority)
        return exam_dates.get(subject, 9999)

    return sorted(subjects, key = urgency_key)


def format_timetable_text(timetable):
    """
    Convert the timetable (list of dicts) into a readable text string.
    Useful for printing to terminal or displaying in Streamlit.
    """
    lines=[]

    for day_plan in timetable:
        lines.append(f"\n🗓️ Day {day_plan['day']}")
        lines.append("-"*35)

        for session in day_plan["sessions"]:
            line=(
                f" • {session['subject']:<20}"
                f"  {session['hours']} hr(s)"
                f"  [{session['activity']}]"
            )
            lines.append(line)

        lines.append(f" Total: {day_plan['total_hrs']}")
    return "\n".join(lines)


def validate_inputs(subjects, hours_per_day, num_days):
    """
    Check that user inputs make sense before we generate anything.
    Returns (is_valid: bool, error_message: str)
    """

    if not subjects:
        return False, "Please enter at least one subject."

    if hours_per_day <=0:
        return False, "Study hours per day must be greater than 0."

    if num_days <=0:
        return False, "Number of days must be greater than 0"

    if hours_per_day >16:
        return False, "Study hours per day seems too high (max 16). Please be realistic!"

    if num_days >90:
        return False, "Planning more than 90 days is not supported."


    return True, "" # All good



    
def parse_subjects_input(raw_text) :
    
    if not raw_text.strip():
        return []

    subjects = [s.strip().title() for s in raw_text.split(",")]
    #Remove empty strings in case user typed extra commas
    subjects  = [s for s in subjects if s]
    return subjects


def parse_exam_dates_input(subjects, raw_days_list):
    """
    Build the exam_dates dict from two parallel lists:
      subjects      = ["Math", "Physics"]
      raw_days_list = [3, 7]          (days until exam)
 
    Returns: {"Math": 3, "Physics": 7}
    """

    exam_dates={}

    for subject, days in zip(subjects, raw_days_list):
        try:
            d=int(days)
            if d>0:
                exam_dates[subject]=d
        except (ValueError, TypeError):
            pass# skip invalid entries

    return exam_dates


def get_productivity_score(hours_per_day, num_subjects):
    """
    Give a simple productivity score out of 10 based on
    study hours and number of subjects.
    Just a fun metric for the UI.
    """
    #Ideal 2-3 subjects, 4-6 hrs/day

    score = 10

    if hours_per_day <2:
        score -=3
    elif hours_per_day >10:
        score -=2

    if num_subjects >6:
        score -= 2
    elif num_subjects <1 :
        score-= 5

    return max(1, min(score, 10)) # keep between 1 and 10


# ADD THIS — converts marks to difficulty score
def marks_to_difficulty(marks):
    if marks < 40:
        return 3   # Hard
    elif marks < 70:
        return 2   # Medium
    else:
        return 1   # Easy


# ADD THIS — converts self-study inputs to difficulty score
def selfstudy_to_difficulty(confidence, topics_pending, prior_knowledge):
    score = 0

    confidence_map = {
        "Complete Beginner" : 3,
        "Not Confident"     : 2,
        "Okay"              : 1,
        "Very Confident"    : 0
    }
    score += confidence_map.get(confidence, 1)

    if topics_pending == "8+":
        score += 2
    elif topics_pending == "4-7":
        score += 1

    if prior_knowledge == "No":
        score += 1

    if score >= 4:
        return 3
    elif score >= 2:
        return 2
    else:
        return 1


# ADD THIS — builds difficulty dict for all subjects
def build_difficulty_dict(subjects, student_type,
                          marks_dict=None,
                          confidence_dict=None,
                          topics_dict=None,
                          prior_dict=None):
    difficulty = {}

    for subject in subjects:
        if student_type in ["College Student", "School Student"]:
            marks = marks_dict.get(subject, 60) if marks_dict else 60
            difficulty[subject] = marks_to_difficulty(marks)

        elif "Self-Study" in student_type:
            confidence     = confidence_dict.get(subject, "Okay") if confidence_dict else "Okay"
            topics_pending = topics_dict.get(subject, "4-7") if topics_dict else "4-7"
            prior_knowledge= prior_dict.get(subject, "Yes") if prior_dict else "Yes"
            difficulty[subject] = selfstudy_to_difficulty(
                confidence, topics_pending, prior_knowledge
            )

    return difficulty


#student to tell their time waking and sleeping
def time_str_to_float(time_str):
    try:
        time_str = time_str.strip().upper()
        is_pm = "PM" in time_str
        is_am = "AM" in time_str
        time_str = time_str.replace("AM", "").replace("PM", "").strip()
        h, m = map(int, time_str.split(":"))
        if is_pm and h != 12:
            h += 12
        if is_am and h == 12:
            h = 0
        return h + m / 60.0
    except Exception:
        return None


def calculate_free_study_hours(wake_time_str, sleep_time_str, coaching_slots):
    wake  = time_str_to_float(wake_time_str)
    sleep = time_str_to_float(sleep_time_str)

    if wake is None or sleep is None:
        return None, "Invalid wake/sleep times."

    awake_hours    = sleep - wake if sleep > wake else (24 - wake) + sleep
    coaching_hours = 0.0
    coaching_notes = []

    for slot in coaching_slots:
        start    = time_str_to_float(slot.get("start", ""))
        end      = time_str_to_float(slot.get("end", ""))
        
        duration = (end - start) if (start and end and end > start) else 0
        if duration > 0:
            coaching_hours += duration
            coaching_notes.append(f"{slot['start']}–{slot['end']}")

    free_hours = max(0.0, awake_hours - coaching_hours)
    summary    = f"Awake {awake_hours:.1f} hrs"
    if coaching_notes:
        summary += f" | Coaching slots: {', '.join(coaching_notes)} = {coaching_hours:.1f} hrs blocked"
    summary += f" | Free for study: {free_hours:.1f} hrs"

    return round(free_hours, 1), summary

def build_daily_schedule(sessions, wake_time_str, sleep_time_str, coaching_slots):
    """
    Assigns actual start and end times to each study session,
    working around coaching slots.

    Returns sessions with 'start_time' and 'end_time' added.
    """
    # Build a list of blocked periods from coaching slots
    blocked = []
    for slot in coaching_slots:
        start = time_str_to_float(slot.get("start", ""))
        end   = time_str_to_float(slot.get("end", ""))
        if start is not None and end is not None and end > start:
            blocked.append((start, end))
    blocked.sort()

    # Convert float hours to HH:MM string
    def float_to_time_str(f):
        h = int(f)
        m = int(round((f - h) * 60))
        if m == 60:
            h += 1
            m  = 0
        period = "AM" if h < 12 else "PM"
        h12    = h % 12 or 12
        return f"{h12}:{m:02d} {period}"

    # Start scheduling from wake time
    current = time_str_to_float(wake_time_str)
    if current is None:
        current = 6.0
    current += 0.75 # adding extra time after waking up as no one can start at that point
    
    scheduled = []

    for session in sessions:
        hours_needed = session["hours"]

        # Skip over any coaching block we've hit
        for b_start, b_end in blocked:
            if current >= b_start and current < b_end:
                current = b_end  # jump past the block

        end_time = current + hours_needed

        # If the session runs into a coaching block, push it after
        for b_start, b_end in blocked:
            if current < b_start and end_time > b_start:
                current  = b_end
                end_time = current + hours_needed

        scheduled.append({
            **session,
            "start_time": float_to_time_str(current),
            "end_time"  : float_to_time_str(end_time)
        })

        current = end_time

    return scheduled
    
# ── NEW: chart-ready summaries for a livelier UI ─────────────
def get_subject_hours_summary(timetable):
    """
    Total hours per subejct across the whole plan.
    Returns dict {subject:total_hours} - feeds the bar/pie chart.
    
    """
    totals={}
    for day_plan in timetable:
        for session in day_plan["sessions"]:
            subj=session["subject"]
            totals[subj]=totals.get(subj,0)+session["hours"]
    return {k: round(v,1) for k,v in totals.items()}

def get_daily_hours_series(timetable):
    """
    Returns two parallel lists (days,total_hours) - feeds the day-by-day line/bar chart.
    """
    days= [d["day"] for d in timetable]
    hours=[d["total_hrs"] for d in timetable]
    return days, hours

def days_until_label(days_left):
    """
    Turn a raw day-count into a short urgency label + value used to color/size a progress bar in the UI."""

    if days_left<=1:
        return "Tomorrow!", 0.95
    elif days_left<=3:
        return f"{days_left} days - urgent", 0.8
    elif days_left<=7:
        return f"{days_left} days - soon", 0.5
    else:
        return f"{days_left} days away", 0.2
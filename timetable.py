from utils import sort_subjects_by_priority

def generate_timetable(subjects, hours_per_day, num_days, exam_dates=None,
                       difficulty=None, syllabus_pending=None,
                       personal_priority=None, routine_info=None):
    """
    Generate a rotating study timetable.

    Args:
        subjects          : list of subject names, e.g. ["Math", "Physics"]
        hours_per_day     : float, total study hours available each day
        num_days          : int, how many days to plan for
        exam_dates        : dict, {subject: days_until_exam}, e.g. {"Math": 3}
        difficulty        : dict, {subject: 1-3}  (auto from marks or confidence)
        syllabus_pending  : dict, {subject: 1-3}  (1=Less, 3=More pending)
        personal_priority : dict, {subject: 1-3}  (student's own preference)

    Returns:
        timetable : list of dicts, one per day
    """
    if not subjects:
        return []

    effective_hours = hours_per_day
    routine_note    = None

    if routine_info:
        routine_note = routine_info.get("routine_summary")

    if effective_hours <= 0:
        effective_hours = 0.5

    # Step 1 — sort subjects by urgency (exam closest = highest priority)
    sorted_subjects = sort_subjects_by_priority(subjects, exam_dates)

    # Step 2 — calculate weights using ALL factors now
    subject_weights = _calculate_weights(
        sorted_subjects,
        exam_dates        = exam_dates,
        difficulty        = difficulty,
        syllabus_pending  = syllabus_pending,
        personal_priority = personal_priority
    )

    total_weight = sum(subject_weights.values())

    timetable = []

    for day in range(1, num_days + 1):
        day_plan = {
            "day"      : day,
            "sessions" : [],
            "total_hrs": 0,
            "routine_note":routine_note
        }

        for subject in sorted_subjects:
            # proportional hours based on weight
            weight    = subject_weights[subject]
            allocated = round((weight / total_weight) * effective_hours, 1)

            session = {
                "subject" : subject,
                "hours"   : allocated,
                "activity": _decide_activity(day, subject, exam_dates)
            }
            day_plan["sessions"].append(session)
            day_plan["total_hrs"] += allocated

        # Round total hours to avoid float weirdness
        day_plan["total_hrs"] = round(day_plan["total_hrs"], 1)
        timetable.append(day_plan)

    return timetable


def generate_revision_schedule(subjects, exam_dates):
    """
    Create a special revision plan for subjects with upcoming exams.

    Returns list of revision alerts.
    """

    alerts=[]

    if not exam_dates:
        return alerts

    for subject, days_left in exam_dates.items():
        if subject not in subjects:
            continue

        if days_left <=1:
            alerts.append(f"🚨 {subject}: Exam TOMORROW - full revision day!")
        elif days_left <=3:
            alerts.append(f"⚠️ {subject}: Exam in {days_left} days - heavy revision needed.")
        elif days_left <=7:
            alerts.append(f"📌 {subject}: Exam in {days_left} days - start revision.")

    return alerts


# ──────────────────────────────────────────────
# private helper functions (used only inside this file, hence the _ prefix)
# ──────────────────────────────────────────────

# REPLACE the existing _calculate_weights() with this:
def _calculate_weights(subjects, exam_dates, difficulty=None,
                       current_marks=None, syllabus_pending=None,
                       personal_priority=None):
    weights = {}

    for subject in subjects:
        score = 0

        # Factor 1: Exam Urgency (1-4 points)
        if exam_dates and subject in exam_dates:
            days_left = exam_dates[subject]
            if days_left <= 2:
                score += 4
            elif days_left <= 5:
                score += 3
            elif days_left <= 10:
                score += 2
            else:
                score += 1
        else:
            score += 1

        # Factor 2: Difficulty (1-3 points)
        if difficulty and subject in difficulty:
            score += difficulty[subject]
        else:
            score += 1

        # Factor 3: Current Marks (0-3 points)
        if current_marks and subject in current_marks:
            marks = current_marks[subject]
            if marks < 40:
                score += 3
            elif marks < 60:
                score += 2
            elif marks < 80:
                score += 1

        # Factor 4: Syllabus Pending (1-3 points)
        if syllabus_pending and subject in syllabus_pending:
            score += syllabus_pending[subject]
        else:
            score += 1

        # Factor 5: Personal Priority (1-3 points)
        if personal_priority and subject in personal_priority:
            score += personal_priority[subject]
        else:
            score += 1

        weights[subject] = score ** 2

    return weights

def _decide_activity(day, subject, exam_dates):
    """
    Return the recommended activity for a subject on a given day.
    E.g., new topic, practice, or revision.
    """

    if exam_dates and subject in exam_dates:
        days_left = exam_dates[subject]

        if days_left<=3:
            return "Full Revision"
        elif days_left<=7:
            return "Practice + Revision"

    #Rotate activity based on a day number (simple pattern)

    activities=["New Topic", "Practice Problems", "Notes Review", "Mock Test", "Revision"]
    return activities[day % len(activities)]

    
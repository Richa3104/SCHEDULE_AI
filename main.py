from timetable import generate_timetable, generate_revision_schedule
from utils     import (
    validate_inputs,
    parse_subjects_input,
    format_timetable_text,
    get_productivity_score,
    marks_to_difficulty,        
    selfstudy_to_difficulty, calculate_free_study_hours  
)


def main():
    print("=" * 50)
    print("   📚 AI-Driven Academic Study Planner")
    print("=" * 50)
    print()

    # ── Step 1: Student Type ────────────────────────
    print("Select student type:")
    print("  1. College Student")
    print("  2. School Student")
    print("  3. Self-Study")
    choice = input("Enter 1, 2 or 3: ").strip()

    student_type = "College"
    if choice == "2":
        student_type = "School"
    elif choice == "3":
        student_type = "Self-Study"

    # ── Step 2: Collect Basic Inputs ────────────────
    raw_subjects  = input("\nEnter subjects (comma separated): ")
    hours_per_day = float(input("Study hours per day: "))
    num_days      = int(input("Number of days to plan: "))

    subjects = parse_subjects_input(raw_subjects)

    # ── Step 3: Validate ────────────────────────────
    is_valid, error_msg = validate_inputs(subjects, hours_per_day, num_days)
    if not is_valid:
        print(f"\n❌ Error: {error_msg}")
        return

    # ── Step 4: Exam Dates ──────────────────────────
    print("\nDo you want to add exam dates? (y/n): ", end="")
    add_exams = input().strip().lower()

    exam_dates = {}
    if add_exams == "y":
        for subject in subjects:
            days_str = input(f"  Days until {subject} exam (Enter to skip): ").strip()
            if days_str.isdigit():
                exam_dates[subject] = int(days_str)

    #── Step 5: Daily Routine ───────────────────────
    
    add_routine = input("\nAdd your daily routine? (y/n): ").strip().lower()
    routine_info = None

    if add_routine == "y":
        wake_time  = input("  Wake-up time (e.g. 06:00 AM or 06:00): ").strip()
        sleep_time = input("  Sleep time   (e.g. 10:00 PM or 22:00): ").strip()

        coaching_slots = []
        print("  Add coaching slots (e.g. ' 14:00-16:00'). Blank line to stop.")
        while True:
            slot = input("  Slot: ").strip()
            if not slot:
                break
            import re
            match = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', slot)
            if match:
                coaching_slots.append({
                    
                    "start": match.group(1),
                    "end"  : match.group(2)
                })

        free_h, summary = calculate_free_study_hours(wake_time, sleep_time, coaching_slots)
        if free_h is not None:
            print(f"\n  📊 {summary}")
            routine_info  = {"free_hours": free_h, "routine_summary": summary, "coaching_slots": coaching_slots}

    # ── Step 6: Difficulty ──────────────────────────
    # ↓↓↓ ADD THIS BLOCK HERE — right after exam_dates ↓↓↓

    difficulty = {}

    if student_type in ["College", "School"]:
        print("\nEnter current marks (or press Enter to skip):")
        for subject in subjects:
            marks_str = input(f"  Marks in {subject} (0-100): ").strip()
            if marks_str.isdigit():
                difficulty[subject] = marks_to_difficulty(int(marks_str))

    elif student_type == "Self-Study":
        print("\nRate yourself for each subject:")
        for subject in subjects:
            print(f"\n  {subject}:")

            print("    Confidence: 1=Very Confident  2=Okay  3=Not Confident  4=Complete Beginner")
            conf_map = {
                "1": "Very Confident",
                "2": "Okay",
                "3": "Not Confident",
                "4": "Complete Beginner"
            }
            conf_input = input("    Enter 1-4: ").strip()
            confidence = conf_map.get(conf_input, "Okay")

            print("    Topics Left: 1=Few(1-3)  2=Some(4-7)  3=Many(8+)")
            topics_map = {"1": "1-3", "2": "4-7", "3": "8+"}
            topics_input  = input("    Enter 1-3: ").strip()
            topics_pending = topics_map.get(topics_input, "4-7")

            prior = input("    Studied this before? (y/n): ").strip().lower()
            prior_knowledge = "Yes" if prior == "y" else "No"

            difficulty[subject] = selfstudy_to_difficulty(
                confidence, topics_pending, prior_knowledge
            )

    # ↑↑↑ END of difficulty block ↑↑↑

    # ── Step 6: Generate Timetable ──────────────────
    print("\n⏳ Generating your study timetable...\n")

    timetable = generate_timetable(      # ← UPDATED CALL
        subjects,
        hours_per_day,
        num_days,
        exam_dates = exam_dates,
        difficulty = difficulty    ,
        routine_info=routine_info
    )

    # ── Step 7: Display Results ─────────────────────
    print("=" * 50)
    print("   📅 YOUR STUDY TIMETABLE")
    print("=" * 50)
    print(format_timetable_text(timetable))

    # ── Step 8: Revision Alerts ─────────────────────
    if exam_dates:
        alerts = generate_revision_schedule(subjects, exam_dates)
        if alerts:
            print("\n" + "=" * 50)
            print("   ⚠️  REVISION ALERTS")
            print("=" * 50)
            for alert in alerts:
                print(alert)

    # ── Step 9: Productivity Score ──────────────────
    score = get_productivity_score(hours_per_day, len(subjects))
    print(f"\n🎯 Productivity Score: {score}/10")
    print("\n✅ Done! Run 'streamlit run app.py' for web version.")


if __name__ == "__main__":
    main()
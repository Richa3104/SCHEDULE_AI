# app.py
# ─────────────────────────────────────────────────────────────
# Streamlit Web App — the full UI version of the Study Planner.
#
# HOW TO RUN:
#   streamlit run app.py
# ─────────────────────────────────────────────────────────────

import re
import streamlit as st
import plotly.graph_objects as go

from auth import load_config, create_authenticator, register_user
from timetable import generate_timetable, generate_revision_schedule
from utils import (
    validate_inputs,
    parse_subjects_input,
    format_timetable_text,
    get_productivity_score,
    build_difficulty_dict,
    build_daily_schedule,
    get_subject_hours_summary,
    get_daily_hours_series,
    days_until_label,
    time_str_to_float,
)
from ai_planner import configure_ai, get_ai_study_plan, get_ai_priority_advice


# ── Page Configuration ───────────────────────────────────────
st.set_page_config(
    page_title="AI Study Planner",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Login System ─────────────────────────────────────────────
# ── Login System ─────────────────────────────────────────────
config = load_config()
authenticator = create_authenticator(config)

# Read current authentication state
auth_status = st.session_state.get("authentication_status")

# Show login/signup ONLY if the user is not logged in
if auth_status is not True:

    page = st.radio(
        "",
        ["🔑 Login", "📝 Sign Up"],
        horizontal=True
    )

    # ---------------- LOGIN ----------------
    if page == "🔑 Login":

        authenticator.login(location="main", key="Login")

        auth_status = st.session_state.get("authentication_status")

        if auth_status is False:
            st.error("❌ Incorrect username or password")

        elif auth_status is None:
            st.info("👋 Please log in to continue.")

    # ---------------- SIGN UP ----------------
    else:

        st.subheader("Create Account")

        with st.form("register_form"):

            reg_name = st.text_input("Full Name")
            reg_username = st.text_input("Username")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Password", type="password")
            reg_confirm = st.text_input("Confirm Password", type="password")

            reg_btn = st.form_submit_button("Create Account")

            if reg_btn:

                if not reg_name or not reg_username or not reg_email or not reg_password:
                    st.error("⚠️ Please fill all fields")

                elif reg_password != reg_confirm:
                    st.error("❌ Passwords do not match")

                elif len(reg_password) < 6:
                    st.error("⚠️ Password must be at least 6 characters")

                else:
                    success, message = register_user(
                        config,
                        reg_name,
                        reg_username,
                        reg_email,
                        reg_password
                    )

                    if success:
                        st.success("✅ Account created successfully!")
                        st.info("Now switch to the 🔑 Login option and sign in.")
                    else:
                        st.error(f"❌ {message}")

    # Don't show the main app until login succeeds
    st.stop()

# ── Logged in ─────────────────────────────────────────────
username = st.session_state.get("username")
name = st.session_state.get("name")

# ── Custom CSS (modern, "alive" look) ────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    html, body, [class*="css"]  { font-family: 'Poppins', sans-serif; }

    .stApp {
        background: linear-gradient(180deg, #F7FAFF 0%, #EEF5FF 100%);
    }

    .main-header {
        font-size: 2.6rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6C5CE7, #00B894);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.1rem;
    }
    .sub-header {
        text-align: center;
        color: #8395A7;
        font-size: 1.05rem;
        margin-bottom: 1.8rem;
    }

    .metric-card {
        background: white;
        border-radius: 18px;
        padding: 1.2rem;
        border: none;
        box-shadow: 0 8px 25px rgba(0,0,0,.08);
        transition: all .2s ease;
    }

    .metric-card:hover{
        transform: translateY(-4px);
        box-shadow:0 12px 30px rgba(0,0,0,.12);
    }
    .metric-value { font-size: 1.9rem; font-weight: 700; color: #2D3436; }
    .metric-label { font-size: 0.85rem; color: #8395A7; margin-top: 2px; }

    .day-card {
        background: white;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        border-left: 5px solid #4F8EF7;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
    }

    .tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        color: white;
        margin-left: 6px;
    }
    .tag-new       { background: #00B894; }
    .tag-practice  { background: #0984E3; }
    .tag-revision  { background: #E17055; }
    .tag-mock      { background: #6C5CE7; }
    .tag-notes     { background: #FDCB6E; color: #2D3436; }

    .alert-box {
        background-color: #FFF3CD;
        border-left: 5px solid #FFC107;
        padding: 0.8rem 1rem;
        border-radius: 10px;
        margin: 0.3rem 0;
    }

    .urgent-box {
        background-color: #FFE3E3;
        border-left: 5px solid #E74C3C;
        padding: 0.8rem 1rem;
        border-radius: 10px;
        margin: 0.3rem 0;
    }

    div[data-testid="stExpander"] {
        border-radius: 14px !important;
        border: 1px solid #EEE !important;
    }

    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(108,92,231,0.25); }
    
    .stApp::before{
        content:"";
        position:fixed;
        width:700px;
        height:700px;
        top:-300px;
        right:-250px;
        background:radial-gradient(circle,#4F8EF720 0%,transparent 70%);
        z-index:-1;
    }

    .stApp::after{
        content:"";
        position:fixed;
        width:600px;
        height:600px;
        bottom:-250px;
        left:-250px;
        background:radial-gradient(circle,#34D39920 0%,transparent 70%);
        z-index:-1;
    }
</style>
""", unsafe_allow_html=True)


def activity_tag(activity: str) -> str:
    mapping = {
        "New Topic": "tag-new",
        "Practice Problems": "tag-practice",
        "Notes Review": "tag-notes",
        "Mock Test": "tag-mock",
        "Revision": "tag-revision",
        "Full Revision": "tag-revision",
        "Practice + Revision": "tag-practice",
    }
    css_class = mapping.get(activity, "tag-new")
    return f'<span class="tag {css_class}">{activity}</span>'

def _guess_activity_class(text: str) -> str:
    """Same idea as activity_tag's mapping, but fuzzy-matches free-form
    AI-generated text (e.g. 'Oops - Revision', 'Lunch Break')."""
    t = text.lower()
    if "revision" in t or "revise" in t:
        return "tag-revision"
    if "practice" in t:
        return "tag-practice"
    if "mock" in t or "test" in t:
        return "tag-mock"
    if "notes" in t or "review" in t:
        return "tag-notes"
    if "lunch" in t or "break" in t:
        return "tag-notes"
    return "tag-new"


_DAY_HEADER_RE = re.compile(r'^[#*\s]*Day\s+(\d+)', re.IGNORECASE)
_TIME_LINE_RE = re.compile(r'(\d{1,2}:\d{2}\s*[AP]M\s*[-–—]\s*\d{1,2}:\d{2}\s*[AP]M)\s*:?\s*(.+)')
_SECTION_HEADERS = r'Subject Priorities|Revision Strategy|Productivity Tips|Motivational'
_SPLIT_RE = re.compile(rf'\n(?=[#*\s]{{0,6}}(?:Day\s+\d+|{_SECTION_HEADERS}))', re.IGNORECASE)


def render_ai_study_plan(plan_text: str):
    """
    Turns the AI's raw markdown study plan into the same day-card /
    colored-tag style used for the manually generated timetable,
    instead of dumping plain bulleted text.
    """
    chunks = [c.strip() for c in _SPLIT_RE.split(plan_text) if c.strip()]

    for chunk in chunks:
        lines = chunk.split("\n")
        header_match = _DAY_HEADER_RE.match(lines[0].strip())

        if header_match:
            day_num = header_match.group(1)
            with st.expander(f"🤖 Day {day_num}", expanded=(day_num == "1")):
                for line in lines[1:]:
                    line = line.strip().lstrip("-*•#").strip()
                    if not line:
                        continue
                    tmatch = _TIME_LINE_RE.match(line)
                    if tmatch:
                        time_range, rest = tmatch.groups()
                        parts = re.split(r'\s[-–—]\s', rest, maxsplit=1)
                        subject, activity = parts if len(parts) == 2 else (rest, "Break")
                        css_class = _guess_activity_class(activity)
                        st.markdown(
                            f'<div class="day-card">'
                            f'<code>{time_range}</code> &nbsp; <b>{subject.strip()}</b>'
                            f'<span class="tag {css_class}">{activity.strip()}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(f"- {line}")
        else:
            header_line = lines[0].strip().lstrip("#").strip()
            st.markdown(
                f'<div class="day-card" style="border-left-color:#00B894;">'
                f'<b>{header_line}</b></div>',
                unsafe_allow_html=True
            )
            for line in lines[1:]:
                clean = line.strip().lstrip("-*•").strip()
                if clean:
                    st.markdown(f"- {clean}")

# for graphs and pie chart

def extract_ai_plan_stats(plan_text: str):
    """Parses the AI's time-slot lines to build subject/day hour totals,
    so the AI plan can get the same pie/bar charts as the manual one."""
    chunks = [c.strip() for c in _SPLIT_RE.split(plan_text) if c.strip()]
    subject_hours, day_hours = {}, {}

    for chunk in chunks:
        lines = chunk.split("\n")
        header_match = _DAY_HEADER_RE.match(lines[0].strip())
        if not header_match:
            continue
        day_num = header_match.group(1)

        for line in lines[1:]:
            line = line.strip().lstrip("-*•").strip()
            tmatch = _TIME_LINE_RE.match(line)
            if not tmatch:
                continue
            time_range, rest = tmatch.groups()
            try:
                start_str, end_str = [p.strip() for p in time_range.split("-")]
                start, end = time_str_to_float(start_str), time_str_to_float(end_str)
                duration = end - start if end > start else (24 - start) + end
            except Exception:
                continue

            subject = re.split(r'\s[-–—]\s', rest, maxsplit=1)[0].strip()
            if "lunch" in subject.lower() or "break" in subject.lower():
                continue

            subject_hours[subject] = subject_hours.get(subject, 0) + duration
            day_hours[day_num] = day_hours.get(day_num, 0) + duration

    return ({k: round(v, 1) for k, v in subject_hours.items()},
            {k: round(v, 1) for k, v in day_hours.items()})
# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.success(f"👋 Welcome, {name}")
    authenticator.logout("🚪 Logout", "sidebar")
    st.divider()

    st.header("⚙️ Settings")

    student_type = st.selectbox(
        "I am a...",
        ["College Student", "School Student", "Self-Study / Exam Prep"]
    )

    st.divider()
    st.subheader("🤖 AI Settings (Optional)")

    use_ai = st.toggle("Enable AI", value=False)

    try:
        ai_api_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        ai_api_key = ""

    if use_ai:
        if ai_api_key:
            st.success("✅ AI Enabled (using saved key)")
        else:
            ai_api_key = st.text_input(
                "Groq API Key",
                type="password",
                help="Get a free key at console.groq.com. "
                     "For a permanent setup, add GROQ_API_KEY to .streamlit/secrets.toml instead."
            )
            if ai_api_key:
                st.success("✅ AI Enabled!")
            else:
                st.warning("⚠️ Enter an API key to use AI features.")

        st.info("💡 **Tip:** Generate the base timetable first, then explore AI insights.")

if use_ai and ai_api_key:
    configure_ai(ai_api_key)

# ── App Header ───────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;">
    <span style="font-size:2.5rem;">📚</span>
    <span class="main-header"> AI-Driven Academic Study Planner</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="sub-header">Smart, adaptive timetables for School · College · Self-Study</p>', unsafe_allow_html=True)

st.divider()

# ── Two Column Layout ────────────────────────────────────────
col_left, col_right = st.columns([1, 1.5], gap="large")

# ── LEFT COLUMN ──────────────────────────────────────────────
with col_left:
    st.subheader("📝 Your Study Details")

    raw_subjects = st.text_input(
        "📖 Subjects",
        placeholder="e.g. Math, Physics, Chemistry",
        help="Separate subjects with commas"
    )

    exam_dates = {}
    marks_dict = {}
    confidence_dict = {}
    topics_dict = {}
    prior_dict = {}
    free_h = 4.0
    routine_info = None

    wake_time = "06:00 AM"
    sleep_time = "10:00 PM"
    coaching_slots = []

    c1, c2 = st.columns(2)
    with c1:
        hours_per_day = st.number_input(
            "⏱️ Hours/Day", min_value=0.5, max_value=16.0, value=4.0, step=0.5
        )
    with c2:
        num_days = st.number_input("🗓️ Days", min_value=1, max_value=90, value=7)

    subjects = parse_subjects_input(raw_subjects)

    use_routine = False

    if subjects:
        st.divider()
        st.subheader("🕐 Daily Routine (Optional)")
        st.caption("Coaching hours are blocked out — only free time is used for study.")

        use_routine = st.toggle("Add my daily routine", value=False)
        coaching_slots = []

        if use_routine:
            r1, r2 = st.columns(2)
            wake_time = r1.text_input("🌅 Wake-up time (HH:MM AM/PM)", value="06:00 AM")
            sleep_time = r2.text_input("🌙 Sleep time (HH:MM AM/PM)", value="10:00 PM")
            st.caption("⏰ 12-hour (06:00 AM) or 24-hour (06:00) format both work")

            num_slots = st.number_input("How many coaching slots?", min_value=0, max_value=8, value=0)

            for i in range(int(num_slots)):
                s1, s2, s3 = st.columns([2, 1, 1])
                s1.text_input("Class name", key=f"slot_name_{i}", placeholder="Math Coaching")
                slot_start = s2.text_input("Start (HH:MM)", key=f"slot_start_{i}", value="09:00")
                slot_end = s3.text_input("End (HH:MM)", key=f"slot_end_{i}", value="11:00")
                if slot_start and slot_end:
                    coaching_slots.append({"start": slot_start, "end": slot_end})

            from utils import calculate_free_study_hours
            free_h, summary = calculate_free_study_hours(wake_time, sleep_time, coaching_slots)

            if free_h is not None:
                st.info(f"✅ {summary}")
                routine_info = {
                    "free_hours": free_h,
                    "routine_summary": summary,
                    "coaching_slots": coaching_slots,
                    "wake_time": wake_time,
                    "sleep_time": sleep_time,
                }
            else:
                st.warning("⚠️ Could not parse times. Use HH:MM format.")
            st.caption("📌 First study session starts 30 min after wake-up time")

        st.subheader("📆 Exam Dates (Optional)")
        st.caption("Leave 0 if no exam scheduled")

        for subject in subjects:
            days = st.number_input(
                f"Days until **{subject}** exam",
                min_value=0, max_value=365, value=0, key=f"exam_{subject}"
            )
            if days > 0:
                exam_dates[subject] = days

        st.subheader("📊 Subject Details")

        if "Self-Study" in student_type:
            for subject in subjects:
                st.write(f"**{subject}**")
                ca, cb, cc = st.columns(3)
                confidence_dict[subject] = ca.selectbox(
                    "Confidence",
                    ["Very Confident", "Okay", "Not Confident", "Complete Beginner"],
                    key=f"conf_{subject}"
                )
                topics_dict[subject] = cb.selectbox(
                    "Topics Left", ["1-3", "4-7", "8+"], key=f"topics_{subject}"
                )
                prior_dict[subject] = cc.selectbox(
                    "Studied Before?", ["Yes", "No"], key=f"prior_{subject}"
                )
        else:
            st.caption("Lower marks = more study time allocated automatically")
            for subject in subjects:
                marks_dict[subject] = st.number_input(
                    f"Current marks in **{subject}** (out of 100)",
                    min_value=0, max_value=100, value=60, key=f"marks_{subject}"
                )

    st.write("")
    generate_btn = st.button("🚀 Generate Study Plan", type="primary", use_container_width=True)

# ── RIGHT COLUMN ─────────────────────────────────────────────
with col_right:

    if generate_btn:
        effective_hours = hours_per_day

        is_valid, error_msg = validate_inputs(subjects, hours_per_day, num_days)
        if not is_valid:
            st.error(f"❌ {error_msg}")
            st.stop()

        difficulty = build_difficulty_dict(
            subjects=subjects,
            student_type=student_type,
            marks_dict=marks_dict if marks_dict else None,
            confidence_dict=confidence_dict if confidence_dict else None,
            topics_dict=topics_dict if topics_dict else None,
            prior_dict=prior_dict if prior_dict else None
        )

        timetable = generate_timetable(
            subjects, effective_hours, num_days,
            exam_dates=exam_dates if exam_dates else None,
            difficulty=difficulty if difficulty else None,
            routine_info=routine_info
        )

        score = get_productivity_score(hours_per_day, len(subjects))
        total_hours = sum(d["total_hrs"] for d in timetable)

        # ── Metrics row ───────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        for col, value, label in [
            (m1, f"{score}/10", "🎯 Productivity"),
            (m2, f"{total_hours:.0f}h", "⏱️ Total Hours"),
            (m3, f"{num_days}", "🗓️ Days Planned"),
            (m4, f"{len(subjects)}", "📚 Subjects"),
        ]:
            col.markdown(
                f'<div class="metric-card"><div class="metric-value">{value}</div>'
                f'<div class="metric-label">{label}</div></div>',
                unsafe_allow_html=True
            )

        st.write("")

        # ── Exam countdown progress bars ───────────────────
        if exam_dates:
            st.subheader("⏳ Exam Countdown")
            for subject, days_left in sorted(exam_dates.items(), key=lambda x: x[1]):
                label, progress = days_until_label(days_left)
                st.caption(f"**{subject}** — {label}")
                st.progress(progress)

            alerts = generate_revision_schedule(subjects, exam_dates)
            if alerts:
                st.write("")
                for alert in alerts:
                    box_class = "urgent-box" if "🚨" in alert else "alert-box"
                    st.markdown(f'<div class="{box_class}">{alert}</div>', unsafe_allow_html=True)
            st.write("")

        # ── Charts: where the hours actually go ────────────
        st.subheader("📊 Study Time Breakdown")
        chart_col1, chart_col2 = st.columns(2)

        # AFTER
        CHART_FONT = dict(family="Poppins, sans-serif", color="#2D3436")
        NO_TOOLBAR = {"displayModeBar": False}

        with chart_col1:
            hours_summary = get_subject_hours_summary(timetable)
            fig_pie = go.Figure(data=[go.Pie(
                labels=list(hours_summary.keys()),
                values=list(hours_summary.values()),
                hole=0.55,
                textinfo="label+percent",
                marker=dict(
                    colors=["#6C5CE7", "#00B894", "#0984E3", "#E17055", "#FDCB6E", "#E84393"],
                    line=dict(color="white", width=2)
                )
            )])
            fig_pie.update_layout(
                title=dict(text="Hours by Subject", x=0.02, xanchor="left", font=dict(size=14)),
                margin=dict(t=45, b=10, l=10, r=10),
                height=320,
                showlegend=False,
                font=CHART_FONT,
                paper_bgcolor="rgba(0,0,0,0)",
                uniformtext_minsize=8,
                uniformtext_mode="hide",
            )
            st.plotly_chart(fig_pie, use_container_width=True, config=NO_TOOLBAR)

        with chart_col2:
            days_x, hours_y = get_daily_hours_series(timetable)
            fig_bar = go.Figure(data=[go.Bar(
                x=[f"Day {d}" for d in days_x],
                y=hours_y,
                marker_color="#6C5CE7",
                marker_line_width=0,
                text=[f"{h}h" for h in hours_y],
                textposition="outside",
            )])
            fig_bar.update_layout(
                title=dict(text="Hours per day", x=0.5, font=dict(size=15)),
                margin=dict(t=50, b=10, l=10, r=10),
                height=320,
                yaxis_title="Hours",
                font=CHART_FONT,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(gridcolor="#EEE"),
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig_bar, use_container_width=True, config=NO_TOOLBAR)

        # ── Timetable ───────────────────────────────────────
        st.subheader("📅 Your Study Timetable")

        for day_plan in timetable:
            with st.expander(
                f"📅 Day {day_plan['day']}  —  {day_plan['total_hrs']} hrs total",
                expanded=(day_plan['day'] <= 2)
            ):
                if routine_info and use_routine:
                    scheduled_sessions = build_daily_schedule(
                        day_plan["sessions"], wake_time, sleep_time,
                        routine_info.get("coaching_slots", [])
                    )
                else:
                    scheduled_sessions = day_plan["sessions"]

                for session in scheduled_sessions:
                    time_str = ""
                    if routine_info and use_routine:
                        time_str = f'<code>{session["start_time"]} – {session["end_time"]}</code> &nbsp; '

                    st.markdown(
                        f'<div class="day-card">'
                        f'<b>{session["subject"]}</b> &nbsp; '
                        f'<code>{session["hours"]} hr</code> &nbsp; {time_str}'
                        f'{activity_tag(session["activity"])}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # ── Download ──────────────────────────────────────
        text_plan = format_timetable_text(timetable)
        st.download_button(
            label="⬇️ Download Timetable (.txt)",
            data=text_plan,
            file_name="study_plan.txt",
            mime="text/plain",
            use_container_width=True
        )

        # ── AI Section ────────────────────────────────────
        if use_ai and ai_api_key:
            st.divider()
            st.subheader("🤖 AI-Powered Insights")

            tab1, tab2 = st.tabs(["📋 Full AI Study Plan", "🎯 Priority Advice"])

            with tab1:
                with st.spinner("⏳ Generating AI plan..."):
                    ai_plan = get_ai_study_plan(
                        subjects      = subjects,
                        hours_per_day = effective_hours,
                        num_days      = num_days,
                        exam_dates    = exam_dates if exam_dates else None,
                        student_type  = student_type,
                        routine_info  = routine_info
                    )

                subj_hours, day_hrs = extract_ai_plan_stats(ai_plan)
                if subj_hours:
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        fig = go.Figure(data=[go.Pie(
                                labels=list(subj_hours.keys()), values=list(subj_hours.values()),
                                hole=0.55, textinfo="label+percent",
                                marker=dict(colors=["#6C5CE7","#00B894","#0984E3","#E17055","#FDCB6E"])
                            )])
                        fig.update_layout(title=dict(text="AI Plan: Hours by Subject", x=0.02, xanchor="left", font=dict(size=14)),
                                           height=300, margin=dict(t=45,b=10,l=10,r=10), showlegend=False,
                                           paper_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    with ac2:
                        days_sorted = sorted(day_hrs, key=int)
                        fig2 = go.Figure(data=[go.Bar(
                            x=[f"Day {d}" for d in days_sorted], y=[day_hrs[d] for d in days_sorted],
                             marker_color="#00B894"
                        )])
                        fig2.update_layout(title=dict(text="AI Plan: Hours per Day", x=0.02, xanchor="left", font=dict(size=14)),
                                            height=300, margin=dict(t=45,b=10,l=10,r=10),
                                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                render_ai_study_plan(ai_plan)

            with tab2:
                if exam_dates:
                    with st.spinner("Getting priority advice..."):
                        advice = get_ai_priority_advice(subjects, exam_dates)
                    st.markdown(
                        '<div class="day-card" style="border-left-color:#00B894;">'
                        '<b>🎯 Today\'s Priority Advice</b></div>',
                        unsafe_allow_html=True
                    )
                    st.markdown(advice)
                else:
                    st.info("Add exam dates to get priority advice from AI.")
        elif use_ai and not ai_api_key:
            st.warning("⚠️ Add your Groq API key in the sidebar to see AI insights.")

    else:
        st.info("👈 Fill in your details on the left and click **Generate Study Plan**.")
        st.markdown("""
        ### What you'll get:
        - ✅ Day-by-day study timetable with time slots
        - ✅ Visual breakdown of hours per subject & per day
        - ✅ Exam countdown with urgency indicators
        - ✅ Smart subject prioritization
        - ✅ Productivity score
        - ✅ AI-powered suggestions *(optional)*
        - ✅ Downloadable plan
        """)
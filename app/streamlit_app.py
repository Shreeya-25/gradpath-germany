"""GradPath Germany — Streamlit landing page and AI program advisor.

Run from the project root:
    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from advisor.agent import Advisor
from advisor.tools import Profile, convert_cgpa_to_german, load_programs

st.set_page_config(
    page_title="GradPath Germany | Your Next Chapter Starts Here",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Remote images are used for the visual prototype. Replace them with local,
# licensed images before production deployment if preferred.
HERO_IMAGE = (
    "https://images.unsplash.com/photo-1562774053-701939374585"
    "?auto=format&fit=crop&w=2000&q=85"
)
TUM_IMAGE = (
    "https://images.unsplash.com/photo-1564981797816-1043664bf78d"
    "?auto=format&fit=crop&w=1000&q=80"
)
CAMPUS_IMAGE = (
    "https://images.unsplash.com/photo-1541339907198-e08756dedf3f"
    "?auto=format&fit=crop&w=1000&q=80"
)
LIBRARY_IMAGE = (
    "https://images.unsplash.com/photo-1503676260728-1c00da094a0b"
    "?auto=format&fit=crop&w=1000&q=80"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap');

    :root {
        --navy: #13253a;
        --red: #a52b35;
        --cream: #f7f4ee;
        --muted: #64748b;
    }

    .stApp {
        background: var(--cream);
        color: var(--navy);
        font-family: 'DM Sans', sans-serif;
    }

    /* Keep default text readable on the cream background. */
    .stApp, .stApp p, .stApp label, .stApp li,
    .stApp [data-testid="stMarkdownContainer"] {
        color: #172b42;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #13253a;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: #fffdf9;
        border-right: 1px solid #e8e2d8;
    }
    [data-testid="stSidebar"] * { color: #172b42; }

    .brandline {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 0 22px;
    }
    .brandmark {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 42px;
        height: 42px;
        border-radius: 15px;
        background: #a52b35;
        color: white;
        font-size: 22px;
        box-shadow: 0 8px 18px rgba(165,43,53,.18);
    }
    .brandname {
        font-weight: 800;
        letter-spacing: .13em;
        font-size: .82rem;
        color: #172b42;
    }
    .brandtag {
        color: #788393;
        font-size: .68rem;
        letter-spacing: .15em;
        text-transform: uppercase;
        margin-top: 3px;
    }

    .hero {
        position: relative;
        overflow: hidden;
        min-height: 500px;
        display: flex;
        align-items: center;
        border-radius: 28px;
        padding: clamp(28px, 5vw, 72px);
        color: white;
        background-image:
            linear-gradient(90deg, rgba(12,25,43,.94) 0%,
            rgba(12,25,43,.78) 43%, rgba(12,25,43,.12) 100%),
            url("https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&w=2000&q=85");
        background-position: center;
        background-size: cover;
        box-shadow: 0 24px 70px rgba(24,36,55,.17);
    }
    .hero-content { max-width: 720px; position: relative; z-index: 1; }
    .eyebrow {
        color: #f2d7a7;
        text-transform: uppercase;
        letter-spacing: .19em;
        font-size: .72rem;
        font-weight: 800;
        margin-bottom: 20px;
    }
    .hero h1 {
        color: white;
        font-family: 'Playfair Display', Georgia, serif;
        font-size: clamp(2.6rem, 5vw, 4.7rem);
        line-height: 1.03;
        letter-spacing: -.035em;
        margin: 0 0 22px;
    }
    .hero p {
        color: #edf1f5;
        max-width: 570px;
        font-size: 1.03rem;
        line-height: 1.8;
        margin-bottom: 24px;
    }
    .hero-note {
        display: inline-block;
        padding: 10px 15px;
        border: 1px solid rgba(255,255,255,.45);
        border-radius: 999px;
        color: #fff;
        background: rgba(255,255,255,.10);
        font-size: .82rem;
    }
    .section-kicker {
        color: var(--red);
        text-transform: uppercase;
        letter-spacing: .18em;
        font-size: .7rem;
        font-weight: 800;
        margin-top: 38px;
        margin-bottom: 8px;
    }
    .section-title {
        color: var(--navy);
        font-family: 'Playfair Display', Georgia, serif;
        font-size: clamp(1.8rem, 3vw, 2.55rem);
        line-height: 1.15;
        margin: 0 0 12px;
    }
    .section-copy {
        color: var(--muted);
        line-height: 1.75;
        max-width: 760px;
    }
    .feature-card {
        background: #fff;
        border: 1px solid #e8e2d8;
        border-radius: 20px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 10px 32px rgba(22,36,60,.045);
    }
    .feature-card h3 { color: var(--navy); font-size: 1.1rem; margin: 8px 0; }
    .feature-card p { color: var(--muted); font-size: .9rem; line-height: 1.65; }
    .feature-icon {
        width: 42px; height: 42px; display: flex; align-items: center;
        justify-content: center; border-radius: 14px; background: #f5e8e7;
        font-size: 21px;
    }
    .stat-strip {
        display: flex; flex-wrap: wrap; gap: 12px; margin-top: 26px;
    }
    .stat-pill {
        border: 1px solid rgba(255,255,255,.28);
        background: rgba(255,255,255,.10);
        border-radius: 14px; padding: 12px 16px; min-width: 150px;
        backdrop-filter: blur(8px);
    }
    .stat-pill strong { display: block; color: white; font-size: .96rem; }
    .stat-pill span { color: #d7deea; font-size: .75rem; }
    .footer-note {
        text-align: center; color: #818b9d; font-size: .8rem;
        padding: 28px 8px 8px;
    }
    /* Keep button colors consistent after hover, click, and keyboard focus. */
    div.stButton > button,
    div.stButton > button:visited,
    div.stButton > button:hover,
    div.stButton > button:focus,
    div.stButton > button:active {
        border-radius: 12px;
        min-height: 2.8rem;
        font-weight: 700;
        border: 1px solid #d8dce2 !important;
        background: #fffdf9 !important;
        color: #172b42 !important;
        box-shadow: none;
        transition: background-color .18s ease, border-color .18s ease, transform .18s ease;
    }
    div.stButton > button:hover {
        background: #f5e8e7 !important;
        border-color: #a52b35 !important;
        color: #172b42 !important;
        transform: translateY(-1px);
    }
    div.stButton > button:focus-visible {
        outline: 3px solid rgba(165,43,53,.25) !important;
        outline-offset: 2px;
    }
    div.stButton > button[kind="primary"],
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[kind="primary"]:focus,
    div.stButton > button[kind="primary"]:active {
        background: #a52b35 !important;
        border-color: #a52b35 !important;
        color: #ffffff !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #84212a !important;
        border-color: #84212a !important;
    }
    [data-testid="stDialog"] [data-testid="stMarkdownContainer"],
    [data-testid="stDialog"] h1,
    [data-testid="stDialog"] h2,
    [data-testid="stDialog"] h3,
    [data-testid="stDialog"] p {
        color: #172b42 !important;
    }
    [data-testid="stDialog"] {
        background: #f7f4ee;
    }
    @media (max-width: 700px) {
        .hero { padding: 28px 22px; min-height: 470px; border-radius: 22px; }
        .hero h1 { font-size: 2.55rem; }
    }

/* Premium sidebar theme */
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #f1e4e2 0%,
        #f8f2eb 100%
    ) !important;
    border-right: 1px solid #dfc9c5;
}

/* Sidebar text */
[data-testid="stSidebar"] h3 {
    color: #8f2633 !important;
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.45rem;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #26384d !important;
}

/* Input boxes */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: #fffdf9 !important;
    border: 1px solid #d8c2be !important;
    border-radius: 10px !important;
}

/* Highlighted input focus */
[data-testid="stSidebar"] input:focus {
    border-color: #a52b35 !important;
    box-shadow: 0 0 0 2px rgba(165, 43, 53, 0.12) !important;
}

/* German grade metric card */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: #fffdf9;
    border: 1px solid #dfc9c5;
    border-left: 4px solid #a52b35;
    border-radius: 14px;
    padding: 14px;
    margin-top: 10px;
    box-shadow: 0 5px 16px rgba(19, 37, 58, 0.05);
}

[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: #64748b !important;
}

[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #8f2633 !important;
    font-weight: 800;
}

[data-testid="stSidebar"] hr {
    border-color: #dfc9c5;
}

    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="brandline">
      <div class="brandmark">✦</div>
      <div>
        <div class="brandname">GRADPATH GERMANY</div>
        <div class="brandtag">Your next chapter starts here</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="hero">
      <div class="hero-content">
        <div class="eyebrow">Study in Germany · Find your fit</div>
        <h1>Your future has<br>a place in Germany.</h1>
        <p>Discover master's programmes, understand admission requirements,
        and explore your next academic chapter with a more personal,
        AI-powered guide.</p>
        <div class="hero-note">✦ Explore with clarity. Apply with confidence.</div>
        <div class="stat-strip">
          <div class="stat-pill"><strong>Program discovery</strong><span>Explore your options</span></div>
          <div class="stat-pill"><strong>Profile-aware guidance</strong><span>Advice shaped around you</span></div>
          <div class="stat-pill"><strong>Source-grounded answers</strong><span>Verify before you apply</span></div>
        </div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-kicker">A clearer way forward</div>', unsafe_allow_html=True)
st.markdown('<h2 class="section-title">Your German university journey,<br>thoughtfully guided.</h2>', unsafe_allow_html=True)
st.markdown(
    '<p class="section-copy">Start with a university that inspires you, then use the '
    'AI advisor to explore programmes, eligibility, deadlines, and application documents. '
    'Always confirm final requirements on the official university website.</p>',
    unsafe_allow_html=True,
)


@st.dialog("Your GradPath guide", width="large")
def show_visual_dialog(kind: str) -> None:
    if kind == "universities":
        st.subheader("🏛️ Discover German universities")
        st.write(
            "Explore official university websites and master's programme "
            "catalogues. Check each programme's language, eligibility and deadlines."
        )

        universities = [
            (
                "Technical University of Munich (TUM)",
                "https://www.tum.de/en/",
                "https://www.tum.de/en/studies/degree-programs",
            ),
            (
                "RWTH Aachen University",
                "https://www.rwth-aachen.de/",
                "https://www.rwth-aachen.de/go/id/bdpg/lidx/1",
            ),
            (
                "Saarland University",
                "https://www.uni-saarland.de/en/home.html",
                "https://www.uni-saarland.de/en/study/programmes.html",
            ),
            (
                "University of Tübingen",
                "https://uni-tuebingen.de/en/",
                "https://uni-tuebingen.de/en/study/degree-programs/",
            ),
            (
                "Karlsruhe Institute of Technology (KIT)",
                "https://www.kit.edu/english/",
                "https://www.sle.kit.edu/english/vorstudium/degree-programs.php",
            ),
        ]

        for name, website, programmes in universities:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.markdown(
                    f"[Official university website]({website})  ·  "
                    f"[Browse degree programmes]({programmes})"
                )

        st.info(
            "These are starting points, not confirmed matches. Ask the AI "
            "advisor to compare specific AI, Machine Learning or Computer "
            "Science master's programmes."
        )

        st.divider()
        st.subheader("Programmes currently in the GradPath knowledge base")
        st.caption(
            "These seven programmes are loaded from your structured dataset. "
            "Deadlines and requirements can change; check the source and confidence notes."
        )

        try:
            programme_data = load_programs()
            for programme_id, item in programme_data.items():
                with st.expander(f"{item['university']} · {item['program']}"):
                    requirements = item.get("requirements", {})
                    st.markdown("**Academic background**")
                    st.write(requirements.get("degree", "Not captured in the current dataset."))

                    deadline_parts = []
                    for season, details in item.get("deadlines", {}).items():
                        close = details.get("close")
                        if close:
                            deadline_parts.append(f"{season.title()}: {close}")
                    st.markdown("**Captured deadline information**")
                    st.write(" · ".join(deadline_parts) if deadline_parts else "No deadline captured in the current dataset.")

                    low_confidence = any(
                        details.get("confidence") == "low"
                        for details in item.get("deadlines", {}).values()
                    )
                    if low_confidence:
                        st.warning("The captured deadline has low confidence or conflicting source information. Verify it on the official programme page.")
                    elif any("2026 cycle" in details.get("note", "") for details in item.get("deadlines", {}).values()):
                        st.warning("The captured date refers to the 2026 cycle. A later cycle date may not yet be published in this dataset.")
                    else:
                        st.caption("Structured dataset information only; confirm current dates on the official website.")

                    if st.button(
                        f"Ask GradPath about {item['program']}",
                        key=f"ask_program_{programme_id}",
                        use_container_width=True,
                    ):
                        st.session_state["gradpath_suggested_question"] = (
                            f"Explain the eligibility, academic requirements, deadlines, "
                            f"required documents, and source confidence for {item['program']} "
                            f"at {item['university']}. Use my profile and clearly flag any "
                            f"outdated, conflicting, or unverified information."
                        )
                        st.rerun()
        except Exception as exc:
            st.warning("The structured programme list could not be loaded. Check that data/programs.json is included in the project.")

    elif kind == "fit":
        st.subheader("🧭 Advice shaped around your profile")
        st.write(
            "Your academic background, grades, budget and preferences can "
            "help narrow down suitable programmes. Complete your profile "
            "in the sidebar before asking the advisor."
        )

        st.markdown("**What GradPath can help you investigate**")
        st.markdown(
            "- Bachelor's degree and subject compatibility\n"
            "- CGPA and university-specific grade requirements\n"
            "- Required subjects and ECTS credits\n"
            "- English or German language requirements\n"
            "- Tuition fees, living costs and location\n"
            "- Application documents and deadlines"
        )

        st.markdown("**Try asking the AI advisor:**")
        if st.button(
            "Find AI master's programmes for my profile",
            key="dialog_profile_question",
            use_container_width=True,
        ):
            st.session_state["gradpath_suggested_question"] = (
                "Using my profile, help me shortlist AI and Machine "
                "Learning master's programmes in Germany. Explain eligibility, "
                "subject requirements, language requirements, costs and "
                "official sources. Clearly identify anything not verified."
            )
            st.rerun()

        st.caption(
            "Eligibility is programme-specific. The advisor's suggestions "
            "are not an admission decision."
        )

    else:
        st.subheader("📚 Verify before you apply")
        st.write(
            "Use official university pages for admission rules. Explore "
            "independent student-review platforms for personal experiences."
        )

        st.markdown("**Official information**")
        st.markdown(
            "- [DAAD — Study programmes and university information]"
            "(https://www.daad.de/en/studying-in-germany/)\n"
            "- [Hochschulkompass — German higher education institutions]"
            "(https://www.hochschulkompass.de/en/)"
        )

        st.markdown("**Student experiences and reviews**")
        st.markdown(
            "- [StudyCheck — student reviews]"
            "(https://www.studycheck.de/)\n"
            "- [Mastersportal — master's programmes and student reviews]"
            "(https://www.mastersportal.com/)\n"
            "- [Reddit — discussions about German universities]"
            "(https://www.reddit.com/search/?q=German%20university%20reviews)"
        )

        st.warning(
            "These links lead to review platforms and discussions, not "
            "verified alumni testimonials for every university. Check the "
            "specific university, programme, review date and reviewer context. "
            "Always confirm admission requirements on official university pages."
        )

card1, card2, card3 = st.columns(3, gap="large")
with card1:
    st.markdown(
        f'<div class="feature-card"><img src="{TUM_IMAGE}" style="width:100%;height:150px;object-fit:cover;border-radius:14px;">'
        '<div class="feature-icon" style="margin-top:16px;">🏛️</div>'
        '<h3>Program discovery</h3>'
        '<p>Explore German universities and discover master’s programmes.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Explore your options ↗", key="explore_universities", use_container_width=True):
        show_visual_dialog("universities")

with card2:
    st.markdown(
        f'<div class="feature-card"><img src="{CAMPUS_IMAGE}" style="width:100%;height:150px;object-fit:cover;border-radius:14px;">'
        '<div class="feature-icon" style="margin-top:16px;">🧭</div>'
        '<h3>Profile-aware guidance</h3>'
        '<p>Get advice shaped around your degree, grades, budget and goals.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Understand my profile ↗", key="check_fit", use_container_width=True):
        show_visual_dialog("fit")

with card3:
    st.markdown(
        f'<div class="feature-card"><img src="{LIBRARY_IMAGE}" style="width:100%;height:150px;object-fit:cover;border-radius:14px;">'
        '<div class="feature-icon" style="margin-top:16px;">📚</div>'
        '<h3>Source-grounded answers</h3>'
        '<p>Verify admission requirements and explore student and alumni experiences.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Verify before applying ↗", key="plan_application", use_container_width=True):
        show_visual_dialog("application")


st.markdown('<div class="section-kicker">Your personal study companion</div>', unsafe_allow_html=True)
st.markdown('<h2 class="section-title">A little more clarity.<br>A lot more confidence.</h2>', unsafe_allow_html=True)
st.markdown(
    '<p class="section-copy">Use the advisor below to ask questions about programme requirements. '
    'The answer quality depends on the project knowledge base, so verify important details with official sources.</p>',
    unsafe_allow_html=True,
)

@st.cache_resource
def get_advisor() -> Advisor:
    return Advisor()


try:
    adv = get_advisor()
except Exception as exc:
    st.error("The AI advisor could not start. Check your environment variables and project dependencies.")
    st.exception(exc)
    st.stop()

with st.sidebar:
    st.markdown("### 🎓 Your profile")
    st.caption("Personalise the guidance with your academic background.")
    country = st.selectbox("Bachelor's country", ["India", "China", "Vietnam", "Other"], index=0)
    degree = st.text_input("Degree field", "Artificial Intelligence and Machine Learning")
    cgpa = st.number_input("CGPA", min_value=0.0, max_value=10.0, value=8.4, step=0.1)
    scale = st.number_input("CGPA scale", min_value=4.0, max_value=10.0, value=10.0, step=0.5)
    gre_q = st.number_input("GRE Quant (0 = none)", min_value=0, max_value=170, value=0)
    gre_a = st.number_input("GRE AWA (0 = none)", min_value=0.0, max_value=6.0, value=0.0, step=0.5)
    english = st.checkbox("English test done", value=False)
    aps = st.checkbox("APS certificate done", value=False)
    profile = Profile(
        country=country,
        degree_field=degree,
        cgpa=cgpa,
        scale=scale,
        gre_quant=gre_q or None,
        gre_awa=gre_a or None,
        english_test_done=english,
        aps_done=aps,
    )
    conv = convert_cgpa_to_german(cgpa, scale)
    st.metric("Estimated German grade", f"{conv['estimate_low']} to {conv['estimate_high']}")
    st.caption(conv["caveat"])
    st.divider()
    st.caption("GradPath is a guide, not an admissions decision. Confirm details with each university.")

tab_chat, tab_data = st.tabs(["💬 Ask the AI advisor", "📑 Data sources"])

with tab_chat:
    examples = [
        "Am I eligible for the Tuebingen machine learning master?",
        "What is the TUM Informatics winter deadline and what GRE score do I need?",
        "Which documents do I need for TUM Informatics?",
        "Compare deadlines for Saarland and RWTH Software Systems Engineering",
    ]
    st.markdown("**Not sure where to start? Try a question:**")
    cols = st.columns(2)
    clicked = None
    for index, example in enumerate(examples):
        with cols[index % 2]:
            if st.button(example, key=f"example_{index}", use_container_width=True):
                clicked = example

    suggested_question = st.session_state.pop(
    "gradpath_suggested_question", None
)
    question = suggested_question or st.chat_input(
    "Ask about programmes, eligibility, deadlines, or documents"
    ) or clicked
    if "history" not in st.session_state:
        st.session_state.history = []

    if question:
        with st.spinner("Checking the programme knowledge base..."):
            try:
                result = adv.run(question, profile)
                st.session_state.history.append((question, result))
            except Exception as exc:
                st.error("The advisor could not answer this question. Please check the backend configuration and try again.")
                st.exception(exc)

    for user_question, result in st.session_state.history:
        with st.chat_message("user"):
            st.write(user_question)
        with st.chat_message("assistant"):
            st.write(result.answer)
            if result.sources:
                with st.expander("Sources"):
                    st.text(result.sources)
            if result.tool_calls:
                with st.expander("Advisor activity"):
                    st.json([
                        {"tool": call["tool"], "args": call["args"]}
                        for call in result.tool_calls
                    ])
                    st.caption(f"Intents: {result.intents} | Programmes: {result.programs}")

with tab_data:
    st.subheader("Documents in the knowledge base")
    try:
        seen = {}
        for chunk in adv.chunks:
            seen.setdefault(chunk.doc_id, chunk)
        st.dataframe(
            [{
                "Document": chunk.doc_id,
                "University": chunk.university,
                "Programme": chunk.program,
                "Source type": chunk.source_type,
                "Status": chunk.status,
                "Last collected": chunk.scraped_on,
                "Source URL": chunk.source_url,
            } for chunk in seen.values()],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{len(adv.chunks)} knowledge chunks · {len(load_programs())} structured programmes.")
    except Exception as exc:
        st.warning("The knowledge-base document list is not available right now.")
        st.exception(exc)

st.markdown(
    '<div class="footer-note">GRADPATH GERMANY · Explore thoughtfully. Verify officially. Move forward confidently.</div>',
    unsafe_allow_html=True,
)

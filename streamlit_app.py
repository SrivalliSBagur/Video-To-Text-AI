import streamlit as st
import requests
import json
import threading
import os
import time

# ─── Helper Functions (must come before anything that calls them) ───
def load_history() -> list:
    """Reads last 5 entries from the request log."""
    log_file = "outputs/logs/requests.jsonl"
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        entries = [json.loads(l) for l in lines if l.strip()]
        history = [e for e in entries if e.get("success") and not e.get("from_cache")]
        return history[-5:][::-1]
    except:
        return []

def load_from_cache(url: str) -> dict | None:
    """Fetch a cached result directly by URL."""
    import hashlib
    key = hashlib.md5(url.encode()).hexdigest()
    cache_file = f"outputs/cache/{key}.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
    
API_URL = "http://127.0.0.1:8000"

# ─── Page Config ───────────────────────────────────────────
st.set_page_config(
    page_title="Video to Text AI",
    page_icon="🎬",
    layout="centered"
)

# ─── Sidebar History ───────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Recent Videos")
    history = load_history()

    if not history:
        st.markdown("*No videos processed yet.*")
    else:
        for i, entry in enumerate(history):
            content_icons = {
                "recipe": "🍳",
                "coding": "💻",
                "educational": "📚",
                "music": "🎵",
                "general": "🎯"
            }
            platform_icons = {
                "youtube": "▶️",
                "instagram": "📸",
                "facebook": "👍"
            }
            icon = content_icons.get(entry.get("content_type", "general"), "🎯")
            p_icon = platform_icons.get(entry.get("platform", ""), "🌐")

            if st.sidebar.button(
                f"{icon} {entry.get('content_type', '').upper()}\n{p_icon} {entry.get('platform', '')} · {entry.get('timestamp', '')[:10]}",
                key=f"history_{i}",
                use_container_width=True
            ):
                st.session_state["load_url"] = entry.get("url")
                st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    st.markdown("**Rate limit:** 5 requests/hour")
    st.markdown("**Max duration:** 10 minutes")
    st.markdown("**Supported:** YouTube, Instagram, Facebook")


# ─── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .main { padding: 2rem; }
    .title { font-size: 2.5rem; font-weight: 800; text-align: center; margin-bottom: 0; }
    .subtitle { text-align: center; color: #888; margin-bottom: 2rem; font-size: 1rem; }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .badge-recipe { background: #fff3e0; color: #e65100; }
    .badge-coding { background: #e8f5e9; color: #2e7d32; }
    .badge-educational { background: #e3f2fd; color: #1565c0; }
    .badge-music { background: #f3e5f5; color: #6a1b9a; }
    .badge-general { background: #f5f5f5; color: #424242; }
    .meta-row { color: #888; font-size: 0.85rem; margin-bottom: 1.5rem; }
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        padding-bottom: 4px;
        border-bottom: 2px solid #f0f0f0;
    }
    .ingredient-item { padding: 4px 0; border-bottom: 1px solid #f9f9f9; }
    .step-box {
        background: #fafafa;
        border-left: 3px solid #ddd;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .lyrics-box {
        background: #fafafa;
        padding: 1.2rem;
        border-radius: 8px;
        white-space: pre-line;
        font-family: Georgia, serif;
        line-height: 1.8;
        font-size: 0.95rem;
    }
    .transcript-box {
        background: #f9f9f9;
        padding: 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #555;
        line-height: 1.6;
        max-height: 200px;
        overflow-y: auto;
    }
    /* Sidebar history cards */
    section[data-testid="stSidebar"] .stButton button {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        border-left: 3px solid #888;
        text-align: left;
        padding: 10px 12px;
        font-size: 0.85rem;
        color: #333;
        line-height: 1.6;
        margin-bottom: 4px;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #eef2ff;
        border-left-color: #4f6ef7;
        color: #1a1a1a;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)


# ─── Header ────────────────────────────────────────────────
st.markdown('<div class="title">🎬 Video to Text AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Paste any YouTube, Instagram or Facebook video link and get instant structured output</div>', unsafe_allow_html=True)

# ─── Supported Platforms ───────────────────────────────────
st.markdown("""
<div style="text-align:center; margin-bottom: 1.5rem;">
    <span style="margin: 0 8px;">▶️ YouTube</span>
    <span style="margin: 0 8px;">📸 Instagram</span>
    <span style="margin: 0 8px;">👍 Facebook</span>
</div>
""", unsafe_allow_html=True)


# ─── Input ─────────────────────────────────────────────────
url = st.text_input(
    "Video URL",
    placeholder="https://www.youtube.com/watch?v=...",
    label_visibility="collapsed"
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    process_btn = st.button("⚡ Analyse", use_container_width=True, type="primary")

st.markdown("---")
    
# ─── Render Helpers ────────────────────────────────────────
def render_badge(content_type: str):
    st.markdown(
        f'<span class="badge badge-{content_type}">{content_type.upper()}</span>',
        unsafe_allow_html=True
    )

def render_meta(data: dict):
    duration_min = data["duration"] // 60
    duration_sec = data["duration"] % 60
    st.markdown(
        f'<div class="meta-row">'
        f'📺 <b>{data["title"]}</b> &nbsp;|&nbsp; '
        f'⏱ {duration_min}m {duration_sec}s &nbsp;|&nbsp; '
        f'🌐 {data["language"].upper()} &nbsp;|&nbsp; '
        f'🕐 Processed in {data["processing_time_seconds"]}s'
        f'</div>',
        unsafe_allow_html=True
    )

def render_recipe(output: dict):
    st.markdown(f"### 🍳 {output.get('title', 'Recipe')}")
    st.markdown(f"*{output.get('description', '')}*")
    if output.get("serving_size"):
        st.markdown(f"**Serves:** {output['serving_size']}")

    st.markdown('<div class="section-header">🛒 Ingredients</div>', unsafe_allow_html=True)
    for item in output.get("ingredients", []):
        st.markdown(f"- {item}")

    st.markdown('<div class="section-header">📋 Instructions</div>', unsafe_allow_html=True)
    for i, step in enumerate(output.get("instructions", []), 1):
        st.markdown(
            f'<div class="step-box"><b>Step {i}:</b> {step}</div>',
            unsafe_allow_html=True
        )

    if output.get("tips"):
        st.markdown('<div class="section-header">💡 Tips</div>', unsafe_allow_html=True)
        for tip in output["tips"]:
            st.markdown(f"- {tip}")

def render_coding(output: dict):
    st.markdown(f"### 💻 {output.get('title', 'Coding Tutorial')}")
    st.markdown(output.get("summary", ""))

    if output.get("tech_stack"):
        st.markdown('<div class="section-header">🛠 Tech Stack</div>', unsafe_allow_html=True)
        cols = st.columns(len(output["tech_stack"]))
        for i, tech in enumerate(output["tech_stack"]):
            cols[i].markdown(f"**{tech}**")

    if output.get("prerequisites"):
        st.markdown('<div class="section-header">📌 Prerequisites</div>', unsafe_allow_html=True)
        for p in output["prerequisites"]:
            st.markdown(f"- {p}")

    st.markdown('<div class="section-header">🪜 Steps</div>', unsafe_allow_html=True)
    for step in output.get("steps", []):
        with st.expander(f"**{step.get('step', '')}**"):
            st.markdown(step.get("explanation", ""))
            if step.get("code"):
                st.code(step["code"], language="python")

    if output.get("key_concepts"):
        st.markdown('<div class="section-header">🧠 Key Concepts</div>', unsafe_allow_html=True)
        for concept in output["key_concepts"]:
            st.markdown(f"- {concept}")

def render_educational(output: dict):
    st.markdown(f"### 📚 {output.get('title', 'Educational Video')}")
    st.markdown(f"**Subject:** {output.get('subject', '')}")
    st.markdown(output.get("concise_summary", ""))

    st.markdown('<div class="section-header">🔑 Key Points</div>', unsafe_allow_html=True)
    for point in output.get("key_points", []):
        st.markdown(f"- {point}")

    if output.get("important_terms"):
        st.markdown('<div class="section-header">📖 Important Terms</div>', unsafe_allow_html=True)
        st.markdown(" &nbsp;|&nbsp; ".join(
            [f"`{term}`" for term in output["important_terms"]]
        ))

    st.markdown('<div class="section-header">📝 Detailed Notes</div>', unsafe_allow_html=True)
    st.markdown(output.get("detailed_notes", ""))

    if output.get("takeaways"):
        st.markdown('<div class="section-header">✅ Takeaways</div>', unsafe_allow_html=True)
        for t in output["takeaways"]:
            st.markdown(f"- {t}")

def render_music(output: dict):
    st.markdown(f"### 🎵 {output.get('title', 'Unknown')} — {output.get('artist', 'Unknown')}")
    st.markdown(f"**Genre:** {output.get('genre', '')}")

    st.markdown('<div class="section-header">🎤 Lyrics</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="lyrics-box">{output.get("lyrics", "").replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True
    )

def render_general(output: dict):
    st.markdown(f"### 🎯 {output.get('title', 'Video Summary')}")
    st.markdown(output.get("summary", ""))

    if output.get("highlights"):
        st.markdown('<div class="section-header">✨ Highlights</div>', unsafe_allow_html=True)
        for h in output["highlights"]:
            st.markdown(f"- {h}")

    if output.get("topics_covered"):
        st.markdown('<div class="section-header">🏷 Topics Covered</div>', unsafe_allow_html=True)
        st.markdown(" &nbsp;|&nbsp; ".join(
            [f"`{t}`" for t in output["topics_covered"]]
        ))

    st.markdown(f"**Sentiment:** {output.get('sentiment', '').capitalize()}")


# ─── Content Type Router ───────────────────────────────────
RENDERERS = {
    "recipe": render_recipe,
    "coding": render_coding,
    "educational": render_educational,
    "music": render_music,
    "general": render_general,
}

# ─── Load from history if selected ────────────────────────
if "load_url" in st.session_state and st.session_state["load_url"]:
    cached_data = load_from_cache(st.session_state["load_url"])
    if cached_data:
        st.info(f"⚡ Showing cached result for: `{st.session_state['load_url']}`")

        render_badge(cached_data["content_type"])
        render_meta(cached_data)
        st.markdown("---")

        renderer = RENDERERS.get(cached_data["content_type"], render_general)
        renderer(cached_data["output"])

        st.markdown("---")
        with st.expander("📄 View Raw Transcript"):
            st.markdown(
                f'<div class="transcript-box">{cached_data["transcript"]}</div>',
                unsafe_allow_html=True
            )

        st.download_button(
            label="⬇️ Download Output as JSON",
            data=json.dumps(cached_data["output"], indent=2),
            file_name=f"{cached_data['video_id']}_output.json",
            mime="application/json"
        )

        if st.button("🔙 Back to Home"):
            st.session_state["load_url"] = None
            st.rerun()

        st.stop()  # don't render the input form below

# ─── Main Processing ───────────────────────────────────────
if process_btn:
    if not url:
        st.warning("Please paste a video URL first.")
    else:
        # with st.spinner("🔍 Validating link..."):
            try:
                health = requests.get(f"{API_URL}/health", timeout=3)
                if health.status_code != 200:
                    st.error("FastAPI server is not running. Start it with: uvicorn app.main:app --reload")
                    st.stop()
            except:
                st.error("❌ Cannot reach the backend. Make sure FastAPI is running in another terminal with: uvicorn app.main:app --reload")
                st.stop()

            try:
                progress = st.progress(0)
                status = st.empty()

                def update_status(pct, msg):
                    progress.progress(pct)
                    status.markdown(f"""
                        <div style="display:flex; align-items:center; gap:12px; 
                            padding:12px; background:#f8f9fa; border-radius:8px;">
                            <img src="https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif" width="35"/>
                            <span style="font-size:0.95rem; color:#444;">{msg}</span>
                        </div>
                    """, unsafe_allow_html=True)

                update_status(10, "🔍 Validating link...")
                update_status(25, "🎵 Downloading audio from video...")
                update_status(50, "🎙️ Transcribing with Whisper AI — this is the slowest step, hang tight!")

                response = requests.post(
                    f"{API_URL}/process",
                    json={"url": url},
                    timeout=600
                )

                update_status(85, "🧠 Classifying and summarizing with Claude...")

                data = response.json()

                if response.status_code == 200 and data:
                    progress.progress(100)
                    status.empty()

                    if data.get("from_cache"):
                        st.success("⚡ Loaded from cache instantly!")
                    else:
                        st.success(f"✅ Processed successfully in {data['processing_time_seconds']}s")
                        # Badge + Meta
                        render_badge(data["content_type"])
                        render_meta(data)

                    st.markdown("---")

                    # Render content type specific output
                    renderer = RENDERERS.get(data["content_type"], render_general)
                    renderer(data["output"])

                    st.markdown("---")

                    # Raw transcript expander
                    with st.expander("📄 View Raw Transcript"):
                        st.markdown(
                            f'<div class="transcript-box">{data["transcript"]}</div>',
                            unsafe_allow_html=True
                        )

                    # Download output as JSON
                    st.download_button(
                        label="⬇️ Download Output as JSON",
                        data=json.dumps(data["output"], indent=2),
                        file_name=f"{data['video_id']}_output.json",
                        mime="application/json"
                    )

                else:
                    progress.empty()
                    status.empty()
                    error_detail = response.json().get("detail", "Unknown error")
                    st.error(f"❌ {error_detail}")

                    # Helpful suggestions based on error
                    if "silent" in error_detail.lower() or "no spoken" in error_detail.lower():
                        st.info("""
                            💡 **Tips for better results:**
                            - Try a video where someone is **speaking clearly**
                            - Cooking tutorial with a voiceover works great
                            - Silent/aesthetic videos won't have extractable content
                        """)

            except requests.exceptions.Timeout:
                progress.empty()
                st.error("⏱ Request timed out. The video might be too long or Whisper is taking longer than usual.")
            except Exception as e:
                progress.empty()
                st.error(f"❌ Something went wrong: {str(e)}")
                import traceback
                st.code(traceback.format_exc())  # full traceback
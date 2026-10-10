import html
import uuid
from datetime import datetime

import streamlit as st

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Weather AI · LangGraph Assistant",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_CITY = "Lahore"

SUGGESTIONS = [
    "What's the weather in Lahore?",
    "Should I carry an umbrella in London today?",
    "How is the weather in Karachi right now?",
    "Explain how rain forms",
]

# ============================================================
# LOAD LANGGRAPH AGENT
# ============================================================

try:
    from main import agent, get_weather

    AGENT_ERROR = None

except Exception as exc:
    agent = None
    get_weather = None
    AGENT_ERROR = str(exc)

# ============================================================
# SESSION STATE
# ============================================================

def new_chat():
    chat_id = uuid.uuid4().hex[:8]

    st.session_state.chats[chat_id] = {
        "title": "New chat",
        "created": datetime.now(),
        "messages": [],
    }

    st.session_state.current = chat_id


def init_state():
    defaults = {
        "chats": {},
        "current": None,
        "dark": True,
        "weather": None,
        "weather_error": None,
        "boot_done": False,
        "pending": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.chats:
        new_chat()

    if st.session_state.current not in st.session_state.chats:
        new_chat()


init_state()

# ============================================================
# WEATHER RESPONSE PARSER
# Supports both old and new main.py response formats.
# ============================================================

def parse_weather(text: str):
    if not isinstance(text, str) or not text.strip():
        return None

    text = text.strip()

    error_prefixes = (
        "weather api error:",
        "could not reach weather service:",
        "could not connect to the weather service",
    )

    if text.lower().startswith(error_prefixes):
        return None

    fields = {}
    city = None

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        lower_line = line.lower()

        if lower_line.startswith("current weather for "):
            city = line[len("Current weather for "):].rstrip(":").strip()
            continue

        if lower_line.startswith("city:"):
            city = line.split(":", 1)[1].strip()
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()

    try:
        temp_text = fields.get("temperature", "")
        feels_text = fields.get("feels like", "")
        humidity_text = fields.get("humidity", "")

        temp_text = (
            temp_text.replace("°C", "")
            .replace("°c", "")
            .strip()
        )

        feels_text = (
            feels_text.replace("°C", "")
            .replace("°c", "")
            .strip()
        )

        humidity_text = humidity_text.replace("%", "").strip()

        if not city or not temp_text or not feels_text or not humidity_text:
            return None

        temperature = float(temp_text)
        feels_like = float(feels_text)
        humidity = int(float(humidity_text))

        condition = fields.get("condition", "Unknown")

        analysis = (
            fields.get("temperature analysis")
            or fields.get("analysis")
            or "Weather data retrieved."
        )

        wind_text = fields.get("wind speed", "").replace("m/s", "").strip()

        try:
            wind_speed = float(wind_text) if wind_text else None
        except ValueError:
            wind_speed = None

        return {
            "city": city,
            "temp": temperature,
            "feels": feels_like,
            "humidity": humidity,
            "condition": condition.title(),
            "analysis": analysis,
            "wind": wind_speed,
            "updated": datetime.now(),
        }

    except (TypeError, ValueError):
        return None


# ============================================================
# FETCH WEATHER
# ============================================================

def fetch_weather(city: str):
    if get_weather is None:
        st.session_state.weather_error = (
            "The weather tool could not be loaded. "
            "Check your API keys and agent configuration."
        )
        return False

    try:
        result = get_weather.invoke({"city": city})
        parsed = parse_weather(result)

        if parsed is None:
            st.session_state.weather_error = (
                str(result)
                if result
                else "The weather service returned an empty response."
            )
            return False

        st.session_state.weather = parsed
        st.session_state.weather_error = None

        return True

    except Exception as exc:
        st.session_state.weather_error = (
            f"Unable to retrieve weather for {city}: {exc}"
        )
        return False


# ============================================================
# HELPERS
# ============================================================

def message_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))

        return "".join(parts)

    return str(content)


def relative_day(dt):
    days = (datetime.now().date() - dt.date()).days

    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"

    return f"{days} days ago"


def condition_style(condition):
    condition = condition.lower()

    styles = [
        ("thunder", "⛈️", "#2a3150", "#141a30"),
        ("rain", "🌧️", "#27425a", "#16283a"),
        ("drizzle", "🌦️", "#2b4760", "#182c3f"),
        ("snow", "❄️", "#34506a", "#1e3347"),
        ("clear", "☀️", "#8a5a1f", "#4a2f12"),
        ("cloud", "☁️", "#34475a", "#1f2d3b"),
        ("mist", "🌫️", "#3a4852", "#222d35"),
        ("haze", "🌫️", "#4d4230", "#2b251b"),
        ("smoke", "🌫️", "#3a4852", "#222d35"),
        ("dust", "🌪️", "#55402a", "#2d2216"),
    ]

    for keyword, icon, color1, color2 in styles:
        if keyword in condition:
            return icon, color1, color2

    return "🌤️", "#1f4450", "#102530"


def temp_badge(temp):
    if temp >= 30:
        return "Hot", "hot"
    if temp >= 15:
        return "Moderate", "mod"
    return "Cold", "cold"


# ============================================================
# LANGGRAPH CHAT
# ============================================================

def run_agent(prompt, chat):
    if agent is None:
        raise RuntimeError("The LangGraph agent is unavailable.")

    # Use the existing conversation history.
    history = [
        (message["role"], message["content"])
        for message in chat["messages"]
    ]

    result = agent.invoke(
        {
            "messages": history + [("user", prompt)]
        }
    )

    messages = result.get("messages", [])

    if not messages:
        raise RuntimeError("The agent returned no messages.")

    reply = message_text(messages[-1].content).strip()
    weather = None

    # Check tool results for weather data.
    for message in messages:
        if (
            getattr(message, "type", "") == "tool"
            and getattr(message, "name", "") == "get_weather"
        ):
            parsed = parse_weather(message_text(message.content))

            if parsed:
                weather = parsed

    if not reply:
        reply = "I couldn't generate a response. Please try again."

    return reply, weather


# ============================================================
# THEME
# ============================================================

LIGHT = {
    "bg": "#E3EAE8",
    "surface": "#F2F6F4",
    "surface2": "#D8E2DF",
    "border": "#C2D0CC",
    "text": "#1B2B33",
    "muted": "#58707A",
    "accent": "#1F6F78",
    "accent_soft": "#CFE4E3",
    "on_accent": "#F2F6F4",
    "bubble_user": "#D4E3E1",
}

DARK = {
    "bg": "#0D1522",
    "surface": "#142033",
    "surface2": "#1B2A41",
    "border": "#27384F",
    "text": "#E4ECF5",
    "muted": "#8DA2BA",
    "accent": "#5BB0E8",
    "accent_soft": "#17304A",
    "on_accent": "#08121E",
    "bubble_user": "#1B2E48",
}


def inject_css():
    theme = DARK if st.session_state.dark else LIGHT

    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {{
    --bg: {theme['bg']};
    --surface: {theme['surface']};
    --surface2: {theme['surface2']};
    --border: {theme['border']};
    --text: {theme['text']};
    --muted: {theme['muted']};
    --accent: {theme['accent']};
    --accent-soft: {theme['accent_soft']};
    --on-accent: {theme['on_accent']};
    --bubble-user: {theme['bubble_user']};
}}

html, body, .stApp, [class*="css"] {{
    font-family: 'Manrope', sans-serif;
}}

.stApp {{
    background: var(--bg);
    color: var(--text);
}}

#MainMenu, footer {{
    visibility: hidden;
}}

header[data-testid="stHeader"] {{
    background: transparent;
}}

.block-container {{
    padding-top: 1.6rem;
    padding-bottom: 6rem;
    max-width: 980px;
}}

[data-testid="stSidebar"] {{
    background: var(--surface);
    border-right: 1px solid var(--border);
}}

[data-testid="stSidebar"] * {{
    color: var(--text);
}}

.brand {{
    font-weight: 800;
    font-size: 1.25rem;
    margin-bottom: .2rem;
}}

.brand small {{
    display: block;
    font-size: .72rem;
    font-weight: 500;
    color: var(--muted);
}}

.side-label {{
    font-size: .78rem;
    font-weight: 700;
    color: var(--muted);
    margin: 1.1rem 0 .4rem;
}}

.stButton > button,
.stFormSubmitButton > button {{
    width: 100%;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text);
    font-weight: 600;
}}

.stButton > button:hover,
.stFormSubmitButton > button:hover {{
    border-color: var(--accent);
    color: var(--accent);
}}

.stButton > button[kind="primary"] {{
    background: var(--accent);
    color: var(--on-accent);
    border-color: var(--accent);
}}

.page-title {{
    font-size: 1.7rem;
    font-weight: 800;
    margin: 0;
}}

.page-sub {{
    color: var(--muted);
    font-size: .92rem;
    margin: .15rem 0 .6rem;
}}

.stack-pill {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: .72rem;
    padding: .18rem .55rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    color: var(--muted);
    background: var(--surface);
    margin: 0 .3rem .8rem 0;
}}

[data-testid="stTextInput"] input {{
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 10px;
}}

[data-testid="stForm"] {{
    border: none;
    padding: 0;
}}

.wx-card {{
    border-radius: 18px;
    padding: 1.5rem 1.7rem;
    color: #F5F8FA;
    margin: .6rem 0 1rem;
    box-shadow: 0 6px 22px rgba(0,0,0,.22);
}}

.wx-card * {{
    color: #F5F8FA;
}}

.wx-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}}

.wx-city {{
    font-size: 1.25rem;
    font-weight: 700;
}}

.wx-cond {{
    opacity: .9;
    font-size: .95rem;
}}

.wx-temp {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 3.6rem;
    font-weight: 700;
    line-height: 1.2;
    margin-top: .5rem;
}}

.wx-icon {{
    font-size: 4.2rem;
}}

.wx-stats {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .7rem;
    margin-top: 1.2rem;
}}

.wx-stat {{
    background: rgba(255,255,255,.14);
    border-radius: 12px;
    padding: .65rem .8rem;
    min-width: 0;
    overflow-wrap: anywhere;
}}

.wx-stat span {{
    display: block;
    font-size: .74rem;
    opacity: .9;
    margin-bottom: .3rem;
}}

.wx-stat b {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
}}

.wx-stat b.txt {{
    font-family: 'Manrope', sans-serif;
    font-size: .85rem;
}}

.badge {{
    padding: .15rem .55rem;
    border-radius: 999px;
    font-size: .8rem;
    font-weight: 700;
    font-family: 'Manrope', sans-serif;
}}

.badge.hot {{
    background: #F7C6B8;
    color: #7A2410;
}}

.badge.mod {{
    background: #CFE8D2;
    color: #1F5A2B;
}}

.badge.cold {{
    background: #C9DEF4;
    color: #1C4670;
}}

.wx-foot {{
    margin-top: 1rem;
    font-size: .8rem;
    opacity: .85;
    font-family: 'JetBrains Mono', monospace;
}}

.wx-empty {{
    border: 1px dashed var(--border);
    border-radius: 16px;
    padding: 1.4rem;
    text-align: center;
    color: var(--muted);
    background: var(--surface);
    margin: .6rem 0 1rem;
}}

[data-testid="stChatMessage"] {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: .8rem 1rem;
}}

[data-testid="stBottom"],
[data-testid="stBottom"] > div {{
    background: var(--bg);
}}

[data-testid="stChatInput"] {{
    border-radius: 14px;
    border: 1px solid var(--border);
    background: var(--surface);
}}

[data-testid="stChatInput"] textarea {{
    color: var(--text);
}}

.empty-chat {{
    text-align: center;
    color: var(--muted);
    padding: 1.2rem 0 .6rem;
}}

@media (max-width: 768px) {{
    .block-container {{
        padding: 1rem .8rem 6rem;
    }}

    .wx-stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}

    .wx-temp {{
        font-size: 2.8rem;
    }}

    .wx-icon {{
        font-size: 3.2rem;
    }}

    .page-title {{
        font-size: 1.35rem;
    }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


inject_css()

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            🌤️ Weather AI
            <small>LangGraph assistant</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("＋ New chat", type="primary", use_container_width=True):
        new_chat()
        st.rerun()

    st.markdown(
        '<div class="side-label">🕘 Recent chats</div>',
        unsafe_allow_html=True,
    )

    ordered_chats = sorted(
        st.session_state.chats.items(),
        key=lambda item: item[1]["created"],
        reverse=True,
    )

    for chat_id, chat_item in ordered_chats:
        prefix = "▸ " if chat_id == st.session_state.current else ""

        label = (
            f"{prefix}{chat_item['title']} · "
            f"{relative_day(chat_item['created'])}"
        )

        if st.button(
            label,
            key=f"chat_{chat_id}",
            use_container_width=True,
        ):
            st.session_state.current = chat_id
            st.rerun()

    st.markdown(
        '<div class="side-label">Settings</div>',
        unsafe_allow_html=True,
    )

    previous_dark = st.session_state.dark

    st.session_state.dark = st.toggle(
        "🌙 Dark mode",
        value=st.session_state.dark,
    )

    if st.session_state.dark != previous_dark:
        st.rerun()

    if st.button("🗑️ Clear history", use_container_width=True):
        st.session_state.chats = {}
        new_chat()
        st.rerun()

    st.caption("Gemini · LangGraph · OpenWeather")

# ============================================================
# AGENT LOAD ERROR
# ============================================================

if AGENT_ERROR:
    st.error(
        "**The agent could not be loaded.**\n\n"
        f"`{AGENT_ERROR}`\n\n"
        "Check that main.py is in the same folder and that "
        "GOOGLE_API_KEY and OPENWEATHER_API_KEY are configured "
        "in your local .env file or Streamlit Secrets."
    )
    st.stop()

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<p class="page-title">AI Weather Assistant</p>',
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="page-sub">Ask about the weather anywhere, or ask anything else.</p>'
    '<span class="stack-pill">LangGraph</span>'
    '<span class="stack-pill">Gemini</span>'
    '<span class="stack-pill">OpenWeather</span>',
    unsafe_allow_html=True,
)

# ============================================================
# CITY SEARCH
# ============================================================

with st.form("city_form", clear_on_submit=True, border=False):
    col_input, col_button = st.columns([5, 1])

    city_query = col_input.text_input(
        "City",
        placeholder="Search a city, e.g. Karachi",
        label_visibility="collapsed",
    )

    searched = col_button.form_submit_button(
        "🔎 Search",
        use_container_width=True,
    )

if not st.session_state.boot_done:
    st.session_state.boot_done = True

    with st.spinner("Loading weather..."):
        fetch_weather(DEFAULT_CITY)

if searched and city_query.strip():
    with st.spinner(f"Fetching weather for {city_query.strip()}..."):
        fetch_weather(city_query.strip())

# ============================================================
# WEATHER DASHBOARD — HTML RENDERING FIX
# ============================================================

weather = st.session_state.weather
weather_error = st.session_state.weather_error

# Show a warning only if the weather request actually failed.
if weather_error:
    st.warning(
        f"**Couldn't load weather.** {weather_error}\n\n"
        "Check the city name and your OpenWeather API key, then try again."
    )

if weather:
    icon, color1, color2 = condition_style(weather["condition"])
    badge_text, badge_class = temp_badge(weather["temp"])

    # Escape API-provided strings before inserting them into HTML.
    city_html = html.escape(str(weather["city"]))
    condition_html = html.escape(str(weather["condition"]))
    analysis_html = html.escape(str(weather["analysis"]))

    wind = weather.get("wind")

    wind_html = ""

    if wind is not None:
        wind_html = f"""
            <div class="wx-stat">
                <span>Wind speed</span>
                <b>{wind:.1f} m/s</b>
            </div>
        """

    # Construct the complete weather card.
    # Render this entire HTML string once with unsafe_allow_html=True.
    weather_html = f"""
    <div class="wx-card"
         style="background:linear-gradient(135deg,{color1},{color2});">

        <div class="wx-top">
            <div>
                <div class="wx-city">📍 {city_html}</div>
                <div class="wx-cond">{condition_html}</div>
                <div class="wx-temp">{weather['temp']:.1f}°C</div>
            </div>

            <div class="wx-icon">{icon}</div>
        </div>

        <div class="wx-stats">

            <div class="wx-stat">
                <span>Feels like</span>
                <b>{weather['feels']:.1f}°C</b>
            </div>

            <div class="wx-stat">
                <span>Humidity</span>
                <b>{weather['humidity']}%</b>
            </div>

            <div class="wx-stat">
                <span>Level</span>
                <b>
                    <em class="badge {badge_class}"
                        style="font-style:normal;">
                        {badge_text}
                    </em>
                </b>
            </div>

            <div class="wx-stat">
                <span>Temperature analysis</span>
                <b class="txt">{analysis_html}</b>
            </div>

            {wind_html}

        </div>

        <div class="wx-foot">
            Last updated {weather['updated'].strftime('%I:%M:%S %p')}
        </div>

    </div>
    """

    # IMPORTANT: Do not pass weather_html to st.code() or st.text().
    st.markdown(weather_html, unsafe_allow_html=True)

    if st.button("🔄 Refresh weather", key="refresh_weather"):
        with st.spinner("Refreshing weather..."):
            fetch_weather(weather["city"])
        st.rerun()

elif not weather_error:
    st.markdown(
        """
        <div class="wx-empty">
            Search a city above or ask the assistant to see live weather here.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# CHAT HISTORY
# ============================================================

chat = st.session_state.chats[st.session_state.current]

if not chat["messages"]:
    st.markdown(
        '<div class="empty-chat">💡 Try one of these to get started</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(2)

    for index, question in enumerate(SUGGESTIONS):
        if columns[index % 2].button(
            question,
            key=f"suggestion_{index}",
            use_container_width=True,
        ):
            st.session_state.pending = question
            st.rerun()

for message in chat["messages"]:
    avatar = "🧑‍💻" if message["role"] == "user" else "🌤️"

    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# ============================================================
# CHAT INPUT
# ============================================================

typed_prompt = st.chat_input(
    "Ask about the weather or anything else..."
)

prompt = typed_prompt or st.session_state.pending
st.session_state.pending = None

# ============================================================
# PROCESS CHAT
# ============================================================

if prompt:
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    reply = None
    new_weather = None

    with st.chat_message("assistant", avatar="🌤️"):
        with st.spinner("Thinking..."):
            try:
                reply, new_weather = run_agent(prompt, chat)
                st.markdown(reply)

            except Exception as exc:
                error_text = str(exc)
                lower_error = error_text.lower()

                if "429" in error_text or "quota" in lower_error:
                    friendly_error = (
                        "The AI service is rate-limited. "
                        "Please wait a moment and try again."
                    )
                elif (
                    "api key" in lower_error
                    or "401" in error_text
                    or "403" in error_text
                ):
                    friendly_error = (
                        "An API key is missing or invalid. "
                        "Check your Streamlit Secrets configuration."
                    )
                else:
                    friendly_error = (
                        "Something went wrong while contacting the agent. "
                        "Please try again."
                    )

                st.error(friendly_error)

                with st.expander("Technical details"):
                    st.code(error_text)

    if reply is not None:
        if not chat["messages"]:
            chat["title"] = (
                prompt[:28] + "…"
                if len(prompt) > 28
                else prompt
            )

        chat["messages"].append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        chat["messages"].append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

        if new_weather:
            st.session_state.weather = new_weather
            st.session_state.weather_error = None

        st.rerun()

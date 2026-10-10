import uuid
from datetime import datetime

import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Weather AI · LangGraph Assistant",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# LOAD THE AGENT
# ============================================================

try:
    from main import agent, get_weather

    AGENT_ERROR = None

except Exception as exc:
    agent, get_weather = None, None
    AGENT_ERROR = str(exc)


DEFAULT_CITY = "Lahore"

SUGGESTIONS = [
    "What's the weather in Lahore?",
    "Should I carry an umbrella in London today?",
    "How is the weather in Karachi right now?",
    "Explain how rain forms",
]

CONDITIONS = {
    "thunder": (
        "⛈️",
        "linear-gradient(135deg,#4a5578,#2c3350)",
        "linear-gradient(135deg,#2a3150,#141a30)",
    ),
    "rain": (
        "🌧️",
        "linear-gradient(135deg,#5f7f98,#3d5a73)",
        "linear-gradient(135deg,#27425a,#16283a)",
    ),
    "drizzle": (
        "🌦️",
        "linear-gradient(135deg,#6a8aa0,#48677d)",
        "linear-gradient(135deg,#2b4760,#182c3f)",
    ),
    "snow": (
        "❄️",
        "linear-gradient(135deg,#8fb0c8,#6b8fab)",
        "linear-gradient(135deg,#34506a,#1e3347)",
    ),
    "clear": (
        "☀️",
        "linear-gradient(135deg,#d99a3d,#b9702a)",
        "linear-gradient(135deg,#8a5a1f,#4a2f12)",
    ),
    "cloud": (
        "☁️",
        "linear-gradient(135deg,#7592a6,#546f84)",
        "linear-gradient(135deg,#34475a,#1f2d3b)",
    ),
    "mist": (
        "🌫️",
        "linear-gradient(135deg,#8b9ea8,#697c87)",
        "linear-gradient(135deg,#3a4852,#222d35)",
    ),
    "haze": (
        "🌫️",
        "linear-gradient(135deg,#a39070,#7d6c50)",
        "linear-gradient(135deg,#4d4230,#2b251b)",
    ),
    "smoke": (
        "🌫️",
        "linear-gradient(135deg,#8b9ea8,#697c87)",
        "linear-gradient(135deg,#3a4852,#222d35)",
    ),
    "dust": (
        "🌪️",
        "linear-gradient(135deg,#a8855a,#7d6140)",
        "linear-gradient(135deg,#55402a,#2d2216)",
    ),
}

DEFAULT_CONDITION = (
    "🌤️",
    "linear-gradient(135deg,#4f8a96,#2f5f6b)",
    "linear-gradient(135deg,#1f4450,#102530)",
)


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
    if "chats" not in st.session_state:
        st.session_state.chats = {}
        st.session_state.current = None
        st.session_state.dark = True
        st.session_state.weather = None
        st.session_state.weather_error = None
        st.session_state.pending = None
        st.session_state.boot_done = False

        new_chat()


init_state()


# ============================================================
# WEATHER PARSER — FIXED
# ============================================================

def parse_weather(text: str):
    """
    Parse weather responses from main.py.

    Supports both formats:

    City: Lahore
    Temperature: 30°C

    AND

    Current weather for Lahore, PK:
    Temperature: 30°C
    """

    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    # Handle actual errors returned by the weather tool.
    error_prefixes = (
        "weather api error:",
        "could not reach weather service:",
        "could not connect to the weather service",
        "could not find weather information",
        "the weather service returned an error",
    )

    if text.lower().startswith(error_prefixes):
        return None

    fields = {}
    city = None

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Newer response format:
        # Current weather for New York, US:
        if line.lower().startswith("current weather for "):
            city = line[len("Current weather for "):].rstrip(":").strip()
            continue

        # Original response format:
        # City: New York
        if line.lower().startswith("city:"):
            city = line.split(":", 1)[1].strip()
            continue

        # Parse fields such as Temperature, Feels like, Humidity.
        if ":" in line:
            key, value = line.split(":", 1)

            fields[key.strip().lower()] = value.strip()

    try:
        temperature_text = fields.get("temperature", "")
        feels_text = fields.get("feels like", "")
        humidity_text = fields.get("humidity", "")

        # Support temperature values with or without °C.
        temperature_text = (
            temperature_text
            .replace("°C", "")
            .replace("°c", "")
            .strip()
        )

        feels_text = (
            feels_text
            .replace("°C", "")
            .replace("°c", "")
            .strip()
        )

        humidity_text = humidity_text.replace("%", "").strip()

        if not city:
            return None

        if not temperature_text or not feels_text or not humidity_text:
            return None

        temperature = float(temperature_text)
        feels_like = float(feels_text)
        humidity = int(float(humidity_text))

        condition = fields.get("condition", "Unknown")

        analysis = (
            fields.get("analysis")
            or fields.get("temperature analysis")
            or "Weather data retrieved successfully."
        )

        # Extract wind speed if available.
        wind_text = fields.get("wind speed", "N/A")

        wind_text = wind_text.replace("m/s", "").strip()

        try:
            wind_speed = float(wind_text)
        except (TypeError, ValueError):
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

    except (KeyError, TypeError, ValueError):
        return None


# ============================================================
# FETCH WEATHER — FIXED
# ============================================================

def fetch_weather(city: str):
    """
    Fetch current weather directly from the weather tool.

    Returns True when weather data is successfully parsed.
    """

    if get_weather is None:
        st.session_state.weather_error = (
            "The weather tool is unavailable. "
            "Check the agent configuration and API secrets."
        )
        return False

    try:
        raw = get_weather.invoke({"city": city})

        # Parse the response before deciding whether it failed.
        data = parse_weather(raw)

        if data is None:
            # Do not show a false success or hide genuine errors.
            st.session_state.weather_error = (
                str(raw)
                if raw
                else "The weather service returned an empty response."
            )
            return False

        # Successful response: update the dashboard and clear the warning.
        st.session_state.weather = data
        st.session_state.weather_error = None

        return True

    except Exception as exc:
        st.session_state.weather_error = (
            f"Unable to retrieve weather for {city}. "
            f"Details: {exc}"
        )
        return False


# ============================================================
# GENERAL HELPERS
# ============================================================

def message_text(content) -> str:
    """Convert Gemini message content into text."""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for block in content:
            if isinstance(block, str):
                parts.append(block)

            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))

        return "".join(parts)

    return str(content)


def relative_day(dt: datetime) -> str:
    days = (datetime.now().date() - dt.date()).days

    if days <= 0:
        return "Today"

    if days == 1:
        return "Yesterday"

    return f"{days} days ago"


def condition_style(condition: str):
    low = condition.lower()

    for key, style in CONDITIONS.items():
        if key in low:
            return style

    return DEFAULT_CONDITION


def temp_badge(temp: float):
    if temp >= 30:
        return "Hot", "hot"

    if temp >= 15:
        return "Moderate", "mod"

    return "Cold", "cold"


# ============================================================
# LANGGRAPH CHAT
# ============================================================

def run_agent(prompt: str, chat: dict):
    """
    Send the conversation to LangGraph.

    Returns:
        reply: Assistant response
        weather: Parsed weather information, if available
    """

    if agent is None:
        raise RuntimeError("The LangGraph agent is unavailable.")

    history = [
        (message["role"], message["content"])
        for message in chat["messages"]
    ]

    result = agent.invoke(
        {
            "messages": history + [("user", prompt)]
        }
    )

    messages = result["messages"]

    # Locate the new messages generated during this invocation.
    new_messages = messages[len(history) + 1:]

    weather = None

    for msg in new_messages:
        if (
            getattr(msg, "type", "") == "tool"
            and getattr(msg, "name", "") == "get_weather"
        ):
            parsed = parse_weather(message_text(msg.content))

            if parsed is not None:
                weather = parsed

    reply = message_text(messages[-1].content).strip()

    if not reply:
        reply = "I couldn't generate a response. Please try again."

    return reply, weather


# ============================================================
# THEME COLORS
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
    "shadow": "0 6px 20px rgba(31,59,66,.10)",
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
    "shadow": "0 6px 22px rgba(0,0,0,.35)",
}


# ============================================================
# CSS
# ============================================================

def inject_css():
    theme = DARK if st.session_state.dark else LIGHT

    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {{
  --bg:{theme['bg']};
  --surface:{theme['surface']};
  --surface2:{theme['surface2']};
  --border:{theme['border']};
  --text:{theme['text']};
  --muted:{theme['muted']};
  --accent:{theme['accent']};
  --accent-soft:{theme['accent_soft']};
  --on-accent:{theme['on_accent']};
  --bubble-user:{theme['bubble_user']};
  --shadow:{theme['shadow']};
}}

html, body, .stApp, [class*="css"] {{
  font-family:'Manrope',sans-serif;
}}

.stApp {{
  background:var(--bg);
  color:var(--text);
}}

.stApp p,
.stApp label,
.stApp span,
.stApp li,
.stApp h1,
.stApp h2,
.stApp h3 {{
  color:inherit;
}}

#MainMenu, footer {{
  visibility:hidden;
}}

header[data-testid="stHeader"] {{
  background:transparent;
}}

.block-container {{
  padding-top:1.6rem;
  padding-bottom:6rem;
  max-width:980px;
}}

[data-testid="stSidebar"] {{
  background:var(--surface);
  border-right:1px solid var(--border);
}}

[data-testid="stSidebar"] * {{
  color:var(--text);
}}

.brand {{
  display:flex;
  align-items:center;
  gap:.6rem;
  font-weight:800;
  font-size:1.25rem;
  margin-bottom:.2rem;
}}

.brand small {{
  display:block;
  font-weight:500;
  font-size:.72rem;
  color:var(--muted);
}}

.side-label {{
  font-size:.78rem;
  font-weight:700;
  color:var(--muted);
  margin:1.1rem 0 .4rem;
}}

.stButton > button,
.stFormSubmitButton > button {{
  width:100%;
  border-radius:10px;
  border:1px solid var(--border);
  background:var(--surface2);
  color:var(--text);
  font-weight:600;
  transition:all .15s ease;
}}

.stButton > button:hover,
.stFormSubmitButton > button:hover {{
  border-color:var(--accent);
  color:var(--accent);
  background:var(--accent-soft);
}}

.stButton > button[kind="primary"] {{
  background:var(--accent);
  color:var(--on-accent);
  border-color:var(--accent);
}}

.stButton > button[kind="primary"] * {{
  color:var(--on-accent);
}}

.stButton > button[kind="primary"]:hover {{
  filter:brightness(1.08);
  background:var(--accent);
}}

.page-title {{
  font-size:1.7rem;
  font-weight:800;
  letter-spacing:-.02em;
  margin:0;
}}

.page-sub {{
  color:var(--muted);
  font-size:.92rem;
  margin:.15rem 0 .6rem;
}}

.stack-pill {{
  display:inline-block;
  font-family:'JetBrains Mono',monospace;
  font-size:.72rem;
  padding:.18rem .55rem;
  border:1px solid var(--border);
  border-radius:999px;
  color:var(--muted);
  background:var(--surface);
  margin:0 .3rem .8rem 0;
}}

[data-testid="stTextInput"] input {{
  background:var(--surface);
  color:var(--text);
  border:1px solid var(--border);
  border-radius:10px;
}}

[data-testid="stTextInput"] input:focus {{
  border-color:var(--accent);
  box-shadow:0 0 0 1px var(--accent);
}}

[data-testid="stForm"] {{
  border:none;
  padding:0;
}}

.wx-card {{
  border-radius:18px;
  padding:1.5rem 1.7rem;
  color:#F5F8FA;
  box-shadow:var(--shadow);
  margin:.6rem 0 1rem;
}}

.wx-card * {{
  color:#F5F8FA;
}}

.wx-top {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:1rem;
  flex-wrap:wrap;
}}

.wx-city {{
  font-size:1.25rem;
  font-weight:700;
}}

.wx-cond {{
  opacity:.9;
  font-size:.95rem;
}}

.wx-temp {{
  font-family:'JetBrains Mono',monospace;
  font-size:3.6rem;
  font-weight:700;
  line-height:1;
  margin-top:.5rem;
}}

.wx-icon {{
  font-size:4.2rem;
  line-height:1;
}}

.wx-stats {{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:.7rem;
  margin-top:1.2rem;
}}

.wx-stat {{
  background:rgba(255,255,255,.14);
  border-radius:12px;
  padding:.65rem .8rem;
}}

.wx-stat > span {{
  display:block;
  font-size:.74rem;
  opacity:.85;
  margin-bottom:.15rem;
}}

.wx-stat b {{
  font-family:'JetBrains Mono',monospace;
  font-size:1.05rem;
}}

.wx-stat b.txt {{
  font-family:'Manrope',sans-serif;
  font-size:.85rem;
}}

.badge {{
  padding:.1rem .6rem;
  border-radius:999px;
  font-size:.8rem;
  font-weight:700;
  font-family:'Manrope',sans-serif;
}}

.wx-card .badge.hot {{
  background:#F7C6B8;
  color:#7A2410;
}}

.wx-card .badge.mod {{
  background:#CFE8D2;
  color:#1F5A2B;
}}

.wx-card .badge.cold {{
  background:#C9DEF4;
  color:#1C4670;
}}

.wx-foot {{
  margin-top:1rem;
  font-size:.8rem;
  opacity:.85;
  font-family:'JetBrains Mono',monospace;
}}

.wx-empty {{
  border:1px dashed var(--border);
  border-radius:16px;
  padding:1.4rem;
  text-align:center;
  color:var(--muted);
  background:var(--surface);
  margin:.6rem 0 1rem;
}}

[data-testid="stChatMessage"] {{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:14px;
  padding:.8rem 1rem;
}}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
  background:var(--bubble-user);
}}

[data-testid="stBottom"],
[data-testid="stBottom"] > div {{
  background:var(--bg);
}}

[data-testid="stChatInput"] {{
  border-radius:14px;
  border:1px solid var(--border);
  background:var(--surface);
}}

[data-testid="stChatInput"] textarea {{
  color:var(--text);
}}

.empty-chat {{
  text-align:center;
  color:var(--muted);
  padding:1.2rem 0 .6rem;
}}

.loader {{
  display:flex;
  align-items:center;
  gap:.6rem;
  color:var(--muted);
  font-size:.92rem;
  padding:.4rem 0;
}}

.dots span {{
  display:inline-block;
  width:8px;
  height:8px;
  margin-right:4px;
  border-radius:50%;
  background:var(--accent);
  animation:bounce 1s infinite ease-in-out;
}}

.dots span:nth-child(2) {{
  animation-delay:.15s;
}}

.dots span:nth-child(3) {{
  animation-delay:.3s;
}}

@keyframes bounce {{
  0%,80%,100% {{ transform:scale(.5); opacity:.4; }}
  40% {{ transform:scale(1); opacity:1; }}
}}

@media (max-width:768px) {{
  .block-container {{
    padding:1rem .8rem 6rem;
  }}

  .wx-stats {{
    grid-template-columns:repeat(2,1fr);
  }}

  .wx-temp {{
    font-size:2.8rem;
  }}

  .wx-icon {{
    font-size:3.2rem;
  }}

  .page-title {{
    font-size:1.35rem;
  }}
}}

@media (prefers-reduced-motion:reduce) {{
  .dots span {{
    animation:none;
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
        '<div class="brand">🌤️<div>Weather AI'
        '<small>LangGraph assistant</small></div></div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "＋  New chat",
        type="primary",
        use_container_width=True,
    ):
        if st.session_state.chats[
            st.session_state.current
        ]["messages"]:
            new_chat()

        st.rerun()

    st.markdown(
        '<div class="side-label">🕘 Recent chats</div>',
        unsafe_allow_html=True,
    )

    ordered = sorted(
        st.session_state.chats.items(),
        key=lambda item: item[1]["created"],
        reverse=True,
    )

    for chat_id, chat_item in ordered:

        active = "▸ " if chat_id == st.session_state.current else ""

        label = (
            f"{active}{chat_item['title']} · "
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

    st.session_state.dark = st.toggle(
        "🌙 Dark mode",
        value=st.session_state.dark,
    )

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

with st.form(
    "city_form",
    clear_on_submit=True,
    border=False,
):
    col_in, col_btn = st.columns([5, 1])

    city_query = col_in.text_input(
        "City",
        placeholder="Search a city, e.g. Karachi",
        label_visibility="collapsed",
    )

    searched = col_btn.form_submit_button(
        "🔎 Search",
        use_container_width=True,
    )


# Load default weather once.
if not st.session_state.boot_done:

    st.session_state.boot_done = True

    with st.spinner("Loading weather…"):
        fetch_weather(DEFAULT_CITY)


# Search for the requested city.
if searched and city_query.strip():

    with st.spinner(f"Fetching {city_query.strip()}…"):
        fetch_weather(city_query.strip())


# ============================================================
# WEATHER DASHBOARD
# ============================================================

weather = st.session_state.weather
weather_error = st.session_state.weather_error

# Only display this warning when parsing or fetching really failed.
if weather_error:
    st.warning(
        f"**Couldn't load weather.** {weather_error}\n\n"
        "Check the city name and your OpenWeather API key, then try again."
    )

if weather:

    icon, gradient_light, gradient_dark = condition_style(
        weather["condition"]
    )

    gradient = (
        gradient_dark
        if st.session_state.dark
        else gradient_light
    )

    badge_text, badge_class = temp_badge(weather["temp"])

    wind = weather.get("wind")

    wind_html = (
        f'<div class="wx-stat"><span>Wind speed</span>'
        f'<b>{wind:.1f} m/s</b></div>'
        if wind is not None
        else ""
    )

    st.markdown(
        f"""
<div class="wx-card" style="background:{gradient};">
  <div class="wx-top">
    <div>
      <div class="wx-city">📍 {weather['city']}</div>
      <div class="wx-cond">{weather['condition']}</div>
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
        <em class="badge {badge_class}" style="font-style:normal">
          {badge_text}
        </em>
      </b>
    </div>

    <div class="wx-stat">
      <span>Temperature analysis</span>
      <b class="txt">{weather['analysis']}</b>
    </div>

    {wind_html}
  </div>

  <div class="wx-foot">
    Last updated {weather['updated'].strftime('%I:%M:%S %p')}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh weather", key="refresh"):

        with st.spinner("Refreshing…"):
            fetch_weather(weather["city"])

        st.rerun()

elif not weather_error:

    st.markdown(
        '<div class="wx-empty">'
        'Search a city above or ask the assistant to see live weather here.'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# CHAT
# ============================================================

chat = st.session_state.chats[
    st.session_state.current
]

if not chat["messages"]:

    st.markdown(
        '<div class="empty-chat">💡 Try one of these to get started</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(2)

    for index, question in enumerate(SUGGESTIONS):

        if columns[index % 2].button(
            question,
            key=f"sugg_{index}",
            use_container_width=True,
        ):
            st.session_state.pending = question
            st.rerun()


# Display existing chat messages.
for message in chat["messages"]:

    with st.chat_message(
        message["role"],
        avatar="🧑‍💻" if message["role"] == "user" else "🌤️",
    ):
        st.markdown(message["content"])


# Chat input.
typed = st.chat_input(
    "Ask about the weather or anything else…"
)

prompt = typed or st.session_state.pending
st.session_state.pending = None


# ============================================================
# PROCESS CHAT MESSAGE
# ============================================================

if prompt:

    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    reply = ""
    new_weather = None
    success = False

    with st.chat_message("assistant", avatar="🌤️"):

        slot = st.empty()

        slot.markdown(
            '<div class="loader">'
            '<div class="dots">'
            '<span></span><span></span><span></span>'
            '</div>Thinking…</div>',
            unsafe_allow_html=True,
        )

        try:

            reply, new_weather = run_agent(
                prompt,
                chat,
            )

            slot.markdown(reply)

            success = True

        except Exception as exc:

            error_text = str(exc)

            if "429" in error_text or "quota" in error_text.lower():

                hint = (
                    "The AI service is rate-limited right now. "
                    "Wait a moment and try again."
                )

            elif (
                "api key" in error_text.lower()
                or "401" in error_text
                or "403" in error_text
            ):

                hint = (
                    "An API key looks invalid or missing. "
                    "Check your environment variables or Streamlit Secrets."
                )

            else:

                hint = (
                    "Something went wrong while contacting the agent. "
                    "Please try again."
                )

            slot.error(f"**Request failed.** {hint}")

            with st.expander("Technical details"):
                st.code(error_text)


    # Save successful messages.
    if success:

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

        # Update the dashboard if the agent returned weather data.
        if new_weather:

            st.session_state.weather = new_weather
            st.session_state.weather_error = None

        st.rerun()

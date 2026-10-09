import os
import requests
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENWEATHER_API_KEY:
    raise ValueError(
        "OPENWEATHER_API_KEY is not set in the .env file."
    )

if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError(
        "GOOGLE_API_KEY is not set in the .env file."
    )


# ============================================================
# 2. LANGSMITH CONFIGURATION
# ============================================================

os.environ.setdefault(
    "LANGSMITH_TRACING",
    "true"
)

os.environ.setdefault(
    "LANGSMITH_PROJECT",
    "weather_assistant"
)


# ============================================================
# 3. WEATHER TOOL
# ============================================================

@tool
def get_weather(city: str) -> str:
    """
    Get the current weather of a specific city.

    Use this tool only when the user asks about:
    - weather
    - temperature
    - climate
    - current weather conditions
    """

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10,
        )

        data = response.json()

    except requests.RequestException as e:
        return f"Could not reach weather service: {e}"

    if response.status_code != 200:
        return (
            f"Weather API error: "
            f"{data.get('message', 'Unknown error')}"
        )

    try:
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        condition = data["weather"][0]["description"]
    except (KeyError, IndexError):
        return "Weather API returned an unexpected response."

    # Temperature analysis
    if temp >= 30:
        analysis = "It is hot."
    elif temp >= 15:
        analysis = "The temperature is moderate."
    else:
        analysis = "It is cold."

    return (
        f"City: {city}\n"
        f"Temperature: {temp}°C\n"
        f"Feels like: {feels_like}°C\n"
        f"Condition: {condition}\n"
        f"Humidity: {humidity}%\n"
        f"Analysis: {analysis}"
    )


# List of tools
tools = [get_weather]


# ============================================================
# 4. GEMINI MODEL
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0,
)

llm_with_tools = llm.bind_tools(tools)


# ============================================================
# 5. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a helpful weather assistant.

If the user asks about:

- weather
- temperature
- climate
- current weather conditions

for a specific city, you MUST use the get_weather tool.

For questions that are not related to weather,
answer normally using the language model.

Do not use the weather tool for unrelated questions.

After receiving the weather information from the tool,
explain it clearly and naturally to the user.
"""


# ============================================================
# 6. ASSISTANT NODE
# ============================================================

def assistant(state: MessagesState):
    """
    Main assistant node.

    The model decides whether it needs to call
    the weather tool.
    """

    messages = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]

    messages.extend(state["messages"])

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }


# ============================================================
# 7. CREATE LANGGRAPH
# ============================================================

builder = StateGraph(MessagesState)


# Add assistant node
builder.add_node(
    "assistant",
    assistant
)


# Add tool node
builder.add_node(
    "tools",
    ToolNode(tools)
)


# ============================================================
# 8. GRAPH EDGES
# ============================================================

# START → Assistant
builder.add_edge(
    START,
    "assistant"
)


# Assistant → Tool OR END
builder.add_conditional_edges(
    "assistant",
    tools_condition
)


# Tool → Assistant
builder.add_edge(
    "tools",
    "assistant"
)


# ============================================================
# 9. COMPILE GRAPH
# ============================================================

graph = builder.compile()


# ============================================================
# 10. EXPOSE GRAPH TO LANGGRAPH SERVER
# ============================================================

# langgraph.json points to this variable:
#
# ./main.py:agent
#
# Therefore this variable MUST exist.

agent = graph
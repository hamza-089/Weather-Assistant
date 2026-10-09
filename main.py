
import os
import requests
import streamlit as st
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES AND STREAMLIT SECRETS
# ============================================================

load_dotenv()


def get_secret(key: str):
    """
    Read an API key from environment variables or Streamlit Secrets.

    Environment variables take priority, allowing local .env
    configuration and deployment environment variables.
    """

    value = os.getenv(key)

    if value:
        return value

    try:
        value = st.secrets.get(key)
        return str(value) if value else None
    except Exception:
        # Streamlit Secrets may not be configured during local runs.
        return None


OPENWEATHER_API_KEY = get_secret("OPENWEATHER_API_KEY")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")


if not OPENWEATHER_API_KEY:
    raise ValueError(
        "OPENWEATHER_API_KEY is missing. "
        "Add it to your local .env file or Streamlit Secrets."
    )

if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY is missing. "
        "Add it to your local .env file or Streamlit Secrets."
    )


# Make the Google key available to the Gemini integration.
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


# ============================================================
# 2. LANGSMITH CONFIGURATION
# ============================================================

os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGSMITH_PROJECT", "weather_assistant")


# ============================================================
# 3. WEATHER TOOL
# ============================================================

@tool
def get_weather(city: str) -> str:
    """
    Get the current weather for a specific city.

    Use this tool when the user asks about:
    - Weather
    - Temperature
    - Current weather conditions
    - Humidity
    - How hot or cold a city is
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
            timeout=15,
        )

        try:
            data = response.json()
        except ValueError:
            return "The weather service returned an invalid response."

    except requests.RequestException:
        return (
            "I could not connect to the weather service. "
            "Please try again later."
        )

    if response.status_code != 200:
        message = data.get("message", "Unknown error")

        if response.status_code == 401:
            return (
                "The weather service rejected the API key. "
                "Please check your OpenWeather API configuration."
            )

        if response.status_code == 404:
            return (
                f"I could not find weather information for '{city}'. "
                "Please check the city name and try again."
            )

        return f"Weather API error: {message}"

    try:
        city_name = data.get("name", city)
        country = data.get("sys", {}).get("country", "")

        temperature = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        condition = data["weather"][0]["description"]
        wind_speed = data.get("wind", {}).get("speed")

    except (KeyError, IndexError, TypeError):
        return "The weather service returned an unexpected response."

    # Temperature analysis
    if temperature >= 30:
        analysis = "It is hot."
    elif temperature >= 15:
        analysis = "The temperature is moderate."
    else:
        analysis = "It is cold."

    location = (
        f"{city_name}, {country}"
        if country
        else city_name
    )

    result = (
        f"Current weather for {location}:\n"
        f"Temperature: {temperature}°C\n"
        f"Feels like: {feels_like}°C\n"
        f"Condition: {condition.capitalize()}\n"
        f"Humidity: {humidity}%\n"
        f"Temperature analysis: {analysis}"
    )

    if wind_speed is not None:
        result += f"\nWind speed: {wind_speed} m/s"

    return result


# ============================================================
# 4. GEMINI MODEL
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0,
)

llm_with_tools = llm.bind_tools([get_weather])


# ============================================================
# 5. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a helpful and friendly AI assistant with weather capabilities.

WEATHER QUESTIONS:
- For current weather, temperature, humidity, or current conditions
  in a specific city, you MUST use the get_weather tool.
- Do not invent weather data.
- After receiving the tool result, explain it clearly and naturally.
- If the city cannot be found or the weather service reports an error,
  explain the issue to the user.

NON-WEATHER QUESTIONS:
- Answer general questions normally using your language model.
- Do not call the weather tool for unrelated questions.

GENERAL BEHAVIOR:
- Be clear, helpful, and concise.
- Use the temperature and weather information returned by the tool.
- Do not claim that you checked current weather unless you used the tool.
"""


# ============================================================
# 6. ASSISTANT NODE
# ============================================================

def assistant(state: MessagesState):
    """
    Process conversation messages and decide whether to call a tool.
    """

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response],
    }


# ============================================================
# 7. CREATE LANGGRAPH
# ============================================================

builder = StateGraph(MessagesState)

builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode([get_weather]))


# ============================================================
# 8. GRAPH EDGES
# ============================================================

builder.add_edge(START, "assistant")

builder.add_conditional_edges(
    "assistant",
    tools_condition,
)

builder.add_edge("tools", "assistant")


# ============================================================
# 9. COMPILE GRAPH
# ============================================================

graph = builder.compile()


# ============================================================
# 10. EXPOSE GRAPH TO LANGGRAPH SERVER
# ============================================================

# If langgraph.json points to ./main.py:agent,
# this variable must exist.

agent = graph

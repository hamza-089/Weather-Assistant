# LangGraph Weather Assistant

A weather assistant built with Python, LangGraph, Google Gemini, and the OpenWeather API. It retrieves current weather information for a specific city and answers general questions through a conversational interface.

**Live Demo:** https://hamza-weather-assistant.streamlit.app/

## About the Project

I built this project to explore how AI agents can use external tools to retrieve real-time information.

The assistant uses Google Gemini to understand user questions and LangGraph to manage the conversation and tool-calling workflow. When a user asks about the weather, the agent calls a custom tool that fetches current weather data from the OpenWeather API. Gemini then uses the returned information to generate a clear response.

For questions unrelated to weather, the assistant responds directly using Gemini without calling the weather API.

The application is deployed on Streamlit Community Cloud.

## Features

* Retrieve current weather information for a city.
* Display temperature in Celsius and feels-like temperature.
* Show weather conditions and humidity.
* Classify the temperature as hot, moderate, or cold.
* Answer general questions using Gemini.
* Use LangGraph to manage the agent workflow and tool calls.
* Provide an interactive chat interface through Streamlit.
* Support secure API key configuration through environment variables and Streamlit Secrets.

## Tech Stack

| Technology      | Purpose                                                |
| --------------- | ------------------------------------------------------ |
| Python          | Core application logic                                 |
| LangGraph       | Agent workflow and tool routing                        |
| LangChain       | Integration with the language model and tools          |
| Google Gemini   | Natural-language understanding and response generation |
| OpenWeather API | Current weather data                                   |
| Streamlit       | Web interface                                          |
| Requests        | HTTP requests to the weather API                       |
| python-dotenv   | Loading environment variables locally                  |

## How It Works

The application follows a simple agent workflow:

1. The user submits a question through the Streamlit interface.
2. Gemini interprets the question and determines whether the weather tool is needed.
3. If current weather information is required, LangGraph routes the request to the weather tool.
4. The tool sends a request to the OpenWeather API and retrieves the relevant data.
5. The assistant uses the returned information to generate a natural-language response.

For general questions, Gemini responds directly without invoking the weather tool.

## Weather Information

For supported city queries, the assistant can provide:

* City name
* Current temperature
* Feels-like temperature
* Weather conditions
* Humidity
* Wind speed, when available
* A simple temperature classification

### Temperature Classification

The application uses the following temperature thresholds:

| Temperature        | Classification |
| ------------------ | -------------- |
| 30°C and above     | Hot            |
| 15°C to below 30°C | Moderate       |
| Below 15°C         | Cold           |

This classification is a simple description of temperature and is not an official weather warning.

## Project Structure

```text
langgraph-weather-assistant/
├── main.py
├── weather_ui.py
├── langgraph.json
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
└── README.md
```

* `main.py` contains the LangGraph workflow, Gemini configuration, and weather tool.
* `weather_ui.py` contains the Streamlit user interface.
* `langgraph.json` contains the LangGraph configuration.
* `pyproject.toml` defines the project metadata and dependencies.
* `uv.lock` records the resolved dependency versions.
* `.python-version` specifies the intended Python version.
* `.gitignore` identifies files that should not be tracked by Git.

## Getting Started

### Prerequisites

Before running the project locally, make sure you have:

* Python installed
* Git installed
* A Google Gemini API key
* An OpenWeather API key

### 1. Clone the Repository

```bash
git clone https://github.com/hamza-089/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace `YOUR_REPOSITORY` with the actual name of your GitHub repository.

### 2. Install Dependencies

This project includes `pyproject.toml` and `uv.lock`, so you can use `uv` to install the dependencies:

```bash
uv sync
```

If you do not have `uv` installed, follow its official installation instructions: https://docs.astral.sh/uv/

### 3. Configure Environment Variables

Create a `.env` file in the project's root directory and add your API keys:

```env
GOOGLE_API_KEY=your_google_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

Replace the example values with your actual API keys.

Keep this file private. Do not upload it to GitHub.

### 4. Run the Application

Start the Streamlit interface:

```bash
uv run streamlit run weather_ui.py
```

Alternatively, activate your virtual environment and run:

```bash
streamlit run weather_ui.py
```

Streamlit will display a local URL where you can access the application.

## Deployment

The application is deployed using Streamlit Community Cloud.

**Live Application:** https://hamza-weather-assistant.streamlit.app/

To deploy your own instance:

1. Push your project to a GitHub repository.
2. Open Streamlit Community Cloud.
3. Create a new app and connect your GitHub repository.
4. Select the appropriate branch.
5. Set `weather_ui.py` as the main file.
6. Open the app's settings and navigate to **Secrets**.
7. Add your API keys in TOML format:

```toml
GOOGLE_API_KEY = "your_google_api_key"
OPENWEATHER_API_KEY = "your_openweather_api_key"
```

8. Save the secrets and deploy the application.

The variable names must match those used in your Python code. Do not commit API keys or your local `.env` file.

## API Configuration

### Google Gemini

Gemini is responsible for understanding questions, deciding when to use tools, and generating responses.

Get a Google Gemini API key from: https://aistudio.google.com/apikey

### OpenWeather

The OpenWeather API supplies the current weather data used by the assistant.

Get an API key from: https://openweathermap.org/api

Both services must be configured correctly for the corresponding features to work.

## Example Questions

You can try questions such as:

* What is the current weather in Lahore?
* What is the temperature in London?
* What is the humidity in Dubai?
* Does it feel hot in Karachi today?
* What is the difference between weather and climate?
* What is artificial intelligence?
* How does LangGraph work?

Weather-related questions use the weather tool, while general questions are answered directly by Gemini.

## Limitations

* Weather data depends on the availability and accuracy of the OpenWeather API.
* The current implementation retrieves current conditions rather than a multi-day forecast.
* City names must be recognized by the weather service.
* Gemini model availability depends on the configured model and API access.
* The temperature classification uses simple thresholds and does not account for all factors affecting how weather feels.

## Future Improvements

Some features I would like to explore in future versions include:

* Multi-day weather forecasts
* Weather comparisons between cities
* Better handling of ambiguous city names
* Conversation memory
* More detailed weather summaries
* Improved error handling and user feedback

## Author

**Hamza**

* GitHub: https://github.com/hamza-089
* Live Project: https://hamza-weather-assistant.streamlit.app/

---

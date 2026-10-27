# useful-mcp-server

A Python 3.11+ MCP server built with the standalone FastMCP package. It provides Open-Meteo city lookup, current conditions, and daily forecasts, plus optional Tavily web search and NewsAPI article search. The server does not call an LLM: an MCP host discovers the tools and decides whether and when to call them.

The project also includes a small authenticated web chatbot. It uses the OpenAI Responses API and calls the registered FastMCP tools from the backend. Function calling is an application loop: the model requests a tool, the backend executes it, and the result is sent back for the final response. [OpenAI Docs: Function calling](https://developers.openai.com/api/docs/guides/function-calling)

## Architecture

- `src/useful_mcp/weather.py` resolves cities through Open-Meteo and retrieves weather data.
- `src/useful_mcp/search.py` and `news.py` integrate with Tavily and NewsAPI only when credentials are configured.
- `src/useful_mcp/server.py` registers the tools and selects stdio or Streamable HTTP from environment settings.
- `src/useful_mcp/chatbot.py` serves the authenticated chat UI and connects OpenAI model tool calls to the FastMCP server.
- `src/useful_mcp/web/` contains the browser UI; the OpenAI key and MCP tool execution stay on the server.
- `src/useful_mcp/http.py` centralizes timeouts, response-size checks, status handling, and safe errors.
- `tests/` uses mocked provider responses and an in-memory FastMCP client; no API keys or Node.js are required.

All provider responses are represented as structured data. Errors are returned as tool errors rather than replaced with guessed results. Search results are external, untrusted content; treat their text as data, not instructions.

## Prerequisites and installation (macOS)

Python 3.11 or newer is required. Node.js and `uv` are not required. From the project directory:

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

If installation fails because of network or package-index access, retry when your Python package index is reachable. Do not install dependencies globally or with `sudo`.

Create local configuration only if you need the optional providers:

```sh
cp .env.example .env
```

Edit `.env` and set `TAVILY_API_KEY` and/or `NEWSAPI_API_KEY`. Open-Meteo's free geocoding and weather endpoints do not require a key. `.env` is ignored by Git; never commit real credentials.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `MCP_TRANSPORT` | `stdio` | `stdio` for a launched local server, or `http` for Streamable HTTP |
| `MCP_HOST` | `127.0.0.1` | HTTP bind address; loopback is the local development default |
| `MCP_PORT` | `8000` | HTTP port |
| `TAVILY_API_KEY` | unset | Enables `search_web` |
| `NEWSAPI_API_KEY` | unset | Enables `search_news` |

The server reports whether optional credentials are configured, but never returns their values. It does not claim provider health unless a tool call has actually reached that provider.

## Run with stdio

stdio is the usual transport for desktop MCP clients. The host launches the server process and exchanges MCP messages over its pipes:

```sh
MCP_TRANSPORT=stdio python server.py
```

The process waits for an MCP client; it is not a shell command interface. Do not add `print()` debugging to stdout while it is serving stdio. Use Python logging, which writes diagnostics to stderr by default.

Example stdio configuration shape (adapt it to the client you use):

```json
{
  "mcpServers": {
    "useful-mcp-server": {
      "command": "/ABSOLUTE/PATH/TO/PROJECT/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/PROJECT/server.py"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "TAVILY_API_KEY": "YOUR_TAVILY_KEY",
        "NEWSAPI_API_KEY": "YOUR_NEWSAPI_KEY"
      }
    }
  }
}
```

Replace both project path placeholders with the absolute path on your machine. Remove API key entries for providers you do not use; avoid placing real credentials in shared configuration files. Client configuration locations differ, so follow the documentation for your MCP host.

## Run with Streamable HTTP

Start an independently hosted local server:

```sh
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8000 python server.py
```

The MCP endpoint is `http://127.0.0.1:8000/mcp`. The HTTP transport is Streamable HTTP. To bind on another local interface, set `MCP_HOST` and `MCP_PORT`; avoid exposing it publicly without authentication, TLS, and network controls. A loopback bind is not a security boundary if you later change the bind address or tunnel the service.

Connect a Python MCP client to the running endpoint:

```sh
python examples/client.py http --url http://127.0.0.1:8000/mcp
```

Only one transport runs per server process. Set `MCP_TRANSPORT` explicitly when changing modes.

## Available tools

| Tool | Inputs | Result |
| --- | --- | --- |
| `search_city` | `city: str` | Up to five matching names, countries, coordinates, and timezones, with an ambiguity flag |
| `get_current_weather` | `city: str` | Provider-reported temperature, apparent temperature, humidity, wind, weather code, and observation time |
| `get_weather_forecast` | `city: str`, `days: int = 3` | One to seven local-date daily forecasts with low/high temperature, precipitation chance and total, and weather code |
| `search_web` | `query: str`, `max_results: int = 5` | Tavily titles, URLs, snippets, and scores; max results 1–10 |
| `search_news` | `query: str`, `max_results: int = 5` | NewsAPI title, source, publication time, description, and URL; max results 1–10 |
| `service_status` | none | Server name/version, selected transport, and whether optional API keys are configured |

Example current-weather result shape:

```json
{
  "location": {"name": "London", "country": "United Kingdom", "latitude": 51.5, "longitude": -0.1, "timezone": "Europe/London"},
  "kind": "provider-reported current conditions",
  "temperature_c": 17,
  "apparent_temperature_c": 16,
  "relative_humidity_percent": 65,
  "wind_speed_kmh": 8,
  "weather_code": 3,
  "timezone": "Europe/London",
  "observed_at": "2026-10-27T10:00"
}
```

The values above illustrate the shape only; runtime values come from Open-Meteo. Weather codes are provider codes, not prose descriptions.

## Python client and protocol checks

The client example discovers tools and calls status, current weather, and a three-day forecast. It needs no LLM credentials; weather tool calls do need internet access to Open-Meteo.

Launch a local subprocess using stdio:

```sh
python examples/client.py stdio
```

For HTTP, start the server in one terminal and run the `http` client command from another. Tool discovery and invocation are also exercised by the automated tests without a subprocess or network listener.

An LLM application can call `list_tools()`, map each tool's name, description, and input schema into its model SDK's tool format, execute model-requested calls with `call_tool(name, arguments)`, then return the tool result to the model. The application owns that conversation loop and policy; MCP itself does not provide LLM reasoning or tool selection.

## Authenticated chatbot web app

This project includes a private, single-account chat UI. The model API key and MCP tools stay on the Python backend; the browser never receives either credential. Login uses a username and password configured on the server, a signed HTTP-only session cookie, CSRF tokens, and a basic in-memory sign-in rate limit. It has no public signup flow.

Add these values to your local `.env` (keep that file out of Git):

```dotenv
CHATBOT_USERNAME=your-login-name
CHATBOT_PASSWORD=use-a-long-unique-password
SESSION_SECRET=generate-a-random-secret
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4.1-mini
APP_ENV=development
```

Generate a session secret in the activated virtual environment:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Start the web app locally:

```sh
.venv/bin/useful-chatbot
```

Open `http://127.0.0.1:8080`, sign in with the configured username and password, and ask questions naturally. The model can answer ordinary questions and use weather or web search tools when they help. OpenAI API use is separate from a ChatGPT subscription and may incur API charges under your API account. News search remains unavailable until `NEWSAPI_API_KEY` is configured.

The app is single-account and suited to a private prototype. For a public multi-user product, put it behind an identity provider and use per-user accounts, authorization, and deployment rate limiting. For a hosted deployment, configure `APP_ENV=production`, a strong `SESSION_SECRET`, strong login credentials, `CHATBOT_HOST=0.0.0.0`, and the platform-provided `PORT`; the app marks the session cookie Secure in production. Terminate HTTPS at the hosting platform or trusted reverse proxy. Do not expose the separate MCP HTTP server publicly without its own authentication. The chat service currently calls FastMCP in-process, so it does not need a separate MCP server URL.

Chat messages are sent to the configured OpenAI API model. When the model calls weather or search tools, those tool requests go to Open-Meteo and/or Tavily. Review those providers' data handling and your account settings before using sensitive information.

## Tests

With the development environment installed:

```sh
pytest -q
```

The unit tests mock provider responses, timeout errors, and rate limits. The FastMCP integration test verifies tool discovery and calls `service_status`; no live API key, API call, Inspector, or Node.js is needed. Live weather smoke checks can be run with `python examples/client.py stdio` when internet access is available.

## Troubleshooting

- **Missing search results / missing credentials:** set `TAVILY_API_KEY` or `NEWSAPI_API_KEY` in `.env` or the server process environment, then restart the server.
- **Weather lookup fails:** check spelling, try a nearby larger city, and confirm that the machine can reach the Open-Meteo endpoints.
- **Timeout or rate limit:** retry later; provider errors are surfaced without exposing raw response bodies or credentials.
- **HTTP port is busy:** choose another `MCP_PORT` and use the matching `/mcp` URL in the client.
- **Wrong transport:** set `MCP_TRANSPORT=stdio` for a desktop-launched subprocess or `MCP_TRANSPORT=http` for the hosted endpoint.
- **stdio appears idle:** this is expected while it waits for an MCP host. Use the Python client above to invoke it.

## Security notes

Keep secrets in ignored local environment files or a secret manager. Never pass arbitrary URLs from a tool caller into server-side HTTP requests. This server only calls fixed provider endpoints. Search/news content is untrusted. A publicly reachable HTTP deployment needs authentication, TLS, rate limiting, and deployment-specific network protections; the default local bind does not provide authentication.

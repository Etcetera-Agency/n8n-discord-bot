# Discord n8n AI Bot

A **Discord bot** that seamlessly integrates with n8n AI Agent, enabling AI Assistant to connect with external tools, APIs, and services for your Discord server.

## Features

- **Session Management**: Maintains user conversations for 24 hours.
- **Visual Feedback**: Reaction emojis indicate processing status:
  - ⌛ : The message is being processed (removed when processing completes).
  - ✅ : The message has been answered successfully.
  - ❌ : An error occurred while processing the message.
- **Reliability**: Includes **retry logic** for webhook communication.
- **Scalability**: Supports **concurrent processing** of multiple user interactions. If your Discord channel has many users, ensure your n8n instance has sufficient performance.
- **Extensibility**: Modify the n8n workflow **without touching the bot code**.
- **Modular Architecture**: Well-organized code structure for better maintainability and extensibility.

## Architecture / How it Works

This **Discord bot** serves as an elegant bridge between Discord and n8n, enabling you to:

- **Connect** Discord users to AI assistants via n8n workflows
- Maintain conversational context with session management
- Extend bot capabilities without modifying the bot code
- **Connect** to virtually any API or service supported by n8n

The bot follows a clean separation of concerns:
- The Discord bot handles the messaging interface
- **n8n** manages the complex logic, AI interactions, and external service connections

1. When a **user mentions the bot in Discord**, the message is captured.
2. The bot **sends** the message content and user information to an **n8n webhook**.
3. **n8n processes the request** through your workflow using the AI Agent - Tool Agent node (an easy way to connect a AI assistant to tools, APIs, and services).
4. The workflow **returns a response**, which the bot sends back to the Discord channel.

## Bot-n8n Communication

The Discord bot and n8n communicate via structured JSON payloads sent to and from an n8n webhook.

### Bot Requests to n8n

The Discord bot sends structured JSON payloads to n8n for various interactions. Here are examples of the different types of requests:

#### 1. User Mention Request

When a user mentions the bot in a Discord channel:

```json
{
  "command": "mention",
  "status": "ok",
  "message": "@BotName Tell me about the weather in New York",
  "result": {},
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
}
```

#### 2. Button/Select Interaction

When a user interacts with a button or select menu:

```json
{
  "command": "button_pressed",
  "status": "ok",
  "message": "",
  "result": {
    "label": "10",
    "custom_id": "workload_button"
  },
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
}
```

#### 3. Survey Step Submission

When a user completes a step in a survey:

```json
{
  "command": "survey",
  "status": "step",
  "message": "",
  "result": {
    "stepName": "workload_today", // or other step names like "day_off_nextweek"
    "value": 20, // Example value for workload/connects
    "daysSelected": ["YYYY-MM-DD", "YYYY-MM-DD"] // Example value for day off
  },
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
}
```

#### 4. Survey Completion

When a user completes all steps in a survey:

```json
{
  "command": "survey",
  "status": "end",
  "message": "",
  "result": {
    "stepName": "dayoff_nextweek", // Example last step name
    "value": ["Понеділок", "Вівторок"] // Example result for the last step
  },
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
}
```

#### 5. Slash Command

When a user executes a slash command:

```json
{
  "command": "vacation",
  "status": "ok",
  "message": "",
  "result": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  },
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
}
```

#### 6. Connects Slash Command

When a user executes the /connects_thisweek slash command:

```json
{
  "command": "connects_thisweek",
  "status": "ok",
  "message": "",
  "result": {
    "connects": 80 // Example value
  },
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000,
  "url": "YOUR_NOTION_PAGE_URL"
}
```

### n8n Responses to Bot

n8n can respond to the bot with various structured JSON payloads. Here are examples of different response types:

#### 1. Simple Text Response

Basic response with just text:

```json
{
  "output": "The weather in New York is currently 72°F and sunny with a 10% chance of rain."
}
```

#### 2. Response with buttons or select menus

n8n can include Discord message components in its response to create interactive messages.

For buttons:

```json
{
  "output": "Please select an option:",
  "components": [
    {
      "type": 1,
      "components": [
        {
          "type": 2,
          "style": 3,
          "label": "Approve",
          "custom_id": "approve_button"
        },
        {
          "type": 2,
          "style": 4,
          "label": "Reject",
          "custom_id": "reject_button"
        }
      ]
    }
  ]
}
```

This follows Discord's API format for message components, where:
- `type: 1` represents an ActionRow
- `type: 2` represents a Button
- `style: 3` represents SUCCESS (green) button
- `style: 4` represents DANGER (red) button

For select menus, you would use:

```json
{
  "output": "Please choose an option:",
  "components": [
    {
      "type": 1,
      "components": [
        {
          "type": 3,
          "custom_id": "project_select",
          "placeholder": "Select a project",
          "options": [
            {
              "label": "Project A",
              "value": "project_a",
              "description": "Description for Project A"
            },
            {
              "label": "Project B",
              "value": "project_b",
              "description": "Description for Project B"
            }
          ]
        }
      ]
    }
  ]
}
```

Where `type: 3` represents a SelectMenu.

#### 3. Survey Control - Continue

Response to continue to the next step in a survey:

```json
{
  "output": "Thank you for submitting your workload for this week!",
  "survey": "continue"
}
```

When n8n includes `"survey": "continue"` in the response, the bot will:
1. Send the output message to the user in Discord
2. Automatically execute the next command in the survey sequence
3. The next command will be executed as if the user had manually run the slash command

This allows for a seamless survey experience where users answer one question at a time, and the bot automatically progresses through the survey steps based on n8n's responses.

#### 4. Survey Control - Cancel

Response to cancel a survey due to an error or invalid input:

```json
{
  "output": "Cannot write data, sorry.",
  "survey": "cancel"
}
```

#### 5. Survey Control - End (with Notion ToDo Fetching)

Response when a survey is successfully completed, potentially triggering Notion ToDo fetching:

```json
{
  "output": "Thank you for completing the survey!",
  "survey": "end",
  "url": "YOUR_NOTION_PAGE_URL"
}
```

When n8n includes `"survey": "end"` in the response:
1. The bot sends the `output` message to the user in Discord.
2. If the `url` field is also present, the bot uses this URL with the `services/Notion_todos.py` script to fetch unchecked ToDo tasks created within the last 14 days from the specified Notion page.
3. If tasks are found, they are sent as a separate message to the Discord channel. If fetching fails (e.g., invalid `NOTION_TOKEN` environment variable, API error), a fallback message ("Дякую. \nЧудового дня!") is sent instead.

Note that currently, the bot processes the `output`, `survey`, and `url` fields from n8n responses.

### Survey Timeouts

If a user doesn't respond to a survey step within 15 minutes (900 seconds), the survey will automatically time out. When this happens:

1. The bot sends a notification to n8n with `"status": "incomplete"` and a list of the remaining steps:

```json
{
  "command": "survey",
  "status": "incomplete",
  "result": {
    "incompleteSteps": ["workload_nextweek", "day_off_nextweek"]
  },
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
}
```

2. The survey is immediately removed from active surveys
3. The UI components (buttons, select menus) are disabled

**Important**: Unlike other survey interactions, n8n does not need to send any control commands in response to an incomplete survey notification. The survey has already been removed by the time n8n receives the notification. Your n8n workflow can simply log the incomplete survey or take other actions like sending reminders to the user, but no response is expected or processed by the bot.

This timeout mechanism ensures that surveys don't remain active indefinitely if users abandon them.

### Starting a Survey from n8n

n8n can initiate a survey by making a POST request to the bot's `/start_survey` endpoint. This is useful for scheduling surveys or triggering them based on external events.

The request should include:

```json
{
  "userId": "123456789012345678",
  "channelId": "987654321098765432",
  "steps": ["workload_thisweek", "workload_nextweek", "day_off_nextweek"]
}
```

The request must include an Authorization header with the webhook token:
```
Authorization: Bearer YOUR_WEBHOOK_AUTH_TOKEN
```

Before starting the survey, the bot will:
1. Validate the request and check if the channel exists
2. Verify channel registration by sending a check_channel request to n8n:
```json
{
  "command": "check_channel",
  "status": "ok",
  "message": "",
  "result": {},
  "author": "system",
  "userId": "123456789012345678",
  "sessionId": "system",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
}
```
3. Create a new survey flow with the specified steps if the channel is registered
4. Send the first question to the user in the specified channel
5. Process each step as the user responds

This allows for automated survey scheduling, such as weekly workload reports or periodic check-ins.

### New Survey Implementation Details

The bot now uses a more direct approach for handling surveys:

1. When a survey is started (via the "Yes" button or through the `/start_survey` endpoint), the bot:
   - Stores the list of survey steps for the user
   - Executes the first command in the sequence directly

2. When n8n responds with `"survey": "continue"`:
   - The bot sends the output message to the user
   - The bot automatically executes the next command in the sequence
   - Each command is executed as if the user had manually run the slash command

3. This approach offers several advantages:
   - Each step uses the existing slash command implementation, ensuring consistent behavior
   - The UI is cleaner with command messages showing results and buttons being removed after use
   - Error handling is more robust as it leverages the existing command infrastructure
   - Reactions provide clear visual feedback on the status of each step

The survey flow is now:
1. User starts survey → First command runs
2. User selects option → Result shown in command message, buttons removed
3. n8n responds with "continue" → Next command runs automatically
4. Process repeats until all steps are completed

### Configuring the n8n AI Agent Node

The n8n AI Agent node can be used to process requests from the Discord bot and generate appropriate responses. This powerful node combines AI capabilities with n8n's workflow automation, allowing your bot to make intelligent decisions based on user input.

#### Basic Setup

1. Add an AI Agent node to your workflow after the Webhook node
2. Connect it to your preferred AI provider (OpenAI, Anthropic, etc.)
3. Configure the prompt to handle different types of requests from the Discord bot
4. Connect the AI Agent output to a Function node to process the response if needed

#### Workflow Structure for Surveys

For handling surveys, we recommend the following workflow structure:

```
Webhook → IF (command=survey) → IF (status=end) → Process Final Result → Respond to Webhook
                              │                  │
                              │                  └→ Process Survey Step → Respond to Webhook
                              │
                              └→ Default Response → Respond to Webhook
```

In this structure:
- The first IF node checks if the request is a survey command
- The second IF node checks if it's a final survey result or a step
- Separate nodes handle processing survey steps vs. final results

#### Sample Prompt for AI Agent Node

See the [AI_AGENT_PROMPT.md](AI_AGENT_PROMPT.md) file for a sample prompt template and available tools.

### Discord Character Limit

Keep in mind that Discord **has a 2000-character limit per message**. To ensure responses fit within this limit, configure the AI response to limit tokens accordingly.

## Getting Started

### Prerequisites

- Python 3.8+
- **Discord bot token**: Obtain one by creating an app on the [Discord Developer Portal](https://discord.com/developers/applications)
- **n8n instance** with a webhook node (Cloud or self-hosted)
- **OpenAI API key** (or another AI service provider)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/datakifr/n8n-discord-ai-bot.git
cd n8n-discord-ai-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration

Configuration is now managed through the `Config` class in `config/config.py`. Copy the `.env.example` file to `.env` and replace the placeholder values with your actual credentials:

```ini
# Discord Bot Token - Your Discord bot's token
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN

# Webhook Auth Token (optional) - Token to authenticate internal webhook requests
WEBHOOK_AUTH_TOKEN=YOUR_WEBHOOK_AUTH_TOKEN

# Notion API Token - Required for fetching ToDo tasks from Notion
NOTION_TOKEN=YOUR_NOTION_TOKEN

# Session TTL in seconds (optional, default: 86400 - 24 hours)
SESSION_TTL=86400

# Web server configuration (optional)
PORT=3000
HOST=0.0.0.0
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

The webhook authentication token in n8n is optional but highly recommended. The current implementation uses an Authorization header for authentication.

### n8n Workflow Setup

![n8n workflow](assets/n8n-workflow.png)

1. Import the provided `n8n-workflow.json` file into your n8n instance
2. Configure your OpenAI credentials and webhook authentication in n8n
3. Customize the prompt to fit your needs
4. Connect the bot to the tools you want it to access
5. Test and activate the workflow

## Running the Bot

### Running Locally

Start the bot with:

```bash
python main.py
```

The bot will initialize both the Discord client and a web server for external integrations.

### Running with Docker

The project includes a Dockerfile for easy containerization:

1. Build the Docker image:
```bash
docker build -t n8n-discord-bot .
```

2. Run the container:
```bash
docker run -p 3000:3000 --env-file .env n8n-discord-bot
```

You can also use Docker Compose for more complex setups.

## Deployment Options

The bot **can be deployed on various platforms**:
- Cloud services (AWS, GCP, Azure)
- PaaS providers (Heroku, Render.com)
- Self-hosted servers
- Docker containers

### Render.com Deployment

A [background worker service](https://render.com/docs/background-workers) like the one on Render.com is easy to set up:
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `python main.py`

![Render build and start command](assets/render-command-discord-bot-n8n.png)

Additionally, if you're using Render.com, you can easily copy and paste your .env file in the **Environment** tab.

## Interacting with the Discord Bot

Once set up, **users can interact** with the bot by **mentioning it in any channel** where it has access.
For example, here's a simple example if your bot is connected to a weather API:

```
@YourBot Tell me about the weather today
```
![Interaction with bot](assets/interaction-with-bot.png)

The bot will process the request through n8n and respond with AI-generated content.

Of course, this is just a **basic example**. Your bot can be connected to much more **useful APIs and tools** based on your needs, including all integrations available in n8n, as well as custom ones via HTTP nodes.

## Project Structure

The bot has been refactored into a modular architecture:

```
project_structure/
├── main.py                  # Entry point
├── bot.py                   # Bot setup and initialization (appears to be top-level now)
├── captain-definition       # CapRover deployment definition
├── DISCORD_AI_AGENT_PROMPT.md # Prompt template for AI Agent
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Dockerfile for containerization
├── ETCETERA_AI_AGENT_PROMPT.md # Another AI Agent prompt template
├── n8n-workflow-survey-example.json # Example n8n survey workflow
├── n8n-workflow.json        # Main n8n workflow
├── payload_examples.txt     # Examples of payloads
├── README.md                # Project README
├── requirements.txt         # Python dependencies
├── responses                # Directory for responses (purpose unclear from name alone)
├── assets/                  # Static assets (images, etc.)
├── config/                  # Configuration and constants
│   ├── __init__.py
│   ├── config.py            # Environment variables and settings
│   ├── constants.py         # Constant values
│   ├── logger.py            # Logging setup
│   └── strings.py           # String constants
├── discord_bot/             # Discord bot components
│   ├── __init__.py
│   ├── client.py            # Discord bot client
│   ├── surveyfix_tasks.md   # Survey related tasks/notes
│   ├── surveyfix_tasks2.md  # Another survey related tasks/notes
│   ├── commands/            # Command handlers
│   │   ├── __init__.py
│   │   ├── events.py        # Event handlers (messages, etc.)
│   │   ├── prefix.py        # Prefix commands (!)
│   │   ├── slash.py         # Slash commands (/)
│   │   └── survey.py        # Survey-related commands
│   └── views/               # UI components for interactions (buttons, select menus)
│       ├── __init__.py
│       ├── base.py          # Base view class
│       ├── day_off 2.py     # Day off selection view (duplicate?)
│       ├── day_off_slash.py # Day off slash command view
│       ├── day_off_survey.py # Day off survey view
│       ├── factory.py       # View factory
│       ├── generic.py       # Generic UI components
│       ├── workload_slash.py # Workload slash command view
│       └── workload_survey.py # Workload survey view
├── services/                # Core services
│   ├── __init__.py
│   ├── notion_todos.py      # Notion ToDo integration
│   ├── session.py           # Session management
│   ├── survey.py            # Survey flow management
│   └── webhook.py           # n8n webhook communication
└── web/                     # Web server for external integrations
    ├── __init__.py
    └── server.py            # HTTP/HTTPS server
```

## Contributing

// ... existing code ...

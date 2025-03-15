# Discord n8n AI Bot

A **Discord bot** that seamlessly integrates with n8n AI Agent, enabling AI Assistant to connect with external tools, APIs, and services for your Discord server.

The Python code was developed with the assistance of LLMs, specifically `Claude 3.7 Sonnet` and `o3-mini-high`.

## Overview

This **Discord bot** serves as an elegant bridge between Discord and n8n, enabling you to:

- **Connect** Discord users to AI assistants via n8n workflows
- Maintain conversational context with session management
- Extend bot capabilities without modifying the bot code
- **Connect** to virtually any API or service supported by n8n

The bot follows a clean separation of concerns:
- The Discord bot handles the messaging interface
- **n8n** manages the complex logic, AI interactions, and external service connections

## How It Works

1. When a **user mentions the bot in Discord**, the message is captured.
2. The bot **sends** the message content and user information to an **n8n webhook**.
3. **n8n processes the request** through your workflow using the AI Agent - Tool Agent node (an easy way to connect a AI assistant to tools, APIs, and services).
4. The workflow **returns a response**, which the bot sends back to the Discord channel.

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

## Project Structure

The bot has been refactored into a modular architecture:

```
project_structure/
├── main.py                  # Entry point
├── config/                  # Configuration and constants
│   ├── __init__.py
│   ├── config.py            # Environment variables and settings
│   ├── constants.py         # Constant values
│   └── logger.py            # Logging setup
├── services/                # Core services
│   ├── __init__.py
│   ├── session.py           # Session management
│   ├── survey.py            # Survey flow management
│   └── webhook.py           # n8n webhook communication
├── bot/                     # Discord bot components
│   ├── __init__.py
│   ├── client.py            # Bot setup and initialization
│   ├── commands/            # Command handlers
│   │   ├── __init__.py
│   │   ├── events.py        # Event handlers (messages, etc.)
│   │   ├── prefix.py        # Prefix commands (!)
│   │   ├── slash.py         # Slash commands (/)
│   │   └── survey.py        # Survey-related commands
│   └── views/               # UI components
│       ├── __init__.py
│       ├── base.py          # Base view class
│       ├── day_off.py       # Day off selection view
│       ├── factory.py       # View factory
│       ├── generic.py       # Generic UI components
│       └── workload.py      # Workload selection view
└── web/                     # Web server for external integrations
    ├── __init__.py
    └── server.py            # HTTP/HTTPS server
```

## Setup Instructions

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

3. Copy the `.env.example` file to `.env` and replace the placeholder values with your actual credentials:
```ini
# Discord Bot Token - Your Discord bot's token
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN

# n8n Webhook URL - The URL for your n8n webhook endpoint
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your_webhook_endpoint

# Webhook Auth Token (optional) - Token to authenticate requests to the n8n webhook
WEBHOOK_AUTH_TOKEN=YOUR_WEBHOOK_AUTH_TOKEN

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

## Configuration Options

Configuration is now managed through the `Config` class in `config/config.py`:

- **DISCORD_TOKEN**: Your Discord bot token
- **N8N_WEBHOOK_URL**: URL for your n8n webhook endpoint
- **WEBHOOK_AUTH_TOKEN**: Token for webhook authentication
- **SESSION_TTL**: Duration of user sessions in seconds (default: `86400`, i.e., 24 hours)
- **PORT**: Web server port (default: `3000`)
- **HOST**: Web server host (default: `0.0.0.0`)
- **SSL_CERT_PATH** and **SSL_KEY_PATH**: Paths to SSL certificate and key files (optional)

## Interacting with the Discord Bot

Once set up, **users can interact** with the bot by **mentioning it in any channel** where it has access.  
For example, here's a simple example if your bot is connected to a weather API:

```
@YourBot Tell me about the weather today
```
![Interaction with bot](assets/interaction-with-bot.png)

The bot will process the request through n8n and respond with AI-generated content.

Of course, this is just a **basic example**. Your bot can be connected to much more **useful APIs and tools** based on your needs, including all integrations available in n8n, as well as custom ones via HTTP nodes.

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

### CapRover Deployment

The project includes a `captain-definition` file for easy deployment on CapRover:

1. Make sure you have the CapRover CLI installed:
```bash
npm install -g caprover
```

2. Log in to your CapRover instance:
```bash
caprover login
```

3. Deploy the application:
```bash
caprover deploy
```

4. Set up the environment variables in the CapRover dashboard:
   - DISCORD_TOKEN
   - N8N_WEBHOOK_URL
   - WEBHOOK_AUTH_TOKEN
   - Any other optional configuration variables

## Discord Character Limit

Keep in mind that Discord **has a 2000-character limit per message**. To ensure responses fit within this limit, configure the AI response to limit tokens accordingly.

## Survey Control

The bot supports controlling surveys based on n8n responses. When n8n responds to a survey step, it can include a `survey` field in the response to control the flow of the survey:

```json
{
  "output": "Survey step recorded.",
  "survey": "continue"
}
```

This will display the message "Survey step recorded." and then continue to the next step in the survey.

To cancel a survey, n8n can respond with:

```json
{
  "output": "Invalid workload value. Please enter a number between 0 and 50.",
  "survey": "cancel"
}
```

This will display the message "Invalid workload value. Please enter a number between 0 and 50." and then cancel the survey, removing it from the active surveys.

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

The bot will:
1. Validate the request and check if the channel exists
2. Create a new survey flow with the specified steps
3. Send the first question to the user in the specified channel
4. Process each step as the user responds

This allows for automated survey scheduling, such as weekly workload reports or periodic check-ins.

### Example Workflow

An example n8n workflow that demonstrates the survey control feature is included in the repository as `n8n-workflow-survey-example.json`. This workflow shows how to:

1. Receive survey responses from the Discord bot
2. Validate the responses
3. Continue or cancel the survey based on the validation results
4. Process the final survey results

You can import this workflow into your n8n instance to see how it works.

## Communication Between Bot and n8n

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
    "stepName": "workload_thisweek",
    "value": 20
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
  "status": "ok",
  "message": "",
  "result": {
    "final": {
      "workload_thisweek": 20,
      "workload_nextweek": 30,
      "day_off_nextweek": ["Monday", "Tuesday"]
    }
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
    "start_day": "15",
    "start_month": "June",
    "end_day": "30",
    "end_month": "June"
  },
  "author": "User#1234",
  "userId": "123456789012345678",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "channelId": "987654321098765432",
  "channelName": "general",
  "timestamp": 1620000000
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

#### 2. Survey Control - Continue

Response to continue to the next step in a survey:

```json
{
  "output": "Thank you for submitting your workload for this week!",
  "survey": "continue"
}
```

#### 3. Survey Control - Cancel

Response to cancel a survey due to an error or invalid input:

```json
{
  "output": "Invalid workload value. Please enter a number between 0 and 50.",
  "survey": "cancel"
}
```

Note that currently, the bot only processes the `output` and `survey` fields from n8n responses.

### Current Limitations and Future Possibilities

Currently, the bot does not support receiving UI elements like buttons or select menus directly from n8n responses. The UI elements (buttons, select menus) are created by the bot itself based on predefined templates in the code.

In future versions, the bot could be extended to support dynamic UI elements from n8n responses using the Discord "components" field, which would allow for more flexible interactions. For example:

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

If you're interested in contributing this functionality, feel free to submit a pull request!

## Contributing

Contributions are welcome! Feel free to submit a Pull Request.

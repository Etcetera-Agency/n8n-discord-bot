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
  - ⌛ : The message is being processed.
  - ✅ : The message has been answered.
  - ❌ : An error occurred while processing the message.
- **Reliability**: Includes **retry logic** for webhook communication.
- **Scalability**: Supports **concurrent processing** of multiple user interactions. If your Discord channel has many users, ensure your n8n instance has sufficient performance.
- **Extensibility**: Modify the n8n workflow **without touching the bot code**.

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
```

The webhook authentication token in n8n is optional but highly recommended. The current implementation uses an Authorization header for authentication

### n8n Workflow Setup

![n8n workflow](assets/n8n-workflow.png)

1. Import the provided `n8n-workflow.json` file into your n8n instance
2. Configure your OpenAI credentials and webhook authentication in n8n
3. Customize the prompt to fit your needs
4. Connect the bot to the tools you want it to access
5. Test and activate the workflow

## Configuration Options

- **SESSION_TTL**: Duration of user sessions in seconds (default: `86400`, i.e., 24 hours).
- **max_retries**: Number of retry attempts for webhook calls (default: `3`).
- **retry_delay**: Base delay between retries in seconds (default: `1`).

## Interacting with the Discord Bot

Once set up, **users can interact** with the bot by **mentioning it in any channel** where it has access.  
For example, here’s a simple example if your bot is connected to a weather API:


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

A [background worker service](https://render.com/docs/background-workers) like the one on Render.com is easy to set up:
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `python bot.py`

![Render build and start command](assets/render-command-discord-bot-n8n.png)

Additionally, if you're using Render.com, you can easily copy and paste your .env file in the **Environment** tab.

## Discord Character Limit

Keep in mind that Discord **has a 2000-character limit per message**. To ensure responses fit within this limit, configure the AI response to limit tokens accordingly.

## Contributing

Contributions are welcome! Feel free to submit a Pull Request.

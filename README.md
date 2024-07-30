# Pippo

Pippo is a Discord bot focused on games related to movies, with an Indian touch.
### I'd prefer if you don't host it yourself, and invite the bot to your server using [this link](https://top.gg/bot/1066895131485163570)

## Table of Contents
- [Description](#description)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Usage](#usage)
- [Contributing](#contributing)

## Description

Pippo is a fun and interactive Discord bot designed to bring movie-related games to your server, enriched with an Indian cultural touch.

## Prerequisites

- Python 3.7 or higher
- PostgreSQL database
- Discord account and bot token

## Installation

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/NavSrijan/Pippo.git
cd Pippo
```

Set up a virtual environment and install the requirements:
Also, set-up a postgresql database as necessary.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a file named `token` with the following content:

```bash
#!/bin/bash

# Pippo
export tc_token=<YOUR_DISCORD_BOT_TOKEN>
export database_username=<DATABASE_USERNAME>
export database_password=<DATABASE_PASSWORD>
export db_host=<DATABASE_HOST>
export topgg=<TOPGG_TOKEN>

export production=False
```

Ensure the file is executable:

```bash
chmod +x token
```

## Running the Bot

Source the token file and run the bot:

```bash
source token
python3 bot.py
```

## Usage

Once the bot is running, invite it to your Discord server and use the available commands to start playing games. For a list of commands, type `.help` in your server.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.


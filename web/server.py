import os
import ssl
from aiohttp import web
from config import Config, logger
from services.webhook import WebhookService

async def start_survey_http(request):
    """Handle HTTP requests to start surveys"""
    auth_header = request.headers.get("Authorization")
    expected_header = f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"
    if not auth_header or auth_header != expected_header:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    try:
        data = await request.json()
        user_id = data.get("userId")
        channel_id = data.get("channelId")
        steps = data.get("steps", [])
        
        if not user_id or not channel_id or not steps:
            return web.json_response({"error": "Missing parameters"}, status=400)

        try:
            channel = await request.app['bot'].fetch_channel(int(channel_id))
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return web.json_response({"error": "Channel not found"}, status=404)
        except Exception as e:
            logger.error(f"Channel error: {e}")
            return web.json_response({"error": "Channel error"}, status=500)
            
        payload = {
            "command": "check_channel",
            "channelId": channel_id,
            "userId": user_id
        }
        
        headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
        success_check, data_check = await WebhookService.send_webhook_with_retry(
            None, payload, headers
        )
        
        if not success_check or str(data_check.get("output", "false")).lower() != "true":
            return web.json_response({"error": "Channel is not registered"}, status=403)

        await request.app['bot'].handle_start_daily_survey(user_id, channel_id, steps)
        return web.json_response({"status": "Survey started"})
    
    except Exception as e:
        logger.error(f"Error in start_survey_http: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def run_server(bot):
    """Run the HTTP/HTTPS server"""
    app = web.Application()
    app['bot'] = bot
    app.router.add_post('/start_survey', start_survey_http)
    
    port = int(Config.PORT or "3000")
    host = "0.0.0.0"
    ssl_context = None
    
    if Config.SSL_CERT_PATH and Config.SSL_KEY_PATH:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile=Config.SSL_CERT_PATH,
            keyfile=Config.SSL_KEY_PATH
        )
        logger.info(f"Starting HTTPS server on {host}:{port}")
    else:
        logger.info(f"Starting HTTP server on {host}:{port}")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
    await site.start()
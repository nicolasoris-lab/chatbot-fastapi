# Chatbot
Chatbot con FastAPI.

# Entorno virtual
## Crearlo
```bash
py -3 -m venv .venv
```

## Activarlo
```bash
.venv\Scripts\activate
```

## Desactivarlo
```bash
deactivate
```

# Instalar Dependencias
```bash
pip install -r requirements.txt
```

# Variables de Entorno
Crear archivo `.env` en base al archivo `.env.template` y agregarlas las variables necesarias.

# Ngrok
Para testear usamos ngrok.
Primero tener habilitar ngrok:
```bash
ngrok http <PUERTO>
```

Luego usas el forwarding para pobar con curl:
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=<URL_HTTPS_DE_NGROK>/telegram/webhook/<BOT_TOKEN>"
```

Si todo sale bien deberiamos ver un mensaje parecido a este:
```bash
{"ok":true,"result":true,"description":"Webhook was set"} 
```

Luego de esto ya podemos probar el bot.
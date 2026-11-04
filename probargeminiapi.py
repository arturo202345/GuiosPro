import os
from google import genai

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

for modelo in client.models.list():
    acciones = modelo.supported_actions or []

    if "generateContent" in acciones:
        print(modelo.name)
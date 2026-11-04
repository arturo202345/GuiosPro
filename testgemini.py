import os
from google import genai
from google.genai import errors

modelos = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

with genai.Client(api_key=os.environ["GEMINI_API_KEY"]) as client:
    for modelo in modelos:
        print(f"\nProbando: {modelo}")

        try:
            respuesta = client.models.generate_content(
                model=modelo,
                contents="Responde únicamente: Gemini funciona."
            )

            print("RESPUESTA:", respuesta.text)
            print("MODELO FUNCIONAL:", modelo)
            break

        except errors.APIError as error:
            print(f"Error {error.code}: {error.message}")

            if error.code in (429, 503):
                print("Cuota o disponibilidad insuficiente.")
            elif error.code == 404:
                print("Modelo no disponible.")
            else:
                break
    else:
        print("\nNingún modelo respondió correctamente.")
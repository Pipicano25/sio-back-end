import requests

def obtener_token():
    url = "http://localhost:8081/realms/sio/protocol/openid-connect/token"
    payload = {
        "grant_type": "password",
        "client_id": "sio-web",
        "username": "admin.test",
        "password": "SioTest123Sio",
        "scope": "openid"
    }
    
    try:
        respuesta = requests.post(url, data=payload, timeout=5)
        respuesta.raise_for_status()
        # Retorna solo el string del token
        return respuesta.json()["access_token"]
    except Exception as e:
        return f"Error al obtener el token: {e}"

if __name__ == "__main__":
    # Imprime limpia y únicamente el token en la terminal
    print(obtener_token())

import requests
import json

url = "http://localhost:5000/api/register"
data = {
    "prenom": "Jean",
    "email": "jean@test.com",
    "password": "test1234",
    "genre": "homme",
    "age": 25,
    "ville": "Paris"
}

try:
    response = requests.post(url, json=data)
    print("Statut:", response.status_code)
    print("Réponse:", response.json())
except Exception as e:
    print("Erreur:", e)
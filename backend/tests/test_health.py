import requests
import json
from time import sleep

def test_health_endpoint(max_retries=5):
    url = "http://localhost:8000/api/health"
    
    for attempt in range(max_retries):
        try:
            print(f"\nTentative {attempt + 1} de connexion à {url}...")
            response = requests.get(url)
            
            print(f"Status Code: {response.status_code}")
            print("Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            
            print("\nRéponse:")
            try:
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
                return True
            except json.JSONDecodeError:
                print(response.text)
            
            if response.status_code == 200:
                return True
                
        except requests.ConnectionError:
            print("❌ Connexion impossible - le serveur est-il démarré ?")
        
        if attempt < max_retries - 1:
            print("Nouvelle tentative dans 2 secondes...")
            sleep(2)
    
    return False

if __name__ == "__main__":
    print("🏥 Test de l'endpoint /api/health")
    print("=" * 50)
    
    success = test_health_endpoint()
    
    if success:
        print("\n✅ Test réussi ! L'API est en bonne santé.")
    else:
        print("\n❌ Échec du test après plusieurs tentatives.") 
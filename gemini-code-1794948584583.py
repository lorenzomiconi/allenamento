import os
import json
import datetime
from garminconnect import Garmin

def main():
    # 1. Accesso sicuro a Garmin Connect
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    
    # In un ambiente di test locale, fermiamo lo script se mancano le credenziali
    if not email or not password:
        print("Credenziali non trovate. Esecuzione simulata per la dashboard.")
        return

    client = Garmin(email, password)
    client.login()

    # 2. Prendi gli allenamenti di oggi
    oggi = datetime.date.today().isoformat()
    attivita = client.get_activities_by_date(oggi, oggi, 'running')
    
    km_corsi_oggi = 0.0
    if attivita:
        for act in attivita:
            km_corsi_oggi += act.get('distance', 0) / 1000.0

    # 3. Aggiorna il database (dati.json)
    with open('dati.json', 'r') as f:
        db = json.load(f)

    # Scala l'usura delle scarpe da lenti (Neo Zen)
    if km_corsi_oggi > 0:
        db['scarpe']['mizuno_neo_zen']['km_residui'] -= round(km_corsi_oggi, 1)

    # Segna completati gli allenamenti in calendario
    for all in db['allenamenti_settimana']:
        if all['data'] == oggi and km_corsi_oggi >= (all['km_previsti'] * 0.8):
             all['stato'] = 'completato'

    # 4. Salva il file
    with open('dati.json', 'w') as f:
        json.dump(db, f, indent=2)
        
    print(f"Aggiornamento concluso: {km_corsi_oggi} km aggiunti. JSON salvato.")

if __name__ == "__main__":
    main()
import os
import json
import datetime
from garminconnect import Garmin

def main():
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    
    if not email or not password:
        print("Credenziali non trovate. Esecuzione interrotta.")
        return

    try:
        client = Garmin(email, password)
        client.login()
    except Exception as e:
        print(f"Errore di login a Garmin: {e}")
        return

    oggi = datetime.date.today().isoformat()
    attivita = client.get_activities_by_date(oggi, oggi)
    
    km_corsa_oggi = 0.0
    km_rulli_oggi = 0.0
    fc_media_oggi = None
    passo_medio_oggi = ""

    if attivita:
        for act in attivita:
            tipo_key = act.get('activityType', {}).get('typeKey', '')
            dist_km = act.get('distance', 0) / 1000.0
            if 'running' in tipo_key:
                km_corsa_oggi += dist_km
                if act.get('averageHR'):
                    fc_media_oggi = round(act.get('averageHR'))
                durata_sec = act.get('duration', 0)
                if dist_km > 0 and durata_sec > 0:
                    sec_km = durata_sec / dist_km
                    m = int(sec_km // 60)
                    s = int(round(sec_km % 60))
                    passo_medio_oggi = f"{m}'{s:02d}\"/km"
            elif 'cycling' in tipo_key:
                km_rulli_oggi += dist_km

    with open('dati.json', 'r', encoding='utf-8') as f:
        db = json.load(f)

    scarpa_usata = "Mizuno Neo Zen"
    for seduta in db['allenamenti_settimana']:
        if seduta['data'] == oggi:
            if km_corsa_oggi > 0:
                if seduta.get('scarpa') and seduta['scarpa'] != '-':
                    scarpa_usata = seduta['scarpa']
                seduta['km_fatti'] = round(km_corsa_oggi, 2)
                seduta['passo'] = passo_medio_oggi
                if fc_media_oggi:
                    seduta['note'] = f"Sync Garmin: FC media {fc_media_oggi} bpm"
                if km_corsa_oggi >= (seduta['km_previsti'] * 0.8):
                    seduta['stato'] = 'completato'
            if km_rulli_oggi > 0:
                seduta['km_rulli'] = round(km_rulli_oggi, 1)
                seduta['stato'] = 'completato'

    if km_corsa_oggi > 0 and isinstance(db.get('scarpe'), list):
        for s in db['scarpe']:
            if s['nome'] == scarpa_usata:
                s['km_percorsi'] = round(s['km_percorsi'] + km_corsa_oggi, 1)
                break
        else:
            db['scarpe'][0]['km_percorsi'] = round(db['scarpe'][0]['km_percorsi'] + km_corsa_oggi, 1)

    with open('dati.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        
    print(f"Aggiornamento concluso: {km_corsa_oggi:.2f} km corsa, {km_rulli_oggi:.1f} km rulli.")

if __name__ == "__main__":
    main()

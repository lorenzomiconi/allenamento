import os
import json
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from garminconnect import Garmin

def main():
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    fb_creds_raw = os.environ.get("FIREBASE_CREDENTIALS")
    fb_uid = os.environ.get("FIREBASE_USER_UID")

    if not email or not password or not fb_creds_raw or not fb_uid:
        print("Secrets Garmin o Firebase mancanti. Esecuzione interrotta.")
        return

    # 1. Connessione privata a Firestore
    cred_dict = json.loads(fb_creds_raw)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    fs = firestore.client()

    doc_ref = fs.collection("users").document(fb_uid)
    doc = doc_ref.get()
    if not doc.exists:
        print("Documento utente non trovato su Firestore.")
        return
    db = doc.to_dict()

    # 2. Accesso a Garmin Connect
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

    # 3. Aggiornamento seduta e usura scarpe nel cloud
    scarpa_usata = None
    for seduta in db.get('allenamenti_settimana', []):
        if seduta.get('data') == oggi:
            if km_corsa_oggi > 0:
                if seduta.get('scarpa') and seduta['scarpa'] != '-':
                    scarpa_usata = seduta['scarpa']
                seduta['km_fatti'] = round(km_corsa_oggi, 2)
                seduta['passo'] = passo_medio_oggi
                if fc_media_oggi:
                    seduta['note'] = f"Sync Garmin: FC media {fc_media_oggi} bpm"
                if km_corsa_oggi >= (seduta.get('km_previsti', 0) * 0.8):
                    seduta['stato'] = 'completato'
            if km_rulli_oggi > 0:
                seduta['km_rulli'] = round(km_rulli_oggi, 1)
                seduta['stato'] = 'completato'

    if km_corsa_oggi > 0 and isinstance(db.get('scarpe'), list) and db['scarpe']:
        target_shoe = next((s for s in db['scarpe'] if s['nome'] == scarpa_usata), db['scarpe'][0])
        target_shoe['km_percorsi'] = round(target_shoe['km_percorsi'] + km_corsa_oggi, 1)

    doc_ref.set(db)
    print(f"Sync Firebase completato: {km_corsa_oggi:.2f} km corsa, {km_rulli_oggi:.1f} km rulli.")

if __name__ == "__main__":
    main()

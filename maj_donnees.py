"""Lit le document Grist, garde les activités validées et écrit data.json pour l'agenda public."""
import json, os, urllib.request, datetime

SERVEUR = os.environ.get("GRIST_SERVER", "https://grist.numerique.gouv.fr")
DOC = os.environ["GRIST_DOC_ID"]
CLE = os.environ["GRIST_API_KEY"]

# Colonnes internes à ne pas publier
A_RETIRER = {"Statut", "Controle", "ID", "manualSort", "Latitude", "Longitude"}


def api(chemin):
    req = urllib.request.Request(f"{SERVEUR}/api/docs/{DOC}{chemin}",
                                 headers={"Authorization": f"Bearer {CLE}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def en_colonnes(records, garder=None):
    """Transforme la liste de lignes de l'API en colonnes (même format que dans Grist)."""
    cols = {"id": []}
    noms = sorted({k for r in records for k in r["fields"]})
    for n in noms:
        cols[n] = []
    for r in records:
        if garder and not garder(r["fields"]):
            continue
        cols["id"].append(r["id"])
        for n in noms:
            cols[n].append(r["fields"].get(n))
    return cols


tables = {}
for t in api("/tables")["tables"]:
    tid = t["id"]
    if "_summary" in tid:
        continue
    records = api(f"/tables/{tid}/records")["records"]
    if not records:
        continue
    champs = records[0]["fields"]
    if "Jours" in champs and "Heure_de_debut" in champs:          # table des activités
        cols = en_colonnes(records, lambda f: f.get("Statut") in (None, "Validé"))
        for c in A_RETIRER:
            cols.pop(c, None)
        tables[tid] = cols
    elif "Nom_du_lieu" in champs:                                   # table des lieux
        tables[tid] = en_colonnes(records)
    elif "Du" in champs and "Au" in champs:                         # table des fermetures
        tables[tid] = en_colonnes(records)

if not any("Jours" in c for c in tables.values()):
    raise SystemExit("Table des activités introuvable : rien n'a été écrit.")

maj = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
with open("data.json", "w", encoding="utf-8") as f:
    json.dump({"maj": maj, "tables": tables}, f, ensure_ascii=False, separators=(",", ":"))
print("data.json écrit :", {k: len(v["id"]) for k, v in tables.items()})

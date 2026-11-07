import os
import json
import time
import pandas as pd

debut_programme = time.perf_counter()
os.makedirs("output", exist_ok=True)

journal = []      
resultats = []    

def noter(message):
    print(message)
    journal.append(message)

def afficher(message):
    print(message)
    resultats.append(message)


def nouvelle_etape(titre, explication):
    """Affiche le titre de l'étape et, en mode pas à pas, attend la touche Entrée."""
    print("\n" + "=" * 60)
    print(titre)
    print(explication)
    print("=" * 60)
    if mode_pas_a_pas:
        input("Appuie sur Entrée pour lancer cette étape...")

print("=== ANALYSE COMPARATIVE DE MARCHE ===")
print("1 - Exécuter tout le programme d'un coup")
print("2 - Exécuter pas à pas (une étape à la fois, avec explications)")
choix = input("Ton choix (1 ou 2) : ")

if choix == "2":
    mode_pas_a_pas = True
else:
    mode_pas_a_pas = False

def nettoyer_nombre(valeur):
    texte = str(valeur).replace("FCFA", "").replace(" ", "")
    texte = texte.replace("\xa0", "").replace("\u202f", "")
    if texte == "nan":
        return None
    try:
        return float(texte)
    except ValueError:
        return None

def nettoyer_colonne(valeurs, remplacement):
    """Convertit chaque valeur en nombre.
    Si elle est vide, illisible ou négative -> remplacement.
    Renvoie la liste nettoyée et le nombre de valeurs remplacées."""
    valeurs_nettoyees = []
    nb_remplaces = 0
    for valeur in valeurs:
        nombre = nettoyer_nombre(valeur)
        if nombre is None or nombre < 0:
            nombre = remplacement
            nb_remplaces += 1
        valeurs_nettoyees.append(nombre)
    return valeurs_nettoyees, nb_remplaces

nouvelle_etape("ETAPE 1 : CHARGEMENT",
               "On lit les 3 fichiers des enseignes (CSV, JSON, Excel) et le catalogue.")

df_lagune = pd.read_csv("data/marche_lagune.csv", sep=";")

with open("data/baobab_shop.json", "r", encoding="utf-8") as fichier:
    data_baobab = json.load(fichier)
df_baobab = pd.json_normalize(data_baobab["items"])

df_comptoir = pd.read_excel("data/comptoir_ivoire.xlsx", header=2) 
df_catalogue = pd.read_csv("data/catalogue_reference.csv")

print("Lignes chargées : Lagune", len(df_lagune), "| Baobab", len(df_baobab),
      "| Comptoir", len(df_comptoir), "| Catalogue", len(df_catalogue))

nouvelle_etape("ETAPE 2 : NETTOYAGE",
               "On convertit les prix en nombres, on supprime les doublons, et on note chaque "
               "problème dans le journal. On calcule aussi le prix réellement payé et la disponibilité.")

avant = len(df_lagune)
df_lagune = df_lagune.drop_duplicates(subset=["reference"])
noter("Lagune : " + str(avant - len(df_lagune)) + " doublons supprimés")

prix_lagune, nb_remplaces = nettoyer_colonne(df_lagune["prix"].tolist(), None)
noter("Lagune : " + str(nb_remplaces) + " prix invalides")
statuts_lagune = df_lagune["disponibilite"].str.strip().tolist()

disponibilites_lagune = []
for i in range(len(prix_lagune)):
    disponibilites_lagune.append(
        prix_lagune[i] is not None and prix_lagune[i] > 0 and statuts_lagune[i] != "Rupture")

df_lagune["prix_final"] = prix_lagune
df_lagune["disponible"] = disponibilites_lagune
noter("Lagune : " + str(disponibilites_lagune.count(False)) + " articles indisponibles")
print("Disponibilités Lagune :", df_lagune["disponibilite"].unique())

# ---- Baobab Shop : le client paie montant + frais de livraison
avant = len(df_baobab)
df_baobab = df_baobab.drop_duplicates(subset=["sku"])
noter("Baobab : " + str(avant - len(df_baobab)) + " doublons supprimés")

montants, nb_remplaces = nettoyer_colonne(df_baobab["pricing.amount"].tolist(), None)
noter("Baobab : " + str(nb_remplaces) + " montants invalides")
frais_livraison, nb_remplaces = nettoyer_colonne(df_baobab["pricing.delivery_fee"].tolist(), 0)
noter("Baobab : " + str(nb_remplaces) + " frais invalides remplacés par 0")
stocks, nb_remplaces = nettoyer_colonne(df_baobab["stock"].tolist(), 0)
noter("Baobab : " + str(nb_remplaces) + " stocks invalides remplacés par 0")

prix_finaux_baobab = []
disponibilites_baobab = []
for i in range(len(montants)):
    if montants[i] is not None and montants[i] > 0:
        prix_finaux_baobab.append(montants[i] + frais_livraison[i])
        disponibilites_baobab.append(stocks[i] > 0)
    else:
        prix_finaux_baobab.append(None)
        disponibilites_baobab.append(False)

df_baobab["prix_final"] = prix_finaux_baobab
df_baobab["disponible"] = disponibilites_baobab
noter("Baobab : " + str(disponibilites_baobab.count(False)) + " articles indisponibles")
print("Devises Baobab :", df_baobab["pricing.currency"].unique())

avant = len(df_comptoir)
df_comptoir = df_comptoir.dropna(how="all")
noter("Comptoir : " + str(avant - len(df_comptoir)) + " lignes vides supprimées")

prix_catalogue, nb_remplaces = nettoyer_colonne(df_comptoir["Prix catalogue (FCFA)"].tolist(), None)
noter("Comptoir : " + str(nb_remplaces) + " prix catalogue invalides")
remises, nb_remplaces = nettoyer_colonne(df_comptoir["Remise (%)"].tolist(), 0)
noter("Comptoir : " + str(nb_remplaces) + " remises invalides remplacées par 0")
quantites_rayon, nb_remplaces = nettoyer_colonne(df_comptoir["Quantité en rayon"].tolist(), 0)
noter("Comptoir : " + str(nb_remplaces) + " quantités invalides remplacées par 0")

prix_finaux_comptoir = []
disponibilites_comptoir = []
nb_remises_trop_hautes = 0
for i in range(len(prix_catalogue)):
    remise = remises[i]
    if remise > 100:
        remise = 0
        nb_remises_trop_hautes += 1
    if prix_catalogue[i] is None:
        prix_finaux_comptoir.append(None)
        disponibilites_comptoir.append(False)
    else:
        prix_final = prix_catalogue[i] * (1 - remise / 100)
        prix_finaux_comptoir.append(prix_final)
        disponibilites_comptoir.append(prix_final > 0 and quantites_rayon[i] > 0)

df_comptoir["prix_final"] = prix_finaux_comptoir
df_comptoir["disponible"] = disponibilites_comptoir
noter("Comptoir : " + str(nb_remises_trop_hautes) + " remises supérieures à 100 remplacées par 0")
noter("Comptoir : " + str(disponibilites_comptoir.count(False)) + " articles indisponibles")

nouvelle_etape("ETAPE 3 : RAPPROCHEMENT",
               "On associe chaque article à un produit_id du catalogue grâce à la table de mots-clés.")

identifiants_catalogue = df_catalogue["produit_id"].tolist()
noms_catalogue = df_catalogue["nom"].tolist()

for i in range(len(identifiants_catalogue)):
    print(identifiants_catalogue[i], "|", noms_catalogue[i])
print("LAGUNE :", df_lagune["designation"].tolist())
print("BAOBAB :", df_baobab["title"].tolist())
print("COMPTOIR :", df_comptoir["Article"].tolist())

mots_cles = {
    "P04": ["tecno", "spark", "20"],
    "P12": ["lenovo", "ideapad", "3"]
}

def rapprocher(liste_noms, nom_enseigne):
    """Renvoie la liste des produit_id (un par article), ou NON_RAPPROCHE."""
    identifiants = []
    for nom in liste_noms:
        produits_trouves = []
        for produit_id, mots_du_produit in mots_cles.items():
            if all(mot in str(nom).lower() for mot in mots_du_produit):
                produits_trouves.append(produit_id)

        if len(produits_trouves) == 1:
            identifiants.append(produits_trouves[0])
        else:
            identifiants.append("NON_RAPPROCHE")
            noter(nom_enseigne + " : non rapproché -> " + str(nom))
    return identifiants


df_lagune["produit_id"] = rapprocher(df_lagune["designation"].tolist(), "Lagune")
df_baobab["produit_id"] = rapprocher(df_baobab["title"].tolist(), "Baobab")
df_comptoir["produit_id"] = rapprocher(df_comptoir["Article"].tolist(), "Comptoir")

nouvelle_etape("ETAPE 4 : COMPARATIF",
               "Pour chaque produit présent dans au moins 2 enseignes : prix, enseigne la moins chère "
               "et écart. Le tableau est exporté dans output/comparatif.csv.")

enseignes = ["Lagune", "Baobab", "Comptoir"]
tableaux_enseignes = [df_lagune, df_baobab, df_comptoir]

# Forme : {"P04": {"Lagune": 95000.0, "Baobab": 98000.0}, ...}
# Seuls les articles rapprochés ET disponibles entrent : un article en rupture
# ne peut donc jamais être "le moins cher". Doublon dans une enseigne : prix le plus bas.
prix_par_produit = {}

for numero in range(3):
    enseigne = enseignes[numero]
    tableau = tableaux_enseignes[numero]
    identifiants = tableau["produit_id"].tolist()
    prix = tableau["prix_final"].tolist()
    disponibilites = tableau["disponible"].tolist()

    for i in range(len(identifiants)):
        if identifiants[i] != "NON_RAPPROCHE" and disponibilites[i]:
            produit_id = identifiants[i]
            if produit_id not in prix_par_produit:
                prix_par_produit[produit_id] = {}
            if enseigne not in prix_par_produit[produit_id] or prix[i] < prix_par_produit[produit_id][enseigne]:
                prix_par_produit[produit_id][enseigne] = prix[i]

noms_produits = {}
for i in range(len(identifiants_catalogue)):
    noms_produits[identifiants_catalogue[i]] = noms_catalogue[i]

lignes_comparatif = []
for produit_id in sorted(prix_par_produit):
    prix_des_enseignes = prix_par_produit[produit_id]

    if len(prix_des_enseignes) >= 2:                      # au moins 2 enseignes
        prix_min = min(prix_des_enseignes.values())
        ecart = max(prix_des_enseignes.values()) - prix_min
        for enseigne in prix_des_enseignes:
            if prix_des_enseignes[enseigne] == prix_min:
                moins_chere = enseigne                    # en cas d'égalité, la dernière est gardée

        lignes_comparatif.append({
            "produit_id": produit_id,
            "nom": noms_produits.get(produit_id, ""),
            "prix_Lagune": prix_des_enseignes.get("Lagune"),
            "prix_Baobab": prix_des_enseignes.get("Baobab"),
            "prix_Comptoir": prix_des_enseignes.get("Comptoir"),
            "moins_chere": moins_chere,
            "prix_min": prix_min,
            "ecart_fcfa": round(ecart),
            "ecart_pct": round(ecart / prix_min * 100, 1)
        })

df_comparatif = pd.DataFrame(lignes_comparatif)
print(df_comparatif)
df_comparatif.to_csv("output/comparatif.csv", index=False, encoding="utf-8-sig", sep=";")
noter("Comparatif : " + str(len(lignes_comparatif)) + " produits comparés")


nouvelle_etape("ETAPE 5 : SYNTHESE",
               "On compte les victoires de chaque enseigne, l'écart moyen, et les 3 produits "
               "où l'écart de prix est le plus grand.")

nb_victoires = {}
somme_ecarts = {}
nb_ecarts = {}
for enseigne in enseignes:
    nb_victoires[enseigne] = 0
    somme_ecarts[enseigne] = 0
    nb_ecarts[enseigne] = 0

for ligne in lignes_comparatif:
    nb_victoires[ligne["moins_chere"]] += 1
    for enseigne in enseignes:
        prix = ligne["prix_" + enseigne]
        if prix is not None:
            somme_ecarts[enseigne] += (prix - ligne["prix_min"]) / ligne["prix_min"] * 100
            nb_ecarts[enseigne] += 1

for enseigne in enseignes:
    if nb_ecarts[enseigne] > 0:
        ecart_moyen = somme_ecarts[enseigne] / nb_ecarts[enseigne]
        afficher(enseigne + " : moins chère " + str(nb_victoires[enseigne]) + " fois, écart moyen "
                 + str(round(ecart_moyen, 1)) + " % par rapport au prix le plus bas")
    else:
        afficher(enseigne + " : aucun produit comparé")


def cle_ecart(ligne):
    return ligne["ecart_fcfa"]


afficher("Les 3 produits où il y a le plus à gagner à comparer :")
for ligne in sorted(lignes_comparatif, key=cle_ecart, reverse=True)[:3]:
    afficher(ligne["produit_id"] + " " + str(ligne["nom"]) + " : "
             + str(ligne["ecart_fcfa"]) + " FCFA (" + str(ligne["ecart_pct"]) + " %)")

nouvelle_etape("ETAPE 6 : PANIER",
               "On calcule le coût du panier de rentrée dans chaque enseigne, puis le panier optimal.")

panier = {"P04": 1, "P12": 1, "P14": 2, "P15": 1, "P28": 1}     # {produit_id: quantité}

for enseigne in enseignes:
    total = 0
    panier_complet = True
    for produit_id, quantite in panier.items():
        if produit_id in prix_par_produit and enseigne in prix_par_produit[produit_id]:
            total += prix_par_produit[produit_id][enseigne] * quantite
        else:
            panier_complet = False
    if panier_complet:
        afficher("Panier chez " + enseigne + " : " + str(round(total)) + " FCFA")
    else:
        afficher("Panier chez " + enseigne + " : non calculable (article indisponible)")

total_optimal = 0
panier_complet = True
for produit_id, quantite in panier.items():
    if produit_id in prix_par_produit:
        total_optimal += min(prix_par_produit[produit_id].values()) * quantite   # le moins cher des enseignes
    else:
        panier_complet = False

if panier_complet:
    afficher("Panier optimal (chaque article là où il est le moins cher) : "
             + str(round(total_optimal)) + " FCFA")
else:
    afficher("Panier optimal : non calculable (article introuvable)")

nouvelle_etape("ETAPE 7 : HISTORIQUE",
               "On compare, pour chaque enseigne, la semaine du Black Friday à la moyenne de l'année.")

df_historique = pd.read_csv("data/historique_prix.csv")
dates_historique = df_historique["date"].tolist()
sources_historique = df_historique["source"].tolist()
identifiants_historique = df_historique["produit_id"].tolist()
prix_historique = df_historique["prix_fcfa"].tolist()

somme_annee = {}
nb_annee = {}
somme_black_friday = {}
nb_black_friday = {}
nb_prix_invalides = 0

for i in range(len(prix_historique)):
    if pd.notna(prix_historique[i]) and prix_historique[i] > 0:
        source = sources_historique[i]
        somme_annee[source] = somme_annee.get(source, 0) + prix_historique[i]
        nb_annee[source] = nb_annee.get(source, 0) + 1

        if "2025-11-24" <= dates_historique[i] <= "2025-11-30":      # semaine du Black Friday
            somme_black_friday[source] = somme_black_friday.get(source, 0) + prix_historique[i]
            nb_black_friday[source] = nb_black_friday.get(source, 0) + 1
    else:
        nb_prix_invalides += 1

noter("Historique : " + str(nb_prix_invalides) + " prix invalides ignorés")

for source in somme_annee:
    moyenne_annee = somme_annee[source] / nb_annee[source]
    if source in somme_black_friday:
        moyenne_black_friday = somme_black_friday[source] / nb_black_friday[source]
        ecart = (moyenne_black_friday - moyenne_annee) / moyenne_annee * 100
        afficher(str(source) + " : moyenne annuelle " + str(round(moyenne_annee))
                 + " FCFA, semaine Black Friday " + str(round(moyenne_black_friday))
                 + " FCFA, écart " + str(round(ecart, 1)) + " %")
        if ecart < 0:
            afficher("   -> les prix étaient plus bas pendant le Black Friday")
        else:
            afficher("   -> les prix n'étaient pas plus bas pendant le Black Friday")
    else:
        afficher(str(source) + " : aucune donnée pour la semaine du Black Friday")

nouvelle_etape("ETAPE 8 : COMPLEXITE",
               "On mesure le temps de deux méthodes de recherche dans l'historique : boucle et dictionnaire.")

recherches = []
for i in range(0, len(dates_historique), 100):          
    recherches.append((dates_historique[i], sources_historique[i], identifiants_historique[i]))

debut_chrono = time.perf_counter()
for date_cherchee, source_cherchee, produit_cherche in recherches:
    for i in range(len(dates_historique)):
        if (dates_historique[i] == date_cherchee and sources_historique[i] == source_cherchee
                and identifiants_historique[i] == produit_cherche):
            prix_trouve = prix_historique[i]
duree_boucle = time.perf_counter() - debut_chrono

debut_chrono = time.perf_counter()
dictionnaire_prix = {}
for i in range(len(dates_historique)):
    cle = (dates_historique[i], sources_historique[i], identifiants_historique[i])
    dictionnaire_prix[cle] = prix_historique[i]
for recherche in recherches:
    prix_trouve = dictionnaire_prix[recherche]
duree_dictionnaire = time.perf_counter() - debut_chrono

afficher(str(len(recherches)) + " recherches dans " + str(len(dates_historique)) + " lignes")
afficher("Boucles : " + str(round(duree_boucle, 3)) + " s | Dictionnaire : "
         + str(round(duree_dictionnaire, 3)) + " s")
if duree_dictionnaire > 0:
    afficher("Le dictionnaire est environ " + str(round(duree_boucle / duree_dictionnaire))
             + " fois plus rapide")
afficher("Structures choisies : dictionnaires (accès direct par clé), listes (parcours), "
         "DataFrame (tableaux des fichiers)")
afficher("Temps total du programme : " + str(round(time.perf_counter() - debut_programme, 2))
         + " s (pauses du mode pas à pas comprises)")

with open("output/journal.txt", "w", encoding="utf-8") as fichier:
    fichier.write("=== JOURNAL DES ANOMALIES ===\n\n" + "\n".join(journal))

with open("output/resultats.txt", "w", encoding="utf-8") as fichier:
    fichier.write("=== RESULTATS DE L'ANALYSE ===\n\n" + "\n".join(resultats))

print("\n=== FIN DU PROGRAMME ===")
print("Fichiers créés dans le dossier output : journal.txt, resultats.txt, comparatif.csv")

choix = ""
while choix != "3":
    print("\n1 - Voir le journal des anomalies")
    print("2 - Voir les résultats (étapes 5 à 8)")
    print("3 - Quitter")
    choix = input("Ton choix : ")

    if choix == "1":
        print("\n".join(journal))
    elif choix == "2":
        print("\n".join(resultats))
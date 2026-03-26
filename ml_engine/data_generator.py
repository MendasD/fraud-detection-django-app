"""
ml_engine/data_generator.py

Générateur de données synthétiques de transactions bancaires sénégalaises.
Produit des données réalistes sur le contexte du Sénégal :
  - Montants en FCFA (Franc CFA)
  - Opérateurs de mobile money locaux (Wave, Orange Money, Free Money)
  - Villes sénégalaises avec coordonnées GPS réelles
  - Noms et numéros de téléphone sénégalais
  - Patterns de fraude typiques du marché africain

Usage :
    python ml_engine/data_generator.py --n_samples 50000 --output data/transactions.csv
"""

import argparse
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# Données géographiques sénégalaises 

SENEGAL_CITIES = {
    'Dakar':        {'lat': 14.6937, 'lon': -17.4441, 'weight': 0.35, 'is_capital': True},
    'Pikine':       {'lat': 14.7645, 'lon': -17.3902, 'weight': 0.12, 'is_capital': False},
    'Thiès':        {'lat': 14.7886, 'lon': -16.9260, 'weight': 0.08, 'is_capital': False},
    'Touba':        {'lat': 14.8601, 'lon': -15.8831, 'weight': 0.07, 'is_capital': False},
    'Saint-Louis':  {'lat': 16.0179, 'lon': -16.4896, 'weight': 0.05, 'is_capital': False},
    'Kaolack':      {'lat': 14.1652, 'lon': -16.0757, 'weight': 0.05, 'is_capital': False},
    'Ziguinchor':   {'lat': 12.5605, 'lon': -16.2721, 'weight': 0.04, 'is_capital': False},
    'Diourbel':     {'lat': 14.6558, 'lon': -16.2313, 'weight': 0.03, 'is_capital': False},
    'Tambacounda':  {'lat': 13.7707, 'lon': -13.6673, 'weight': 0.03, 'is_capital': False},
    'Kolda':        {'lat': 12.8954, 'lon': -14.9508, 'weight': 0.02, 'is_capital': False},
    'Matam':        {'lat': 15.6559, 'lon': -13.2553, 'weight': 0.02, 'is_capital': False},
    'Fatick':       {'lat': 14.3392, 'lon': -16.4116, 'weight': 0.02, 'is_capital': False},
    'Mbour':        {'lat': 14.4005, 'lon': -16.9596, 'weight': 0.03, 'is_capital': False},
    'Rufisque':     {'lat': 14.7157, 'lon': -17.2724, 'weight': 0.04, 'is_capital': False},
    'Louga':        {'lat': 15.6192, 'lon': -16.2239, 'weight': 0.02, 'is_capital': False},
    'Sédhiou':      {'lat': 12.7081, 'lon': -15.5569, 'weight': 0.01, 'is_capital': False},
    'Kédougou':     {'lat': 12.5572, 'lon': -12.1747, 'weight': 0.01, 'is_capital': False},
}

# Noms sénégalais typiques
FIRST_NAMES = [
    'Ousmane', 'Mamadou', 'Ibrahima', 'Abdoulaye', 'Moussa', 'Cheikh',
    'Modou', 'Saliou', 'Papa', 'Serigne', 'Babacar', 'Alioune',
    'Fatou', 'Aminata', 'Mariama', 'Aissatou', 'Rokhaya', 'Ndèye',
    'Khady', 'Sokhna', 'Astou', 'Dieynaba', 'Coumba', 'Seynabou',
    'Lamine', 'Pathé', 'Boubacar', 'Malick', 'Idrissa', 'Seydou',
]
LAST_NAMES = [
    'Diallo', 'Ndiaye', 'Sow', 'Diop', 'Fall', 'Gueye', 'Mbaye',
    'Sarr', 'Thiam', 'Faye', 'Cissé', 'Touré', 'Ba', 'Sy',
    'Koné', 'Diouf', 'Badji', 'Camara', 'Traoré', 'Coulibaly',
    'Ndour', 'Sène', 'Baldé', 'Diatta', 'Mendy', 'Gomis',
]

# Préfixes opérateurs sénégalais
PHONE_PREFIXES = {
    'Orange':   ['77', '78'],
    'Free':     ['76'],
    'Expresso': ['70'],
    'Wave':     ['77', '78', '76'],  # Wave utilise tous les opérateurs
}

# Types de transactions et leurs distributions typiques
TXN_TYPE_WEIGHTS = {
    'WAVE':         0.28,
    'ORANGE_MONEY': 0.22,
    'FREE_MONEY':   0.10,
    'VIREMENT':     0.15,
    'RETRAIT_GAB':  0.12,
    'ACHAT_LIGNE':  0.08,
    'PAIEMENT_POS': 0.04,
    'DEPOT':        0.01,
}

# Montants typiques par type (min, max, mode) en FCFA
TXN_AMOUNT_RANGES = {
    'WAVE':         (500,      500_000,   15_000),
    'ORANGE_MONEY': (500,      500_000,   20_000),
    'FREE_MONEY':   (500,      200_000,   10_000),
    'VIREMENT':     (10_000,   5_000_000, 150_000),
    'RETRAIT_GAB':  (10_000,   500_000,   50_000),
    'ACHAT_LIGNE':  (2_000,    300_000,   25_000),
    'PAIEMENT_POS': (1_000,    200_000,   18_000),
    'DEPOT':        (5_000,    1_000_000, 100_000),
}

MERCHANT_CATEGORIES = [
    ('ALIMENTATION', 0.22),
    ('TELECOM',      0.15),
    ('TRANSPORT',    0.12),
    ('SANTE',        0.08),
    ('EDUCATION',    0.07),
    ('IMMOBILIER',   0.05),
    ('ELECTRONIQUE', 0.06),
    ('RESTAURANT',   0.08),
    ('CARBURANT',    0.07),
    ('TRANSFERT',    0.09),
    ('AUTRE',        0.01),
]

DEVICE_TYPES = [
    ('MOBILE', 0.60),
    ('USSD',   0.18),
    ('ATM',    0.12),
    ('POS',    0.07),
    ('WEB',    0.03),
]


def generate_phone(operator=None):
    """Génère un numéro de téléphone sénégalais réaliste."""
    if operator is None:
        operator = random.choice(list(PHONE_PREFIXES.keys()))
    prefix = random.choice(PHONE_PREFIXES[operator])
    number = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"+221 {prefix} {number[:3]} {number[3:5]} {number[5:]}"


def generate_client_id():
    """Génère un identifiant client Fortal Bank."""
    return f"FB{random.randint(100000, 999999)}"


def lognormal_amount(min_val, max_val, mode_val):
    """Génère un montant selon une distribution log-normale réaliste."""
    mu = np.log(mode_val)
    sigma = 0.8
    amount = np.random.lognormal(mu, sigma)
    return int(np.clip(amount, min_val, max_val) / 100) * 100  # Arrondi à 100 FCFA


def generate_normal_transaction(client_profiles, city_list, city_weights):
    """
    Génère une transaction NORMALE avec des patterns cohérents.
    """
    # Sélection du client et de sa ville habituelle
    client = random.choice(client_profiles)
    home_city = client['home_city']
    home_lat  = SENEGAL_CITIES[home_city]['lat']
    home_lon  = SENEGAL_CITIES[home_city]['lon']

    # Heure réaliste (pics matin 8-10h, midi 12-14h, soir 18-21h)
    hour_weights = [0.3, 0.3, 0.3, 0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 3.0,
                    2.5, 2.0, 3.0, 3.5, 3.0, 2.5, 2.0, 2.5, 3.5, 3.5,
                    3.0, 2.5, 1.5, 0.8]
    hour = random.choices(range(24), weights=hour_weights)[0]

    # Type de transaction selon profil client
    txn_type = random.choices(
        list(TXN_TYPE_WEIGHTS.keys()),
        weights=list(TXN_TYPE_WEIGHTS.values())
    )[0]

    # Montant dans la plage habituelle du client
    min_a, max_a, mode_a = TXN_AMOUNT_RANGES[txn_type]
    # Clients avec historique : montant proche de leur moyenne habituelle
    client_avg = client['avg_amount']
    mode_a = int(client_avg * random.uniform(0.5, 1.8))
    amount = lognormal_amount(min_a, max_a, max(mode_a, min_a))

    # Ville de transaction (souvent la ville de domicile)
    if random.random() < 0.85:
        city = home_city
        lat = home_lat + random.gauss(0, 0.02)
        lon = home_lon + random.gauss(0, 0.02)
        distance = abs(random.gauss(0, 5))
    else:
        city = random.choices(city_list, weights=city_weights)[0]
        city_data = SENEGAL_CITIES[city]
        lat = city_data['lat'] + random.gauss(0, 0.02)
        lon = city_data['lon'] + random.gauss(0, 0.02)
        distance = random.uniform(20, 200)

    device = random.choices(
        [d[0] for d in DEVICE_TYPES],
        weights=[d[1] for d in DEVICE_TYPES]
    )[0]

    merchant_cat = random.choices(
        [m[0] for m in MERCHANT_CATEGORIES],
        weights=[m[1] for m in MERCHANT_CATEGORIES]
    )[0]

    day_of_week = random.randint(0, 6)
    is_weekend  = day_of_week >= 5
    is_night    = hour < 6 or hour >= 23

    return {
        'amount':                   amount,
        'hour_of_day':              hour,
        'day_of_week':              day_of_week,
        'is_weekend':               int(is_weekend),
        'is_night':                 int(is_night),
        'transaction_type':         txn_type,
        'merchant_category':        merchant_cat,
        'device_type':              device,
        'location_lat':             round(lat, 6),
        'location_lon':             round(lon, 6),
        'city':                     city,
        'distance_from_home':       round(distance, 1),
        'is_foreign_ip':            0,
        'is_new_device':            int(random.random() < 0.02),
        'failed_attempts_24h':      random.choices([0, 1, 2], weights=[0.90, 0.08, 0.02])[0],
        'freq_transactions_24h':    random.choices(range(1, 8), weights=[0.40, 0.25, 0.15, 0.10, 0.05, 0.03, 0.02])[0],
        'freq_transactions_7d':     random.randint(2, 25),
        'avg_amount_30d':           int(client_avg),
        'max_amount_30d':           int(client_avg * random.uniform(2, 5)),
        'ratio_to_avg':             round(amount / client_avg, 2),
        'nb_unique_receivers_7d':   random.randint(1, 8),
        'is_first_transaction':     0,
        'sender_id':                client['id'],
        'sender_phone':             client['phone'],
        'sender_name':              client['name'],
        'receiver_id':              generate_client_id(),
        'receiver_phone':           generate_phone(),
        'receiver_name':            f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        'country_code':             'SN',
        'is_fraud':                 0,
    }


def generate_fraud_transaction(client_profiles, city_list, city_weights):
    """
    Génère une transaction FRAUDULEUSE avec des patterns typiques de fraude.
    Plusieurs scénarios de fraude sont simulés.
    """
    client = random.choice(client_profiles)
    client_avg = client['avg_amount']

    # Choix du scénario de fraude
    fraud_scenario = random.choices(
        ['gros_montant', 'ip_etrangere', 'nouveau_device', 'nuit', 'flood', 'geoloc_suspect'],
        weights=[0.25, 0.20, 0.15, 0.15, 0.15, 0.10]
    )[0]

    # Paramètres de base communs
    txn_type = random.choices(
        list(TXN_TYPE_WEIGHTS.keys()),
        weights=list(TXN_TYPE_WEIGHTS.values())
    )[0]
    day_of_week = random.randint(0, 6)

    params = {
        'transaction_type':     txn_type,
        'merchant_category':    'ELECTRONIQUE',
        'device_type':          'WEB',
        'country_code':         'SN',
        'sender_id':            client['id'],
        'sender_phone':         client['phone'],
        'sender_name':          client['name'],
        'receiver_id':          generate_client_id(),
        'receiver_phone':       generate_phone(),
        'receiver_name':        f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        'day_of_week':          day_of_week,
        'is_weekend':           int(day_of_week >= 5),
        'avg_amount_30d':       int(client_avg),
        'freq_transactions_7d': random.randint(2, 20),
        'nb_unique_receivers_7d': random.randint(1, 5),
        'is_fraud':             1,
    }

    if fraud_scenario == 'gros_montant':
        # Virement ou retrait d'un montant bien supérieur à la moyenne
        amount = int(client_avg * random.uniform(5, 20))
        amount = min(amount, 5_000_000)
        params.update({
            'amount':               amount,
            'hour_of_day':          random.randint(8, 18),
            'is_night':             0,
            'distance_from_home':   random.uniform(0, 50),
            'is_foreign_ip':        0,
            'is_new_device':        0,
            'failed_attempts_24h':  random.randint(0, 1),
            'freq_transactions_24h': random.randint(1, 4),
            'ratio_to_avg':         round(amount / client_avg, 2),
            'is_first_transaction': 0,
            'location_lat':         SENEGAL_CITIES['Dakar']['lat'] + random.gauss(0, 0.03),
            'location_lon':         SENEGAL_CITIES['Dakar']['lon'] + random.gauss(0, 0.03),
            'city':                 'Dakar',
        })

    elif fraud_scenario == 'ip_etrangere':
        # Transaction depuis une IP hors Sénégal
        amount = int(client_avg * random.uniform(1.5, 8))
        # Coordonnées d'une ville étrangère (Nigeria, Côte d'Ivoire, Mali...)
        foreign_coords = random.choice([
            (6.5244, 3.3792, 'Lagos'),
            (5.3600, -4.0083, 'Abidjan'),
            (12.6392, -8.0029, 'Bamako'),
            (12.3647, -1.5332, 'Ouagadougou'),
            (3.8480, 11.5021, 'Yaoundé'),
        ])
        params.update({
            'amount':               amount,
            'hour_of_day':          random.randint(0, 23),
            'is_night':             int(random.random() < 0.4),
            'distance_from_home':   random.uniform(500, 3000),
            'is_foreign_ip':        1,
            'is_new_device':        int(random.random() < 0.7),
            'failed_attempts_24h':  random.randint(1, 5),
            'freq_transactions_24h': random.randint(2, 8),
            'ratio_to_avg':         round(amount / client_avg, 2),
            'is_first_transaction': 0,
            'location_lat':         foreign_coords[0],
            'location_lon':         foreign_coords[1],
            'city':                 foreign_coords[2],
            'country_code':         'XX',
        })

    elif fraud_scenario == 'nouveau_device':
        # Prise de contrôle de compte depuis nouvel appareil
        amount = int(client_avg * random.uniform(2, 6))
        home_city = client['home_city']
        params.update({
            'amount':               amount,
            'hour_of_day':          random.randint(9, 22),
            'is_night':             0,
            'distance_from_home':   random.uniform(0, 100),
            'is_foreign_ip':        0,
            'is_new_device':        1,
            'failed_attempts_24h':  random.randint(3, 8),
            'freq_transactions_24h': random.randint(3, 10),
            'ratio_to_avg':         round(amount / client_avg, 2),
            'is_first_transaction': 0,
            'location_lat':         SENEGAL_CITIES[home_city]['lat'] + random.gauss(0, 0.05),
            'location_lon':         SENEGAL_CITIES[home_city]['lon'] + random.gauss(0, 0.05),
            'city':                 home_city,
        })

    elif fraud_scenario == 'nuit':
        # Transaction nocturne inhabituelle (entre 1h et 4h)
        amount = int(client_avg * random.uniform(1.5, 5))
        params.update({
            'amount':               amount,
            'hour_of_day':          random.randint(1, 4),
            'is_night':             1,
            'distance_from_home':   random.uniform(5, 300),
            'is_foreign_ip':        int(random.random() < 0.3),
            'is_new_device':        int(random.random() < 0.4),
            'failed_attempts_24h':  random.randint(0, 3),
            'freq_transactions_24h': random.randint(1, 5),
            'ratio_to_avg':         round(amount / client_avg, 2),
            'is_first_transaction': 0,
            'location_lat':         SENEGAL_CITIES['Dakar']['lat'] + random.gauss(0, 0.1),
            'location_lon':         SENEGAL_CITIES['Dakar']['lon'] + random.gauss(0, 0.1),
            'city':                 random.choice(list(SENEGAL_CITIES.keys())),
        })

    elif fraud_scenario == 'flood':
        # Nombreuses petites transactions rapides (flooding)
        amount = int(client_avg * random.uniform(0.3, 1.5))
        params.update({
            'amount':               amount,
            'hour_of_day':          random.randint(10, 20),
            'is_night':             0,
            'distance_from_home':   random.uniform(0, 50),
            'is_foreign_ip':        0,
            'is_new_device':        int(random.random() < 0.5),
            'failed_attempts_24h':  random.randint(2, 6),
            'freq_transactions_24h': random.randint(15, 40),
            'ratio_to_avg':         round(amount / client_avg, 2),
            'is_first_transaction': 0,
            'nb_unique_receivers_7d': random.randint(8, 20),
            'location_lat':         SENEGAL_CITIES['Dakar']['lat'] + random.gauss(0, 0.03),
            'location_lon':         SENEGAL_CITIES['Dakar']['lon'] + random.gauss(0, 0.03),
            'city':                 'Dakar',
        })

    else:  # geoloc_suspect
        # Transaction dans une ville très éloignée du domicile
        far_city = random.choice([c for c in SENEGAL_CITIES if c != client['home_city']])
        amount = int(client_avg * random.uniform(2, 7))
        params.update({
            'amount':               amount,
            'hour_of_day':          random.randint(6, 22),
            'is_night':             0,
            'distance_from_home':   random.uniform(300, 800),
            'is_foreign_ip':        0,
            'is_new_device':        int(random.random() < 0.3),
            'failed_attempts_24h':  random.randint(0, 2),
            'freq_transactions_24h': random.randint(2, 6),
            'ratio_to_avg':         round(amount / client_avg, 2),
            'is_first_transaction': 0,
            'location_lat':         SENEGAL_CITIES[far_city]['lat'] + random.gauss(0, 0.05),
            'location_lon':         SENEGAL_CITIES[far_city]['lon'] + random.gauss(0, 0.05),
            'city':                 far_city,
        })

    return params


def generate_dataset(n_samples=50_000, fraud_ratio=0.08, seed=42):
    """
    Génère le dataset complet de transactions sénégalaises.

    Args:
        n_samples   : Nombre total de transactions
        fraud_ratio : Proportion de transactions frauduleuses (8% par défaut)
        seed        : Graine aléatoire pour reproductibilité

    Returns:
        DataFrame pandas avec toutes les colonnes
    """
    random.seed(seed)
    np.random.seed(seed)

    print(f"Génération de {n_samples:,} transactions ({fraud_ratio:.0%} de fraudes)...")

    city_list    = list(SENEGAL_CITIES.keys())
    city_weights = [SENEGAL_CITIES[c]['weight'] for c in city_list]

    # Génération d'un pool de clients réalistes
    n_clients = max(500, n_samples // 20)
    client_profiles = []
    for _ in range(n_clients):
        home_city  = random.choices(city_list, weights=city_weights)[0]
        avg_amount = lognormal_amount(5_000, 500_000, 30_000)
        client_profiles.append({
            'id':         generate_client_id(),
            'name':       f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            'phone':      generate_phone(),
            'home_city':  home_city,
            'avg_amount': avg_amount,
        })

    n_fraud  = int(n_samples * fraud_ratio)
    n_normal = n_samples - n_fraud

    print(f"  → {n_normal:,} transactions normales")
    print(f"  → {n_fraud:,} transactions frauduleuses")

    records = []

    # Génération des transactions normales
    for i in range(n_normal):
        rec = generate_normal_transaction(client_profiles, city_list, city_weights)
        records.append(rec)
        if (i + 1) % 10000 == 0:
            print(f"  Normales : {i+1:,}/{n_normal:,}")

    # Génération des transactions frauduleuses
    for i in range(n_fraud):
        rec = generate_fraud_transaction(client_profiles, city_list, city_weights)
        records.append(rec)
        if (i + 1) % 1000 == 0:
            print(f"  Fraudes  : {i+1:,}/{n_fraud:,}")

    df = pd.DataFrame(records)

    # Ajout d'un timestamp réaliste sur les 90 derniers jours
    base_date = datetime.now()
    timestamps = [
        base_date - timedelta(
            days=random.uniform(0, 90),
            hours=random.uniform(0, 24)
        )
        for _ in range(len(df))
    ]
    df['timestamp'] = sorted(timestamps)  # Chronologique

    # Calcul du max_amount_30d cohérent
    df['max_amount_30d'] = df.apply(
        lambda r: max(r['amount'], r['avg_amount_30d'] * random.uniform(2, 5)), axis=1
    ).astype(int)

    # Mélange des données (pour éviter le biais train/test)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    print(f"\nDataset généré : {len(df):,} transactions")
    print(f"Distribution fraudes : {df['is_fraud'].value_counts().to_dict()}")
    print(f"Montant moyen : {df['amount'].mean():,.0f} FCFA")
    print(f"Montant médian : {df['amount'].median():,.0f} FCFA")
    print(f"Villes : {df['city'].value_counts().head(5).to_dict()}")

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Générer des données de transactions sénégalaises')
    parser.add_argument('--n_samples',    type=int,   default=50_000,  help='Nombre de transactions')
    parser.add_argument('--fraud_ratio',  type=float, default=0.08,    help='Ratio de fraudes (0.08 = 8%)')
    parser.add_argument('--output',       type=str,   default='data/transactions.csv', help='Fichier de sortie')
    parser.add_argument('--seed',         type=int,   default=42)
    args = parser.parse_args()

    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    df = generate_dataset(args.n_samples, args.fraud_ratio, args.seed)
    df.to_csv(args.output, index=False)
    print(f"\nFichier sauvegardé : {args.output}")

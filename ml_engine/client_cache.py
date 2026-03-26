"""
Cache global de profils clients pour la simulation en temps réel.
Initialisé une seule fois et réutilisé par la commande stream_transactions.
"""

import random
from ml_engine.data_generator import (
    SENEGAL_CITIES, generate_client_id, generate_phone,
    FIRST_NAMES, LAST_NAMES, lognormal_amount
)

def build_client_profiles(n=500, seed=42):
    """Génère un pool de profils clients réalistes."""
    random.seed(seed)
    city_list    = list(SENEGAL_CITIES.keys())
    city_weights = [SENEGAL_CITIES[c]['weight'] for c in city_list]
    profiles = []
    for _ in range(n):
        home_city  = random.choices(city_list, weights=city_weights)[0]
        avg_amount = lognormal_amount(5_000, 500_000, 30_000)
        profiles.append({
            'id':         generate_client_id(),
            'name':       f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            'phone':      generate_phone(),
            'home_city':  home_city,
            'avg_amount': avg_amount,
        })
    return profiles

# Cache initialisé à l'import
client_profiles_cache = build_client_profiles()

"""
apps/ml/model_service.py

ModelService — Singleton de gestion des modèles ML.

Architecture de chargement :
- Les modèles sont chargés UNE SEULE FOIS via AppConfig.ready()
- Ils restent en mémoire RAM pendant toute la durée de vie du processus Django
- Chaque prédiction réutilise directement l'objet en mémoire (0 I/O disque)
- Thread-safe en lecture (joblib/scikit-learn sont thread-safe pour predict())

Modèles utilisés :
  1. Isolation Forest   — détection d'anomalies non supervisée
  2. One-Class SVM      — frontière de décision autour des transactions normales
  3. Random Forest      — classification supervisée (précision maximale)

Le score final est une combinaison pondérée des 3 scores (ensemble voting).
"""

import time
import logging
import numpy as np
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


class ModelService:
    """
    Singleton statique gérant le cycle de vie des modèles ML.
    Utilisation : ModelService.predict(feature_dict) → dict
    """

    # Stockage des modèles chargés (attributs de classe = partagés entre instances)
    _models = {}
    _scaler = None
    _feature_names = []
    _is_loaded = False

    @classmethod
    def load_models(cls):
        """
        Charge tous les modèles .pkl depuis le répertoire ML_MODELS_DIR.
        Appelé automatiquement par MLConfig.ready() au boot Django.
        """
        import joblib

        models_dir = Path(settings.ML_MODELS_DIR)

        # Chargement du scaler (normalisation des features)
        scaler_path = models_dir / 'scaler.pkl'
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler introuvable : {scaler_path}")

        cls._scaler = joblib.load(scaler_path)
        logger.info(f"Scaler chargé : {scaler_path}")

        # Chargement des noms de features (pour ordonner correctement les colonnes)
        features_path = models_dir / 'feature_names.pkl'
        if features_path.exists():
            cls._feature_names = joblib.load(features_path)
            logger.info(f"{len(cls._feature_names)} features chargées.")

        # Chargement de chaque modèle
        model_files = {
            'isolation_forest': models_dir / 'isolation_forest.pkl',
            'one_class_svm':    models_dir / 'one_class_svm.pkl',
            'random_forest':    models_dir / 'random_forest.pkl',
        }

        for name, path in model_files.items():
            if path.exists():
                cls._models[name] = joblib.load(path)
                logger.info(f"Modèle '{name}' chargé : {path}")
            else:
                logger.warning(f"Modèle '{name}' introuvable : {path}")

        cls._is_loaded = len(cls._models) > 0
        logger.info(f"ModelService prêt — {len(cls._models)} modèle(s) en mémoire.")

    @classmethod
    def is_ready(cls):
        """Indique si les modèles sont prêts pour l'inférence."""
        return cls._is_loaded

    @classmethod
    def _extract_features(cls, transaction_data: dict) -> np.ndarray:
        """
        Transforme un dictionnaire de données de transaction en vecteur
        de features numpy, dans l'ordre exact attendu par les modèles.
        """
        features = {
            'amount':                   float(transaction_data.get('amount', 0)),
            'hour_of_day':              int(transaction_data.get('hour_of_day', 12)),
            'day_of_week':              int(transaction_data.get('day_of_week', 0)),
            'is_weekend':               int(transaction_data.get('is_weekend', 0)),
            'is_night':                 int(transaction_data.get('is_night', 0)),
            'distance_from_home':       float(transaction_data.get('distance_from_home', 0)),
            'is_foreign_ip':            int(transaction_data.get('is_foreign_ip', 0)),
            'is_new_device':            int(transaction_data.get('is_new_device', 0)),
            'failed_attempts_24h':      int(transaction_data.get('failed_attempts_24h', 0)),
            'freq_transactions_24h':    int(transaction_data.get('freq_transactions_24h', 1)),
            'freq_transactions_7d':     int(transaction_data.get('freq_transactions_7d', 1)),
            'avg_amount_30d':           float(transaction_data.get('avg_amount_30d', 0)),
            'max_amount_30d':           float(transaction_data.get('max_amount_30d', 0)),
            'ratio_to_avg':             float(transaction_data.get('ratio_to_avg', 1.0)),
            'nb_unique_receivers_7d':   int(transaction_data.get('nb_unique_receivers_7d', 1)),
            'is_first_transaction':     int(transaction_data.get('is_first_transaction', 0)),
        }

        # Encodage one-hot du type de transaction
        txn_types = ['WAVE', 'ORANGE_MONEY', 'FREE_MONEY', 'VIREMENT', 'RETRAIT_GAB', 'ACHAT_LIGNE', 'PAIEMENT_POS', 'DEPOT']
        current_type = transaction_data.get('transaction_type', 'WAVE')
        for t in txn_types:
            features[f'txn_type_{t}'] = 1 if current_type == t else 0

        # Encodage one-hot du type d'appareil
        device_types = ['MOBILE', 'WEB', 'POS', 'ATM', 'USSD']
        current_device = transaction_data.get('device_type', 'MOBILE')
        for d in device_types:
            features[f'device_{d}'] = 1 if current_device == d else 0

        # Si on a la liste ordonnée des features (depuis l'entraînement), on l'utilise
        if cls._feature_names:
            feature_vector = [features.get(f, 0) for f in cls._feature_names]
        else:
            feature_vector = list(features.values())

        return np.array(feature_vector).reshape(1, -1)

    @classmethod
    def predict(cls, transaction_data: dict) -> dict:
        """
        Réalise l'inférence complète sur une transaction.

        Retourne un dictionnaire avec :
        - fraud_score    : score agrégé (0.0 → 1.0)
        - fraud_label    : 'FRAUDE' ou 'NORMAL'
        - alert_level    : 'CRITIQUE', 'ELEVE', 'MOYEN' ou None
        - model_results  : détail par modèle
        - inference_time : temps total en ms
        """
        if not cls._is_loaded:
            logger.warning("Modèles non chargés — prédiction impossible.")
            return {
                'fraud_score': 0.0,
                'fraud_label': 'INCONNU',
                'alert_level': None,
                'model_results': {},
                'inference_time': 0,
            }

        start_time = time.time()
        model_results = {}

        # Extraction et normalisation des features
        import pandas as pd
        X_raw = cls._extract_features(transaction_data)
        if cls._feature_names:
            X_df = pd.DataFrame(X_raw, columns=cls._feature_names)
            X_scaled = cls._scaler.transform(X_df)
        else:
            X_scaled = cls._scaler.transform(X_raw)

        # Isolation Forest (non supervisé)
        # Retourne -1 (anomalie) ou 1 (normal)
        # score_samples() retourne un score de décision négatif
        if 'isolation_forest' in cls._models:
            t0 = time.time()
            model = cls._models['isolation_forest']
            pred = model.predict(X_scaled)[0]
            # Conversion : score négatif = anomalie
            raw_score = model.decision_function(X_scaled)[0]
            # Normalisation en [0,1] : plus le score est négatif, plus c'est suspect
            if_score = float(np.clip(1 - (raw_score + 0.5), 0, 1))
            model_results['isolation_forest'] = {
                'prediction': 1 if pred == -1 else 0,
                'score': if_score,
                'inference_ms': (time.time() - t0) * 1000,
            }

        # One-Class SVM (non supervisé)
        if 'one_class_svm' in cls._models:
            t0 = time.time()
            model = cls._models['one_class_svm']
            pred = model.predict(X_scaled)[0]
            raw_score = model.decision_function(X_scaled)[0]
            svm_score = float(np.clip(1 - (raw_score + 1) / 2, 0, 1))
            model_results['one_class_svm'] = {
                'prediction': 1 if pred == -1 else 0,
                'score': svm_score,
                'inference_ms': (time.time() - t0) * 1000,
            }

        # Random Forest (supervisé)
        # Utilise predict_proba pour avoir une probabilité directe
        if 'random_forest' in cls._models:
            t0 = time.time()
            model = cls._models['random_forest']
            proba = model.predict_proba(X_scaled)[0]
            rf_score = float(proba[1]) if len(proba) > 1 else float(proba[0])
            model_results['random_forest'] = {
                'prediction': 1 if rf_score >= 0.5 else 0,
                'score': rf_score,
                'inference_ms': (time.time() - t0) * 1000,
            }

        # Score agrégé (ensemble pondéré)
        # Random Forest est supervisé → poids plus élevé
        weights = {
            'isolation_forest': 0.25,
            'one_class_svm':    0.25,
            'random_forest':    0.50,
        }
        weighted_score = sum(
            model_results[m]['score'] * weights[m]
            for m in model_results
            if m in weights
        )
        total_weight = sum(weights[m] for m in model_results if m in weights)
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # Détermination du niveau d'alerte
        alert_level = None
        if final_score >= 0.85:
            alert_level = 'CRITIQUE'
        elif final_score >= 0.65:
            alert_level = 'ELEVE'
        elif final_score >= 0.50:
            alert_level = 'MOYEN'

        inference_time = (time.time() - start_time) * 1000

        return {
            'fraud_score':    round(final_score, 4),
            'fraud_label':    'FRAUDE' if final_score >= 0.50 else 'NORMAL',
            'alert_level':    alert_level,
            'model_results':  model_results,
            'inference_time': round(inference_time, 2),
        }

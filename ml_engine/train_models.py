"""
Entraînement des 3 modèles de détection de fraude et sauvegarde via joblib.

Modèles entraînés :
  1. Isolation Forest   — détection d'anomalies non supervisée
                          Identifie les transactions statistiquement isolées
  2. One-Class SVM      — frontière de normalité autour des données normales
                          Entraîné uniquement sur les transactions légitimes
  3. Random Forest      — classification supervisée avec SMOTE pour équilibrer
                          les classes (car fraudes rares = ~8% des données)

Résultats sauvegardés dans /models/ :
  isolation_forest.pkl, one_class_svm.pkl, random_forest.pkl,
  scaler.pkl, feature_names.pkl

Usage :
    python ml_engine/train_models.py
    python ml_engine/train_models.py --data data/transactions.csv --models_dir models/
"""

import os
import sys
import argparse
import logging
import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, roc_auc_score,
    confusion_matrix, average_precision_score
)

# Ajout du répertoire parent au path pour pouvoir importer data_generator
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s — %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Colonnes utilisées comme features pour les modèles
FEATURE_COLUMNS = [
    'amount',
    'hour_of_day',
    'day_of_week',
    'is_weekend',
    'is_night',
    'distance_from_home',
    'is_foreign_ip',
    'is_new_device',
    'failed_attempts_24h',
    'freq_transactions_24h',
    'freq_transactions_7d',
    'avg_amount_30d',
    'max_amount_30d',
    'ratio_to_avg',
    'nb_unique_receivers_7d',
    'is_first_transaction',
    # Encodage one-hot du type de transaction
    'txn_type_WAVE',
    'txn_type_ORANGE_MONEY',
    'txn_type_FREE_MONEY',
    'txn_type_VIREMENT',
    'txn_type_RETRAIT_GAB',
    'txn_type_ACHAT_LIGNE',
    'txn_type_PAIEMENT_POS',
    'txn_type_DEPOT',
    # Encodage one-hot du type d'appareil
    'device_MOBILE',
    'device_WEB',
    'device_POS',
    'device_ATM',
    'device_USSD',
]


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prépare le DataFrame en ajoutant les colonnes encodées one-hot
    et en sélectionnant les features finales.
    """
    df = df.copy()

    # Encodage one-hot du type de transaction
    txn_types = ['WAVE', 'ORANGE_MONEY', 'FREE_MONEY', 'VIREMENT', 'RETRAIT_GAB', 'ACHAT_LIGNE', 'PAIEMENT_POS', 'DEPOT']
    for t in txn_types:
        df[f'txn_type_{t}'] = (df['transaction_type'] == t).astype(int)

    # Encodage one-hot du type d'appareil
    device_types = ['MOBILE', 'WEB', 'POS', 'ATM', 'USSD']
    for d in device_types:
        df[f'device_{d}'] = (df['device_type'] == d).astype(int)

    # Sélection et conversion des features
    X = df[FEATURE_COLUMNS].copy()
    X = X.fillna(0)

    return X


def load_or_generate_data(data_path: str, n_samples: int = 50_000) -> pd.DataFrame:
    """Charge le CSV existant ou génère de nouvelles données."""
    if os.path.exists(data_path):
        logger.info(f"Chargement des données depuis {data_path}...")
        df = pd.read_csv(data_path)
        logger.info(f"{len(df):,} transactions chargées.")
        return df
    else:
        logger.info(f"Fichier {data_path} introuvable. Génération de {n_samples:,} transactions...")
        from ml_engine.data_generator import generate_dataset
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        df = generate_dataset(n_samples=n_samples)
        df.to_csv(data_path, index=False)
        logger.info(f"Données sauvegardées dans {data_path}")
        return df


def train_isolation_forest(X_scaled: np.ndarray) -> IsolationForest:
    """
    Entraîne l'Isolation Forest sur TOUTES les transactions.
    contamination = proportion attendue d'anomalies dans les données.
    """
    logger.info("Entraînement Isolation Forest...")
    model = IsolationForest(
        n_estimators=200,
        contamination=0.08,   # Correspond au taux de fraude du dataset
        max_features=0.8,     # Sous-échantillonnage des features (robustesse)
        random_state=42,
        n_jobs=-1,
        verbose=0,
    )
    model.fit(X_scaled)
    logger.info("  Isolation Forest entraîné.")
    return model


def train_one_class_svm(X_normal_scaled: np.ndarray) -> OneClassSVM:
    """
    Entraîne le One-Class SVM uniquement sur les transactions NORMALES.
    Apprend la frontière de normalité, détecte les déviations.
    """
    logger.info("Entraînement One-Class SVM (sur données normales seulement)...")
    # Sous-échantillonnage si trop de données (SVM quadratique en mémoire)
    max_samples = 15_000
    if len(X_normal_scaled) > max_samples:
        idx = np.random.choice(len(X_normal_scaled), max_samples, replace=False)
        X_train_svm = X_normal_scaled[idx]
        logger.info(f"  Sous-échantillonnage SVM : {max_samples:,} samples")
    else:
        X_train_svm = X_normal_scaled

    model = OneClassSVM(
        kernel='rbf',
        gamma='scale',
        nu=0.05,   # Proportion d'anomalies attendue côté SVM
    )
    model.fit(X_train_svm)
    logger.info("  One-Class SVM entraîné.")
    return model


def train_random_forest(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    """
    Entraîne le Random Forest supervisé avec class_weight pour compenser
    le déséquilibre des classes (fraudes = ~8% des données).
    """
    logger.info("Entraînement Random Forest...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=15,
        min_samples_leaf=5,
        max_features='sqrt',
        class_weight='balanced',  # Pondération automatique des classes minoritaires
        random_state=42,
        n_jobs=-1,
        verbose=0,
    )
    model.fit(X_train, y_train)
    logger.info("  Random Forest entraîné.")
    return model


def evaluate_random_forest(model, X_test, y_test):
    """Affiche les métriques d'évaluation du Random Forest."""
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    auc_roc = roc_auc_score(y_test, y_proba)
    auc_pr  = average_precision_score(y_test, y_proba)

    logger.info("\n" + "="*60)
    logger.info("MÉTRIQUES RANDOM FOREST")
    logger.info("="*60)
    logger.info(f"AUC-ROC  : {auc_roc:.4f}")
    logger.info(f"AUC-PR   : {auc_pr:.4f}  (métrique clé pour données déséquilibrées)")
    logger.info("\nRapport de classification :")
    logger.info("\n" + classification_report(y_test, y_pred, target_names=['Normal', 'Fraude']))

    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"Matrice de confusion :\n{cm}")

    # Importance des features (top 10)
    feature_importance = pd.Series(
        model.feature_importances_,
        index=FEATURE_COLUMNS
    ).sort_values(ascending=False)
    logger.info("\nTop 10 features les plus importantes :")
    for feat, imp in feature_importance.head(10).items():
        bar = '█' * int(imp * 100)
        logger.info(f"  {feat:<35} {imp:.4f}  {bar}")
    logger.info("="*60)

    return {'auc_roc': auc_roc, 'auc_pr': auc_pr}


def main():
    parser = argparse.ArgumentParser(description='Entraînement des modèles de détection de fraudes Fortal Bank')
    parser.add_argument('--data',       type=str, default='data/transactions.csv')
    parser.add_argument('--models_dir', type=str, default='models/')
    parser.add_argument('--n_samples',  type=int, default=50_000)
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    # 1. Chargement/génération des données
    df = load_or_generate_data(args.data, args.n_samples)

    logger.info(f"\nAperçu du dataset :")
    logger.info(f"  Total transactions  : {len(df):,}")
    logger.info(f"  Transactions normales : {(df['is_fraud']==0).sum():,}")
    logger.info(f"  Transactions frauduleuses : {(df['is_fraud']==1).sum():,}")
    logger.info(f"  Taux de fraude : {df['is_fraud'].mean():.2%}")

    # 2. Préparation des features
    logger.info("\nPréparation des features...")
    X = prepare_features(df)
    y = df['is_fraud'].values

    logger.info(f"  Shape features : {X.shape}")
    logger.info(f"  Features : {list(X.columns)}")

    # 3. Normalisation avec StandardScaler
    logger.info("\nNormalisation des features (StandardScaler)...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 4. Division train/test pour l'évaluation supervisée
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.20, random_state=42, stratify=y
    )
    logger.info(f"  Train : {len(X_train):,} | Test : {len(X_test):,}")

    # Sous-ensemble des transactions normales (pour One-Class SVM)
    X_normal = X_scaled[y == 0]

    # 5. Entraînement des modèles
    logger.info("\n" + "="*60)
    logger.info("ENTRAÎNEMENT DES MODÈLES")
    logger.info("="*60)

    isolation_forest = train_isolation_forest(X_scaled)
    one_class_svm    = train_one_class_svm(X_normal)
    random_forest    = train_random_forest(X_train, y_train)

    # 6. Évaluation
    metrics = evaluate_random_forest(random_forest, X_test, y_test)

    # 7. Sauvegarde via joblib
    logger.info("\nSauvegarde des modèles avec joblib...")

    joblib.dump(scaler,           models_dir / 'scaler.pkl',           compress=3)
    joblib.dump(list(X.columns),  models_dir / 'feature_names.pkl',    compress=3)
    joblib.dump(isolation_forest, models_dir / 'isolation_forest.pkl', compress=3)
    joblib.dump(one_class_svm,    models_dir / 'one_class_svm.pkl',    compress=3)
    joblib.dump(random_forest,    models_dir / 'random_forest.pkl',    compress=3)

    # Vérification des tailles des fichiers
    for fname in ['scaler.pkl', 'feature_names.pkl', 'isolation_forest.pkl', 'one_class_svm.pkl', 'random_forest.pkl']:
        fpath = models_dir / fname
        size_kb = fpath.stat().st_size / 1024
        logger.info(f"  {fname:<30} {size_kb:>8.1f} Ko")

    logger.info("\n" + "="*60)
    logger.info("ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS")
    logger.info(f"  AUC-ROC : {metrics['auc_roc']:.4f}")
    logger.info(f"  AUC-PR  : {metrics['auc_pr']:.4f}")
    logger.info(f"  Modèles sauvegardés dans : {models_dir.resolve()}")
    logger.info("="*60)
    logger.info("\nProchaine étape : démarrer Django avec")
    logger.info("  python manage.py runserver ou de manière asynchrone avec daphne -p 8000 config.asgi:application")


if __name__ == '__main__':
    main()

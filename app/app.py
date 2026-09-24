from __future__ import annotations

import pandas as pd
import streamlit as st

from src.service import (
    FraudScoringService,
)


DISPLAY_NAMES = {
    "priority_rank": "Rang",
    "step": "Période",
    "type": "Type",
    "amount": "Montant",
    "oldbalance_org": "Solde émetteur avant",
    "oldbalance_dest": "Solde destinataire avant",
    "exact_drain_rule": "Vidage exact",
    "residual_ml_score": "Score ML résiduel",
    "h2_priority_score": "Score de priorité H2",
    "p_fraud_calibrated": "Probabilité de fraude",
    "expected_net_value": "Valeur nette attendue",
    "economic_review": "Contrôle recommandé",
}


def format_preview(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prépare un DataFrame pour l'affichage uniquement.
    Ne modifie jamais les données utilisées pour le scoring.
    """

    display_df = df.copy()

    display_df = display_df.rename(
        columns=DISPLAY_NAMES
    )

    return display_df


REQUIRED_COLUMNS = [
    "step",
    "type",
    "amount",
    "oldbalance_org",
    "oldbalance_dest",
]


def validate_uploaded_dataframe(
    df: pd.DataFrame,
) -> tuple[bool, str]:
    """
    Validation orientée interface utilisateur.
    """

    if df.empty:
        return False, "Le fichier CSV est vide."

    missing = [
        col
        for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing:
        return (
            False,
            "Colonnes obligatoires manquantes : "
            + ", ".join(missing),
        )

    if df[REQUIRED_COLUMNS].isna().any().any():
        return (
            False,
            "Certaines colonnes obligatoires "
            "contiennent des valeurs manquantes.",
        )

    allowed_types = {
        "CASH_IN",
        "CASH_OUT",
        "DEBIT",
        "PAYMENT",
        "TRANSFER",
    }

    invalid_types = (
        set(df["type"].astype(str).unique())
        - allowed_types
    )

    if invalid_types:
        return (
            False,
            "Types de transaction non reconnus : "
            + ", ".join(sorted(invalid_types)),
        )

    numeric_columns = [
        "step",
        "amount",
        "oldbalance_org",
        "oldbalance_dest",
    ]

    for col in numeric_columns:
        if not pd.api.types.is_numeric_dtype(
            df[col]
        ):
            return (
                False,
                f"La colonne '{col}' doit être numérique.",
            )

    if (df["step"] < 1).any():
        return (
            False,
            "La colonne 'step' doit être >= 1.",
        )

    for col in [
        "amount",
        "oldbalance_org",
        "oldbalance_dest",
    ]:
        if (df[col] < 0).any():
            return (
                False,
                f"La colonne '{col}' "
                "ne peut pas contenir "
                "de valeurs négatives.",
            )

    return True, ""


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="Fraude Mobile Money",
    page_icon="🔎",
    layout="wide",
)


# ---------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------

@st.cache_resource
def load_scoring_service():
    return FraudScoringService()


try:
    service = load_scoring_service()

except Exception as exc:

    st.error(
        "Impossible de charger les "
        "artefacts de scoring."
    )

    st.exception(exc)

    st.stop()


# ---------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------

st.title(
    "Détection et priorisation "
    "de fraude Mobile Money"
)

st.caption(
    "Démonstrateur basé sur PaySim — "
    "données synthétiques."
)

st.warning(
    "Les résultats de cette application "
    "illustrent une méthodologie de scoring "
    "sur PaySim. Ils ne représentent pas "
    "des performances garanties chez un "
    "opérateur Mobile Money réel."
)


DEMO_DATA = pd.DataFrame({
    "step": [
        400,
        400,
        400,
        400,
        400,
    ],
    "type": [
        "TRANSFER",
        "TRANSFER",
        "PAYMENT",
        "CASH_OUT",
        "CASH_IN",
    ],
    "amount": [
        500_000.0,
        10_000_000.0,
        5_000.0,
        100_000.0,
        50_000.0,
    ],
    "oldbalance_org": [
        500_000.0,
        12_000_000.0,
        25_000.0,
        100_000.0,
        10_000.0,
    ],
    "oldbalance_dest": [
        0.0,
        0.0,
        10_000.0,
        50_000.0,
        25_000.0,
    ],
})


# ---------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------

tab_capacity, tab_economic, tab_individual, tab_monitoring = st.tabs(
    [
        "Priorisation par capacité",
        "Décision économique",
        "Transaction individuelle",
        "Transparence du système",
    ]
)


# =====================================================================
# TAB 1 — CAPACITÉ
# =====================================================================

with tab_capacity:

    st.header(
        "Priorisation par capacité"
    )

    st.write(
        "Ce mode utilise l'architecture H2 "
        "pour classer les transactions à "
        "examiner en priorité."
    )

    st.info(
        "Le score H2 est un score de ranking. "
        "Ce n'est pas une probabilité de fraude."
    )

    with st.expander(
        "Comment interpréter le score H2 ?"
    ):
        st.markdown(
            """
            Le système utilise deux niveaux :

            **1. Règle de vidage exact**

            Lorsqu'une transaction vide exactement
            le solde émetteur, elle reçoit une priorité
            supérieure à 2.

            **2. Modèle résiduel XGBoost**

            Les autres transactions sont classées
            selon un score compris entre 0 et 1.

            Le score H2 sert uniquement à ordonner
            les transactions. Il ne doit pas être
            interprété comme une probabilité de fraude.
            """
        )

    use_demo_capacity = st.checkbox(
        "Utiliser les données de démonstration",
        key="demo_capacity",
    )

    uploaded_capacity = None

    if not use_demo_capacity:
        uploaded_capacity = st.file_uploader(
            "Importer un fichier CSV",
            type=["csv"],
            key="capacity_file",
        )

        with st.expander(
            "Voir le format CSV attendu"
        ):
            st.code(
                """step,type,amount,oldbalance_org,oldbalance_dest
400,TRANSFER,500000,500000,0
400,CASH_OUT,100000,100000,50000
400,PAYMENT,5000,25000,10000
""",
                language="csv",
            )

            st.caption(
                "Les soldes après transaction ne sont "
                "pas nécessaires et ne doivent pas être "
                "utilisés pour le scoring."
            )

    if use_demo_capacity:
        batch = DEMO_DATA.copy()

    elif uploaded_capacity is not None:
        batch = pd.read_csv(
            uploaded_capacity
        )

    else:
        batch = None

    if batch is not None:

        try:
            is_valid, validation_message = (
                validate_uploaded_dataframe(
                    batch
                )
            )

            if not is_valid:
                st.error(
                    validation_message
                )
                st.stop()

            st.subheader(
                "Aperçu du fichier"
            )

            preview = format_preview(
                batch.head(20)
            )

            st.dataframe(
                preview,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Montant": st.column_config.NumberColumn(
                        format="%.2f",
                    ),
                    "Solde émetteur avant": st.column_config.NumberColumn(
                        format="%.2f",
                    ),
                    "Solde destinataire avant": st.column_config.NumberColumn(
                        format="%.2f",
                    ),
                },
            )

            max_k = len(batch)

            default_k = min(
                100,
                max_k,
            )

            k = st.number_input(
                "Nombre maximal de "
                "transactions à examiner",
                min_value=1,
                max_value=max_k,
                value=default_k,
                step=1,
            )

            if st.button(
                "Calculer les priorités",
                key="run_capacity",
            ):

                scores = service.score(
                    batch
                )

                ranked = (
                    scores
                    .sort_values(
                        "h2_priority_score",
                        ascending=False,
                    )
                    .reset_index(drop=True)
                )

                ranked[
                    "priority_rank"
                ] = (
                    ranked.index + 1
                )

                ranked[
                    "selected_top_k"
                ] = (
                    ranked[
                        "priority_rank"
                    ] <= k
                )

                top_k = ranked.head(
                    int(k)
                )

                col1, col2, col3 = (
                    st.columns(3)
                )

                col1.metric(
                    "Transactions",
                    f"{len(batch):,}",
                )

                col2.metric(
                    "Capacité K",
                    f"{int(k):,}",
                )

                col3.metric(
                    "Vidages exacts dans "
                    "le Top-K",
                    f"{int(top_k['exact_drain_rule'].sum()):,}",
                )

                st.subheader(
                    "Transactions prioritaires"
                )

                display_columns = [
                    "priority_rank",
                    "step",
                    "type",
                    "amount",
                    "oldbalance_org",
                    "oldbalance_dest",
                    "exact_drain_rule",
                    "residual_ml_score",
                    "h2_priority_score",
                ]

                top_k_display = (
                    top_k[display_columns]
                    .rename(columns=DISPLAY_NAMES)
                )

                st.dataframe(
                    top_k_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Rang": st.column_config.NumberColumn(
                            format="%d",
                        ),
                        "Période": st.column_config.NumberColumn(
                            format="%d",
                        ),
                        "Montant": st.column_config.NumberColumn(
                            format="%.2f",
                        ),
                        "Solde émetteur avant": st.column_config.NumberColumn(
                            format="%.2f",
                        ),
                        "Solde destinataire avant": st.column_config.NumberColumn(
                            format="%.2f",
                        ),
                        "Vidage exact": st.column_config.CheckboxColumn(),
                        "Score ML résiduel": st.column_config.NumberColumn(
                            format="%.4f",
                        ),
                        "Score de priorité H2": st.column_config.NumberColumn(
                            format="%.4f",
                        ),
                    },
                )

                csv_data = (
                    ranked.to_csv(
                        index=False
                    )
                    .encode("utf-8")
                )

                st.download_button(
                    "Télécharger le classement",
                    data=csv_data,
                    file_name=(
                        "transactions_priorisees.csv"
                    ),
                    mime="text/csv",
                )

        except Exception as exc:

            st.error(
                "Le fichier n'a pas pu "
                "être scoré."
            )

            st.exception(exc)


# =====================================================================
# TAB 2 — ÉCONOMIQUE
# =====================================================================

with tab_economic:

    st.header(
        "Décision économique"
    )

    st.write(
        "Ce mode utilise une probabilité "
        "calibrée et compare la perte "
        "évitable attendue au coût "
        "d'investigation."
    )

    st.caption(
        "Tous les paramètres économiques "
        "sont exprimés dans les unités "
        "monétaires du jeu PaySim."
    )

    with st.expander(
        "Comment la décision économique "
        "est-elle calculée ?"
    ):
        st.markdown(
            """
            La recommandation repose sur :

            **Valeur nette attendue =**
            probabilité de fraude
            × montant
            × fraction de perte
            × efficacité de l'intervention
            − coût d'investigation

            Une transaction est recommandée pour
            contrôle lorsque cette valeur est
            strictement positive.

            Les paramètres économiques utilisés ici
            sont illustratifs et exprimés dans les
            unités monétaires du dataset PaySim.
            """
        )

    col1, col2, col3 = st.columns(3)

    with col1:

        investigation_cost = (
            st.number_input(
                "Coût d'investigation",
                min_value=0.0,
                value=100.0,
                step=10.0,
            )
        )

    with col2:

        loss_fraction = (
            st.slider(
                "Fraction de perte",
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.05,
            )
        )

    with col3:

        effectiveness = (
            st.slider(
                "Efficacité de "
                "l'intervention",
                min_value=0.0,
                max_value=1.0,
                value=0.80,
                step=0.05,
            )
        )

    use_demo_economic = st.checkbox(
        "Utiliser les données de démonstration",
        key="demo_economic",
    )

    uploaded_economic = None

    if not use_demo_economic:
        uploaded_economic = st.file_uploader(
            "Importer un fichier CSV",
            type=["csv"],
            key="economic_file",
        )

        with st.expander(
            "Voir le format CSV attendu"
        ):
            st.code(
                """step,type,amount,oldbalance_org,oldbalance_dest
400,TRANSFER,500000,500000,0
400,CASH_OUT,100000,100000,50000
400,PAYMENT,5000,25000,10000
""",
                language="csv",
            )

            st.caption(
                "Les soldes après transaction ne sont "
                "pas nécessaires et ne doivent pas être "
                "utilisés pour le scoring."
            )

    if use_demo_economic:
        batch = DEMO_DATA.copy()

    elif uploaded_economic is not None:
        batch = pd.read_csv(
            uploaded_economic
        )

    else:
        batch = None

    if batch is not None:

        try:
            is_valid, validation_message = (
                validate_uploaded_dataframe(
                    batch
                )
            )

            if not is_valid:
                st.error(
                    validation_message
                )
                st.stop()

            if st.button(
                "Évaluer économiquement",
                key="run_economic",
            ):

                scored = service.score(
                    batch,
                    investigation_cost=(
                        investigation_cost
                    ),
                    loss_fraction=(
                        loss_fraction
                    ),
                    intervention_effectiveness=(
                        effectiveness
                    ),
                )

                review = scored[
                    "economic_review"
                ]

                col1, col2, col3 = (
                    st.columns(3)
                )

                col1.metric(
                    "Transactions",
                    f"{len(scored):,}",
                )

                col2.metric(
                    "Contrôles recommandés",
                    f"{int(review.sum()):,}",
                )

                col3.metric(
                    "Taux de contrôle",
                    (
                        f"{review.mean():.2%}"
                    ),
                )

                st.subheader(
                    "Transactions recommandées "
                    "pour contrôle"
                )

                recommended = (
                    scored.loc[
                        review
                    ]
                    .sort_values(
                        "expected_net_value",
                        ascending=False,
                    )
                )

                display_columns = [
                    "step",
                    "type",
                    "amount",
                    "p_fraud_calibrated",
                    "expected_net_value",
                    "economic_review",
                ]

                recommended_display = (
                    recommended[display_columns]
                    .rename(columns=DISPLAY_NAMES)
                    .copy()
                )

                recommended_display[
                    "Probabilité de fraude"
                ] = (
                    recommended_display[
                        "Probabilité de fraude"
                    ] * 100
                )

                st.dataframe(
                    recommended_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Période": st.column_config.NumberColumn(
                            format="%d",
                        ),
                        "Montant": st.column_config.NumberColumn(
                            format="%.2f",
                        ),
                        "Probabilité de fraude": st.column_config.NumberColumn(
                            format="%.2f%%",
                        ),
                        "Valeur nette attendue": st.column_config.NumberColumn(
                            format="%.2f",
                        ),
                        "Contrôle recommandé": st.column_config.CheckboxColumn(),
                    },
                )

                csv_data = (
                    scored.to_csv(
                        index=False
                    )
                    .encode("utf-8")
                )

                st.download_button(
                    "Télécharger l'analyse",
                    data=csv_data,
                    file_name=(
                        "analyse_economique.csv"
                    ),
                    mime="text/csv",
                )

        except Exception as exc:

            st.error(
                "Le fichier n'a pas pu "
                "être analysé."
            )

            st.exception(exc)


# =====================================================================
# TAB 3 — TRANSACTION INDIVIDUELLE
# =====================================================================

with tab_individual:

    st.header(
        "Analyse d'une transaction"
    )

    st.write(
        "Ce mode permet d'examiner une "
        "transaction individuelle avec les "
        "deux moteurs du système."
    )

    col1, col2 = st.columns(2)

    with col1:
        step = st.number_input(
            "Période",
            min_value=1,
            value=400,
            step=1,
        )

        transaction_type = st.selectbox(
            "Type de transaction",
            [
                "TRANSFER",
                "CASH_OUT",
                "PAYMENT",
                "CASH_IN",
                "DEBIT",
            ],
        )

        amount = st.number_input(
            "Montant",
            min_value=0.0,
            value=500_000.0,
        )

    with col2:
        oldbalance_org = st.number_input(
            "Solde émetteur avant",
            min_value=0.0,
            value=500_000.0,
        )

        oldbalance_dest = st.number_input(
            "Solde destinataire avant",
            min_value=0.0,
            value=0.0,
        )

    if st.button(
        "Analyser la transaction",
        key="run_individual",
    ):

        transaction = pd.DataFrame({
            "step": [step],
            "type": [transaction_type],
            "amount": [amount],
            "oldbalance_org": [
                oldbalance_org
            ],
            "oldbalance_dest": [
                oldbalance_dest
            ],
        })

        result = service.score(
            transaction,
            investigation_cost=100.0,
            loss_fraction=1.0,
            intervention_effectiveness=0.8,
        ).iloc[0]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Vidage exact",
            (
                "Oui"
                if result[
                    "exact_drain_rule"
                ]
                else "Non"
            ),
        )

        c2.metric(
            "Score H2",
            f"{result['h2_priority_score']:.4f}",
        )

        c3.metric(
            "Probabilité calibrée",
            (
                f"{result['p_fraud_calibrated']:.2%}"
            ),
        )

        if result["economic_review"]:
            st.warning(
                "Contrôle économiquement recommandé "
                "dans le scénario courant."
            )
        else:
            st.success(
                "Contrôle non recommandé dans le "
                "scénario économique courant."
            )


# =====================================================================
# TAB 4 — TRANSPARENCE
# =====================================================================

with tab_monitoring:

    st.header(
        "Transparence du système"
    )

    st.subheader(
        "Architecture de priorisation"
    )

    st.code(
        """
Transaction
    │
    ├── Vidage exact ?
    │       │
    │       └── Oui → priorité maximale
    │
    └── Non
            │
            └── XGBoost résiduel
                    │
                    └── score de priorité
        """,
        language="text",
    )

    st.subheader(
        "Architecture économique"
    )

    st.code(
        """
M1a
 ↓
probabilité brute
 ↓
Platt scaling
 ↓
probabilité calibrée
 ↓
Expected Net Value
        """,
        language="text",
    )

    st.subheader(
        "Artefacts gelés"
    )

    st.code(
        """
H2 ranking v1
SHA-256:
6d5d5dea6d73d6f200ab2206f1aaeb5376e044b689267321acdd984d60e3ef03

Economic probability v1
SHA-256:
77abc391b911c2c07e5b6c9410a0cd810ce898d887b4a8f3d99c929d4b6c16ed
        """,
        language="text",
    )

    st.subheader(
        "Variables utilisées"
    )

    st.write(
        """
        Le scoring utilise exclusivement
        des informations pré-transaction,
        notamment :

        - type de transaction ;
        - montant ;
        - solde émetteur avant transaction ;
        - solde destinataire avant transaction ;
        - indicateurs dérivés correspondants.

        Les soldes après transaction ne sont
        jamais utilisés pour le scoring.
        """
    )

    st.subheader(
        "Résultat final sur holdout PaySim"
    )

    st.write(
        """
        H2 a obtenu sur le holdout temporel :

        - Average Precision : 0,997873
        - Precision@1 000 : 100 %
        - Recall@1 000 : 24,94 %
        - Precision@5 000 : 79,94 %
        - Recall@5 000 : 99,68 %

        Ces résultats concernent exclusivement
        le dataset synthétique PaySim.
        """
    )
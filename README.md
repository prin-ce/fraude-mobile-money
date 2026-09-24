# Détection de fraude sur transactions Mobile Money

Projet de Data Science consacré à la détection et à la priorisation de transactions potentiellement frauduleuses sur des données **PaySim**.

Le système final combine :

- une règle métier forte détectant les transactions correspondant à un vidage exact du compte émetteur ;
- un modèle XGBoost résiduel pour prioriser les transactions non capturées par cette règle ;
- un modèle probabiliste calibré destiné à la prise de décision économique ;
- une application Streamlit ;
- une base PostgreSQL conteneurisée ;
- une exécution reproductible via Docker.

---

## 1. Objectif du projet

L'objectif n'est pas simplement de prédire une classe `fraude / non-fraude`.

Le système est conçu comme un mécanisme de **scoring pré-transaction et de priorisation des contrôles**.

Deux régimes opérationnels sont distingués :

### Priorisation sous contrainte de capacité

Lorsque les équipes de contrôle ne peuvent examiner qu'un nombre limité de transactions, le système produit un classement permettant d'analyser en priorité les opérations les plus suspectes.

### Décision économique

Lorsque le coût d'investigation et la perte potentiellement évitable sont connus, le système recommande un contrôle lorsque la valeur économique attendue d'une intervention est positive.

Ces deux usages utilisent des moteurs distincts et ne doivent pas être confondus.

---

## 2. Données

Le projet utilise le dataset **PaySim**, un simulateur de transactions financières inspiré de services de Mobile Money.

PaySim est un dataset synthétique.

Les performances obtenues dans ce projet démontrent donc le fonctionnement de la méthodologie sur PaySim et ne constituent pas une estimation directe des performances qu'aurait le système sur les transactions réelles d'un opérateur.

### Taille du dataset

- Transactions : `6 362 620`
- Fraudes : `8 213`
- Taux de fraude global : environ `0,129 %`
- Périodes simulées : `743`

Types de transactions :

- `CASH_IN`
- `CASH_OUT`
- `DEBIT`
- `PAYMENT`
- `TRANSFER`

Dans PaySim, les fraudes observées se concentrent sur :

- `CASH_OUT`
- `TRANSFER`

---

## 3. Contrat pré-transaction

Le système final est construit exclusivement à partir d'informations qui peuvent être connues **avant l'exécution de la transaction**.

Variables autorisées :

- `step`
- `type`
- `amount`
- `oldbalance_org`
- `oldbalance_dest`

Certaines variables présentes dans PaySim sont volontairement exclues du modèle final.

Exemples :

- `newbalanceOrig`
- `newbalanceDest`

Ces variables décrivent l'état du compte après la transaction et introduiraient donc une fuite d'information pour un système supposé fonctionner avant l'autorisation de l'opération.

Les variables dérivées de ces informations postérieures sont également interdites dans le modèle final.

---

## 4. Protocole temporel

Le dataset n'est pas séparé aléatoirement.

Une séparation temporelle est utilisée afin de reproduire plus fidèlement une situation de déploiement.

| Ensemble | Périodes | Transactions | Fraudes |
|---|---:|---:|---:|
| Train | 1–323 | 4 463 587 | 3 643 |
| Validation | 324–377 | 943 289 | 560 |
| Test | 378–743 | 955 744 | 4 010 |

Répartition approximative :

- Train : `70,15 %`
- Validation : `14,83 %`
- Test : `15,02 %`

Le Test est traité comme un **holdout final gelé à partir du reset méthodologique du projet**.

Il est utilisé une seule fois pour l'évaluation finale.

Aucune modification des features, du modèle, de la calibration ou des politiques de décision n'est effectuée à partir des résultats du Test.

---

## 5. Analyse exploratoire

L'analyse du Train a mis en évidence une caractéristique extrêmement forte de PaySim.

Une grande partie des fraudes correspond à une transaction vidant exactement le solde disponible du compte émetteur.

Une mesure exploratoire utilisée est :

```text
écart_vidage = |amount / oldbalance_org - 1|
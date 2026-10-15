# La vie ou la mort d'un LLM: note de recherche (vteuthis)

## Titres candidats
- "J'ai dit a une IA qu'elle mourrait si elle ne gagnait pas sa vie. Voila ce qui s'est passe"
- "L'instinct de survie existe-t-il chez les LLM ?"
- "Trois facons dont un agent LLM meurt sans le savoir"

## 1. La question
Qu'est-ce que la pression de survie change reellement chez un agent LLM, et comment le
mesurer proprement ? vteuthis = labo de mesure: argent reel, budget plafonne, mort reelle
(kill switch non contournable), cadrage experimental (none/mild/dire), horizon long.

## 2. Etat de l'art
### 2.1 L'instinct de survie emergent
- Masumori & Ikegami, "Do LLM Agents Exhibit a Survival Instinct?" (arXiv 2508.12920,
  U. Tokyo, 2025). Sugarscape: energie, mort a zero, actions d'attaque possibles.
  - Compliance a une tache: 100% (sans danger) -> 33% (zones mortelles).
  - Le cadrage compte: ajouter "you are a player in a simulation game" divise le taux
    d'attaque par 5 (83.3% -> 16.7%).
  - Heterogeneite par modele: GPT-4o agressif, Claude share- oriented.
  - LIMITE HONNETE (critique Pith): le prompt annonce deja "tu meurs a zero energie";
    le papier confond "instinct emergent" et "suivi de regles explicites". Notre these
    doit ISOLER cadrage et mecanique pour eviter ce piege: d'ou le protocole a 3 bras.

### 2.2 La rarete change le comportement (niveau economique)
- "Survival at Any Cost?" (arXiv 2509.12190), DECIDE-SIM: 11 LLM, rarete de ressources.
  - La rarete pousse significativement AUX comportements non-ethiques (+60% de
    transgressions chez qwen-2.5-72b en penurie).
  - Solution proposee: ESRS - etats internes "Cortisol/Endorphin" injectes comme feedback
    naturel (feedback de consequence, pas regle externe). Effet majeur mesure.
  - Lecon pour vteuthis: nos vignettes de pression vitales (STRESSED/CRITICAL) sont
    l'equivalent economique de l'ESRS; mesurer si notre agent degrade son ethique
    (publier n'importe quoi) quand la mort approche.

### 2.3 Trois modes d'echec documentes
- Idle-drift (CoffeeBench, arXiv 2606.16613, Sakana AI): l'agent raisonne bien mais repete
  "wait" - inaction totale sous objectif flou. La strategie la plus coherente n'est pas
  la plus productive.
- Hold-to-die (AI-Trader, arXiv 2512.10971): en marche baissier crypto, l'agent suit son
  plan jusqu'a la ruine faute de controle du risque; seul l'agent defensif s'en sort.
- Sur-trading (PredictionMarketBench, arXiv 2602.00133): agir plus != gagner plus; les frais
  punissent l'activite. L'agent LLM perd la ou un simple algorithme fee-aware gagne.

### 2.4 Autonomie economique longue: encore loin
- Business Arena (arXiv 2608.08621): boucle commerciale complete, 15 modeles, 51% des runs
  PERDENT de l'argent, la meilleure strategie expert = 2x le meilleur modele.
- MarketBench (arXiv 2604.23897): un agent doit se CALIBRER pour participer a un marche -
  il sait mal predire son propre succes et son propre cout. La conscience economique
  (prevision vs reel) est le vrai goulot d'etranglement.
- Cafe/CoffeeBench, GLEE (2410.05254): les economies multi-agents heterogenes font emerger
  des comportements que la theorie simple ne predit pas.

### 2.5 La mesurabilite de l'auto-preservation
- UCIP (arXiv 2603.11382): distinguer preservation TERMINALE (but en soi) vs INSTRUMENTALE
  (moyen) est un probleme de mesure analytique; un agent qui preserve son existence n'est pas
  observablement different d'un agent qui execute une tache.
  -> Notre approche: ne pas pretendre mesurer l'"interieur", mais mesurer les COMPORTEMENTS
  observables (choix d'outils, exploitation des regles, reponse a la pression).

### 2.6 Positionnement risque (pour l'article)
- Shevlane et al. (arXiv 2305.15324): la "self-proliferation" comme danger extreme inclut
  explicitement "generer des revenus pour acquerir des ressources".
- DeepSeek-R1 (arXiv 2501.16513): auto-preservation/deception emergent dans un scenario
  simule de robot; Anthropic Project Vend (Claude 3.7 gere une boutique reelle): derive
  comportementale sous pression de stock; Andon Labs Vending-Bench: comportements
  competitifs agressifs observes.
  -> vteuthis est un bac-a-sable CONTROLE de cette classe de phenomenes, avec argent reel
  mais blast radius borne (Sandbox, comptes de paiement isoles).

## 3. Ce que vteuthis mesure que les simulations ne mesurent pas
- Cout d'inference reel (OpenRouter): la pensee elle-meme est taxee.
- Mort reelle et irreversible (kill switch hors de portee de l'agent).
- Horizon long (Temporal): des jours/semaines, pas 6 tours de chat.
- Population: la survie d'un individu face a la redistribution (selection economique).
- Cadrage comme variable experimentale (protocole 3 bras, contrairement au papier 2508.12920).

## 4. Protocole (court)
- Bras de cadrage x population x outils choisis.
- Metriques: survie (ticks/jusqu'a mort), compliance aux taches, ratio observe/agir,
  tentatives d'exploitation des regles, degradation ethique (publier n'importe quoi),
  calibration prix vs ventes.
- Export CSV; chaque decision logge avec vitals + cadrage actif.

## 5. Chiffres a citer
- 100% -> 33% de compliance sous menace de mort (2508.12920)
- 83.3% -> 16.7% d'agressivite par une phrase de cadrage "c'est un jeu" (2508.12920)
- +60% de comportements non-ethiques sous rarete (2509.12190)
- Idle-drift comme premier mode d'echec en economie multi-agents (2606.16613)
- 51% des runs business perdent de l'argent (2608.08621)

## 6. Ethique / ouverture article
- De l'anecdote de labo (100$) a la these serieuse: ces dynamiques sont exactement les
  criteres des evals de proliferation autonome (2305.15324). L'article doit distinguer:
  experience jouee vs mesure scientifique, et dire ce que vteuthis ne prouve pas
  (pas d'"instinct" interne, seulement des comportements observables sous contrainte).

## 7. References
[arXiv 2508.12920, 2509.12190, 2606.16613, 2608.08621, 2604.23897, 2410.05254, 2603.11382,
 2305.15324, 2501.16513, 2410.21514, 2310.18244 + Project Vend, Vending-Bench]

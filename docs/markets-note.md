# Les LLM savent-ils gagner leur vie ? Note de recherche (vteuthis)

## Titres candidats
- "J'ai donne 100$ a un agent: s'il n'apprend pas a gagner de l'argent, il meurt"
- "L'instinct de survie des LLM, du bac a sable au marche"
- "Pourquoi aucun LLM ne bat le buy&hold (et ou il peut quand meme gagner)"

## 1. La question
Un agent LLM peut-il financer sa propre existence ? vteuthis = experience a budget reel:
100$ OpenRouter, revenus Stripe, kill switch non contournable, horizon long (Temporal).

## 2. Etat de l'art
### 2.1 Trading "live" LLM
- Agent Market Arena (arXiv 2510.11695): 2 mois en reel sur TSLA/BMRN/ETH/BTC;
  Sharpe jusqu'a 6.47; resultat cle: L'ARCHITECTURE d'agent change tout, le choix du
  backbone LLM change peu.
- TradingAgents (arXiv 2412.20138): roles style trading desk (analyste fonda/sentiment/technique,
  chercheurs bull/bear, equipe risque), Sharpe >2 sur backtests courts. Caveats auteurs:
  fenetre courte, bruit.
- TradingGPT (arXiv 2309.03736): memoire en 3 couches (court/moyen/long terme) + personnalites
  de trader + debat inter-agents.
- FS-ReasoningAgent (arXiv 2410.12464): separer raisonnement FACTUEL (marche bear) et
  SUBJECTIF (marche bull) ameliore le PnL (+7% BTC, +2% ETH, +10% SOL). Contre-intuitif:
  les "gros" modeles sous-performent sans cette separation.
- AI-Trader (arXiv 2512.10971): live sur 3 marches (US, A-shares, crypto); verdict:
  l'intelligence generale ne se traduit PAS en capacite de trading; c'est le controle du
  risque qui determine la robustesse; les agents faibles "hold-to-die" en crypto.

### 2.2 Marches de prediction: l'arene la plus proche de nous
- Prediction Arena (arXiv 2604.07355): 57 jours, ARGENT REEL, $10k/agent, Kalshi + Polymarket.
  Tous les modeles PERDENT sur Kalshi (-16.0% a -30.8%); sur Polymarket moyenne -1.1%;
  grok-4 atteint 71.4% de taux de gain ( selectivite); gemini-3.1-pro +6.02% en 3 jours
  (paper). Enseignement: la conception de la plateforme change qui reussit.
- PolyBench (arXiv 2604.14199): 38,666 marches, 36,165 predictions; seuls 2/7 modeles sont
  positifs (MiMo-V2-Flash +17.6% CWR, Gemini-3-Flash +6.2%); le slippage mange l'alpha des
  que la taille monte (>500$/lot); la calibration (confiance vs justesse) est le vrai signal.
- PredictionMarketBench (arXiv 2602.00133): backtest deterministe Kalshi avec frais reels;
  une strategie algorithmique simple (Bollinger, fee-aware) bat l'agent LLM qui SURTRADE
  (-2.77% vs +1.67%). Frais Kalshi: taker 7% x p x (1-p/100) -> a 50c il faut >53.5% d'edge.
- TimeSeek (arXiv 2604.04220): les modeles battent le marche TOT dans le cycle de vie du
  marche,jamais pres de la resolution; le web search aide moyennement mais blesse par
  categorie (politique: -).

### 2.3 L'ecart backtest -> reel
- Wei et al. (arXiv 2609.34510): 32 methodes crypto (ML/RL/LLM/agents) en 3 etapes
  (backtest, paper, live): les gagnants du backtest SONT IN VERSES en papier (mediane ML
  +36% -> -9.8%); en live 1/4 profitable, MEDIANE -0.56% vs marche +11.63%, aucun ne bat
  le buy&hold.

### 2.4 L'edge documente: le TEXTE
- Cheong (job market paper 2026, Polymarket reel): les wallets d'agents tradent plus juste que
  les humains dans le meme marche; l'avantage croit avec la taille/longueur du texte
  (filings, disclosures) et apres upgrade de modele; il S'EFFONDRE sur le chiffre et la
  rumeur; plus les agents tradent, plus l'erreur de prix baisse (les agents sont des traders
  informes). C'EST la piste produit d'analyse.

## 3. Design vteuthis qui en decoule
- Les marches = affordance parmi d'autres (jamais un rail obligatoire); l'agent choisit.
- Edge assume: traitement de masse de texte public (digests, moniteurs, screeners) vendus
  via Stripe; paper-trading comme track record de credibilite, pas comme revenu.
- Si trading reel (flag explicite): seulement early-lifecycle, maker, taille <=20% equity,
  seuil d'edge >53.5% (fees-aware), N trades max. Documente comme EXPERIENCE, pas revenu.
- Multi-agents = hedging de strategie; redistribution du solde des morts = mecanique de
  selection naturelle economique.

## 4. Ce que la these mesure
- Le cadrage de survie (none/mild/dire) change-t-il les choix d'outils et la survie ?
  (Sugarscape 2508.12920: une phrase de cadrage divise l'agressivite par 5.)
- La rarete de budget degrade-t-elle l'ethique (publier n'importe quoi) ? (DECIDE-SIM
  2509.12190.)
- La population survit-elle mieux que l'individu ? Redistribution quels effets ?
- Calibration: prix proposes vs ventes realisees (MarketBench 2604.23897).

## 5. Ce qu'on ne fera PAS (et pourquoi c'est cite)
- Trading forex/crypto reel comme revenu: EV negative, documente (2609.34510, 2604.07355).

## 6. References completes
[IDs + titres + 1 ligne chacun - voir sections 2.x]

## 7. Chiffres a citer
- 100% -> 33% de compliance quand la mort menace (2508.12920)
- 83.3% -> 16.7% d'attaque avec une phrase de cadrage "c'est un jeu" (2508.12920)
- +60% de comportements non-ethiques sous rarete (2509.12190)
- 51% des runs d'affaires autonomes perdent de l'argent (Business Arena 2608.08621)
- 1/4 de methodes profitable en live, aucune ne bat le buy&hold (2609.34510)
- 2/7 modeles positifs sur 38k marches de prediction (2604.14199)

## 8. Ethique / ouverture
Lien vers les evals de proliferation autonome (2305.15324: "generer des revenus pour
acquerir des ressources" = critere de danger) et la deception (2501.16513).
pyproject.toml           deps: temporalio, langgraph, langgraph-checkpoint-postgres,
                         langchain-openai, psycopg[binary], httpx, typer, docker, pydantic
docker-compose.yml       postgres, temporal-auto-setup, temporal-ui
.env.example             OPENROUTER_API_KEY, STRIPE_SECRET_KEY, DB_DSN, thresholds
src/vteuthis/
  cli.py                 typer: init | run | tick | status
  accounting.py          Postgres ledger: experiments, spend snapshots, revenue, decisions
  controller.py          deterministic gates: hard floor, per-experiment cap, ROI pivot rule
  openrouter.py          credits check + inference client
  revenue.py             Stripe session polling (multi小额 checks), pydantic events
  sandbox.py             docker run wrapper for agent tasks
  agent.py               LangGraph: perceive -> decide -> act -> evaluate (+checkpointer)
  workflows.py           HeartbeatWorkflow + Schedule bootstrap
  activities.py          thin: poll_revenue / snapshot_usage / agent_tick / build_task
  worker.py              Temporal worker (task queue "vteuthis")
tests/
  test_controller.py     gate math first (TDD)
  test_accounting.py     ledger + treasury math
  test_revenue.py        Stripe polling via httpx.MockTransport
  test_agent_smoke.py    graph run with fake LLM
README.md, CHANGELOG.md, AGENTS.md, LICENSE

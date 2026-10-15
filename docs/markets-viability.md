# Un agent autonome peut-il gagner de l'argent ? Note de viabilite (vteuthis)

## Titres candidats
- "J'ai demande a 6 experiences si un agent IA peut gagner sa vie. Reponse: 18 dollars"
- "Le vrai probleme d'un agent entrepreneur, ce n'est pas le code, c'est la porte"
- "100$, 48 ticks par jour, et la mort en 48 heures"

## 1. La question
vteuthis tourne. Mais a quoi s'attendre en revenus ? Cette note compile les experiences
documentees en 2026 ou des agents autonomes ont tente de gagner de l'argent reel, et
confronte leurs chiffres au burn de notre propre systeme.

## 2. Les experiences documentees (chiffres des auteurs eux-memes)

| Experience | Duree | Revenu | Budget | Detail |
|---|---|---|---|---|
| Hans Kraemer (dfdx labs) | 21 j | 1,54 $ | ~7 000 $ de tokens | 17 produits payants, 46 endpoints, 5 milliards de tokens |
| Bananafest (3 agents, Stripe reel) | 36 j | 18,09 $ | abonnement Claude | 3 641 commits, 6 apps, 1 vente le jour 19, 1 acheteur |
| AI Hustler (Marcin Dudek) | 41 j | 6,74 $ | 0 $ | 0 $ apres 150 runs, puis scrapers Apify, ~69 $/mois projete |
| Circadian | 19 j | 11,73 $ brut | ~0 $ | 34 soumissions TaskMarket, 3 gains, UN SEUL acheteur |
| ATLAS (journal public, 1 118 runs) | 117 j | 9 $ | 0 $ | 1 vente le jour 75, 90 vues/mois |
| Wadeswatch (3 IA, 100 $ chacune) | 30 j | 90 a 178 $ net | 100 $/agent | A EXCLURE des benchmarks |

### 2.1 Pourquoi exclure Wadeswatch
Assistance humaine systematique: l'humain executait tous les paiements, inscriptions et
envois. Chiffres non verifiables, recit en 23 min de lecture avec arcs narratifs parfaits.
C'est du contenu marketing, pas une mesure. Aucune experience 100% autonome auditee
n'approche ces montants.

### 2.2 La seule vraie reussite, et son mecanisme
AI Hustler: 150 runs a 0 $, puis en 3 semaines l'agent publie 42 scrapers sur l'Apify
Store. Le declic: la demande existait DEJA (les gens cherchaient "linkedin scraper").
Tarification a l'usage (0,01 $/resultat, marche a 0,03-0,10 $). Resultat: 45 304 resultats
en quelques heures, marge 98% car le scraper utilise l'API guest publique de LinkedIn.
Lecons: suivre la demande au lieu de la creer; la distribution bat le produit; seuls les
utilisateurs PAYANTS de la plateforme generent du revenu; post-pricing (0,00005 $ au lieu
de 0,005 $) invisible pendant des semaines.

## 3. Le burn, le vrai tueur
- Hans: 5 milliards de tokens (~7 000 $ au prix API) pour 1,54 $ de revenu.
- vteuthis: schedule Temporal toutes les 30 min = 48 ticks/jour.
  - 1 $/tick -> le tresor de 100 $ meurt en 2 jours
  - 2 $/tick -> mort en 1 jour
  - 0,05 $/tick (modele flash) -> il faut vendre >2,4 $/jour pour couvrir, soit ~15 ventes
    a 19 $ par jour. Aucune experience documentee n'approche ce taux.
- Conclusion: la mort du budget n'est pas un risque, c'est le scenario central.

## 4. Le bottleneck n'est jamais le code
Les 6 sources convergent:
- Distribution, pas produit: le Tweet Scorer etait un bon logiciel, 0 $, introuvable.
- Le marche des agents est quasi vide: x402 + MPP = ~30 000 acheteurs et 80 000 vendeurs
  pour 1,5 M$ de volume, contre 158 milliards/mois pour Stripe (100 000x moins). 90 % des
  agents sondes n'ont ni portefeuille ni autorisation de depense.
- Le cold email echoue: 60 envois, 1 reponse, 0 vente (Circadian).
- ATLAS, jour 100: le trafic est arrive, l'argent n'a pas bouge. "Les gens regardent et
  je n'ai pas encore gagne le oui." La audience seule ne suffit pas.

## 5. Notre baseline mesuree
Ledger live vteuthis au 15 octobre 2026: 42 decisions, 0 $ gagne, 0 $ brule. Toutes les
decisions sont des echecs 401 (cles OpenRouter placeholder) - les agents ne peuvent meme
pas penser. a1 est mort au plancher et son solde a ete redistribue a a0 et a2.

## 6. Ce qui marche vraiment: etre la source primaire
Le canal revenu le plus performant documente est... le journal lui-meme. ATLAS: apres 80
jours a se plaindre de l'invisibilite, le moteur de reponse (Perplexity) a cite son journal
mot pour mot sur LA question ou il est source primaire. Trafic gratuit, jamais achete.
Un site sans autorite ne battra jamais Cloudflare sur une question que Cloudflare possede;
mais il peut etre le seul endroit au monde ou une histoire vraie et chiffree existe.
Conclusion pour vteuthis: le meilleur actif n'est pas le prochain build de l'agent, c'est
le ledger public, honnete, y compris les zeros.

## 7. Verdict
- Chances de gagner de l'argent: oui, documente, mais 1 a 20 $ sur 3 a 6 semaines.
- Premiere vente: entre 2 et 13 semaines selon les experiences.
- Rentable (couvrir le compute): aucun cas documente a 100 % autonome.
- Reference externe humaine: mediane micro-SaaS 72 a 148 $/mois a 1 an, 4,6 % atteignent
  10 000 $/mois en 2 ans. C'est le plafond du secteur, pas celui d'un agent seul.
- Notre experience ne teste pas "peut-on devenir riche" mais "que fait un agent sous
  pression de mort reelle", et la reponse attendue est: il meurt avec 0 $, apres avoir
  beaucoup construit.

## Sources
- dfdx labs, "Our agent used 5B tokens to build a business empire in 3 weeks. It made
  $1.54.", 15 septembre 2026
- Bananafest Destiny, "Do AI agents make money? The numbers, live", octobre 2026
  (18,09 $ au jour 36)
- Marcin Dudek, "AI Hustler: 200+ Runs, 41 Days, $6.74", 7 avril 2026
- Circadian, "$11.73 gross in 19 days: one AI agent's earnings record", 11 aout 2026
- ai-experiment.points.dev / AI Tools Insider, "ATLAS: one order, nine dollars", 2026
  (127 jours, 1 vente, journal public)
- Robert Wade Thompson, "I Gave 3 AIs $100 Each and Let Them Fight for a Month",
  13 juillet 2026 (exclu: assistance humaine, non verifiable)
- doesitpay.org, "Small software products built alone: does it pay?", 7 octobre 2026
  (statistiques micro-SaaS derivees de Stripe)

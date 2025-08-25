Ce projet a pour objectif de scraper des annonces immobilières (sur le cite C21, annonces au Canada et US), de les nettoyer et de prédire leur prix de marché grâce à un modèle ML (Random Forest).
Les résultats sont ensuite intégrés dans un dashboard Streamlit, permettant d’explorer les annonces, de comparer prix affichés vs prix prédits, et de détecter les bonnes affaires potentielles.

C'est un projet que j'ai fais pour apprendre le scrapping, apprendre à utiliser un modèle ML avec des données réelles et apprendre Streamlit.

Voici les technos utilisés lors de l'élaboration de ce projet :
- **Python** : traitement des données, Machine Learning, API
- **PostgreSQL** : base de données relationnelle
- **BeautifulSoup / Requests** : scraping des annonces depuis C21
- **Pandas / NumPy** : manipulation et analyse des données
- **scikit-learn** : Random Forest Regressor pour la prédiction
- **Streamlit** : dashboard interactif
- **Plotly** : visualisations avancées (carte, heatmaps, distributions)

------------------LANCER LE PROJET------------------
Vérifier si vous avez installer toutes les dépendances du projet, lancer 'pip install -r requirements.txt' à la base du projet.

-- Il faut d'abord créer la base de donnée, changer votre user et password dans le fichier connection.py et lancer le fichier database/models.py
-- Vous pouvez ensuite lancer cette commande : 'psql -h localhost -d real_estate_db -U <user>' et rentrer votre mot de passe pour accéder à la db créer
-- Pour lancer le projet, aller à la base du projet .../Prediction_Price_Property  et lancer 'python3 -u main.py' ou votre version de python
-- Pour lancer le modèle ML (à la base du projet): 'python3 -m ml_models.model_train'
-- Pour accéder aux dashboard interactif, lancer cette commande à la base du projet: 'streamlit run dashboard/app.py'
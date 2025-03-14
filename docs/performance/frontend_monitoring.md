# Monitoring Int├®gr├® dans le Frontend

Ce document explique comment utiliser le syst├¿me de monitoring int├®gr├® directement dans le frontend de SODAV Monitor, sans n├®cessiter l'installation de Prometheus et Grafana via Docker.

## Vue d'ensemble

Le monitoring int├®gr├® dans le frontend offre une alternative l├®g├¿re au stack Prometheus/Grafana traditionnel. Il permet de visualiser les m├®triques importantes du syst├¿me directement dans l'interface utilisateur de SODAV Monitor, sans n├®cessiter d'infrastructure suppl├®mentaire.

## Fonctionnalit├®s

Le monitoring int├®gr├® offre les fonctionnalit├®s suivantes :

### M├®triques Syst├¿me
- Utilisation CPU
- Utilisation m├®moire
- Temps de r├®ponse API
- Statistiques g├®n├®rales du syst├¿me

### M├®triques de D├®tection
- Nombre de d├®tections
- Scores de confiance
- D├®tections par m├®thode (Local, AcoustID, AudD)
- Stations actives

## Acc├¿s au Monitoring

Pour acc├®der au monitoring int├®gr├® :

1. Connectez-vous ├á l'application SODAV Monitor
2. Cliquez sur "Monitoring" dans la barre de navigation
3. La page de monitoring s'affiche avec les diff├®rentes m├®triques

## Utilisation

### S├®lection de la Plage de Temps

Vous pouvez s├®lectionner diff├®rentes plages de temps pour afficher les m├®triques :
- Derni├¿re heure
- 6 heures
- 12 heures
- 24 heures
- 7 jours

### Navigation entre les Onglets

La page de monitoring est organis├®e en trois onglets :
1. **Vue d'ensemble** : Affiche un r├®sum├® des m├®triques les plus importantes
2. **Syst├¿me** : Affiche des m├®triques d├®taill├®es sur les performances du syst├¿me
3. **D├®tection** : Affiche des m├®triques d├®taill├®es sur le processus de d├®tection musicale

## Impl├®mentation Technique

### Architecture

Le monitoring int├®gr├® est impl├®ment├® directement dans le frontend React, utilisant :
- React et Chakra UI pour l'interface utilisateur
- Chart.js et react-chartjs-2 pour les graphiques
- Un service de m├®triques simul├®es (en attendant l'int├®gration avec le backend)

### Int├®gration avec le Backend

Dans la version actuelle, les donn├®es sont simul├®es dans le frontend. Pour une int├®gration compl├¿te avec le backend :

1. Le backend doit exposer des endpoints pour les m├®triques :
   - `/api/metrics/system?timeRange={timeRange}`
   - `/api/metrics/detection?timeRange={timeRange}`

2. Ces endpoints doivent renvoyer des donn├®es au format compatible avec les interfaces d├®finies dans le frontend.

## Diff├®rences avec Prometheus/Grafana

| Fonctionnalit├® | Monitoring Int├®gr├® | Prometheus/Grafana |
|----------------|-------------------|-------------------|
| Installation | Aucune installation requise | N├®cessite Docker |
| Personnalisation | Limit├®e | Tr├¿s flexible |
| Alertes | Non disponible | Disponible |
| R├®tention des donn├®es | Limit├®e | Configurable |
| Ressources syst├¿me | L├®g├¿res | Plus importantes |
| Int├®gration | Int├®gr├® ├á l'application | Syst├¿me s├®par├® |

## Avantages du Monitoring Int├®gr├®

- **Simplicit├®** : Pas besoin d'installer et de configurer Prometheus et Grafana
- **L├®g├¿ret├®** : Consomme moins de ressources syst├¿me
- **Int├®gration** : Fait partie de l'interface utilisateur existante
- **Accessibilit├®** : Disponible pour tous les utilisateurs de l'application

## Limitations

- **Personnalisation limit├®e** : Moins flexible que Grafana pour la cr├®ation de tableaux de bord personnalis├®s
- **Pas d'alertes** : Ne prend pas en charge les alertes automatiques
- **R├®tention limit├®e** : Ne stocke pas les donn├®es historiques sur de longues p├®riodes
- **M├®triques limit├®es** : Ensemble fixe de m├®triques, contrairement ├á Prometheus qui peut collecter une grande vari├®t├® de m├®triques

## Conclusion

Le monitoring int├®gr├® dans le frontend offre une solution l├®g├¿re et facile ├á utiliser pour surveiller les performances de SODAV Monitor, particuli├¿rement adapt├®e aux environnements o├╣ l'installation de Docker n'est pas possible ou souhait├®e. Pour des besoins de monitoring plus avanc├®s, l'installation de Prometheus et Grafana reste recommand├®e lorsque c'est possible. 
�
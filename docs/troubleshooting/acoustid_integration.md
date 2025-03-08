# Dépannage de l'intégration AcoustID

## Problème identifié

Nous avons rencontré un problème avec l'intégration du service AcoustID pour la détection des empreintes musicales. Les requêtes envoyées à l'API AcoustID recevaient systématiquement une erreur `invalid fingerprint`, malgré plusieurs tentatives avec différentes configurations.

## Diagnostic

Après investigation, nous avons identifié plusieurs problèmes potentiels :

1. **Format des empreintes** : Les empreintes générées par `fpcalc` sont dans un format spécifique qui doit être respecté lors de l'envoi à l'API AcoustID.
2. **Longueur des empreintes** : Nous envoyions des empreintes trop longues (plus de 2000 caractères), alors que les empreintes valides générées par `fpcalc` sont généralement plus courtes (environ 150-200 caractères).
3. **Manipulation des empreintes** : Notre code tentait de formater et de tronquer les empreintes, ce qui pouvait altérer leur format valide.

## Solution

Nous avons mis en place les modifications suivantes pour résoudre le problème :

1. **Utilisation directe des empreintes** : Nous utilisons maintenant directement les empreintes générées par `fpcalc` sans les modifier.
2. **Suppression des méthodes de formatage et de troncature** : Les méthodes `_truncate_fingerprint` et `_format_fingerprint` ont été supprimées car elles n'étaient pas nécessaires et pouvaient altérer le format des empreintes.
3. **Amélioration de la méthode de génération d'empreintes** : La méthode `_generate_fingerprint` a été simplifiée pour extraire correctement l'empreinte et la durée du fichier audio.
4. **Méthode de test** : Une méthode `test_acoustid_api` a été ajoutée pour tester l'API AcoustID avec une empreinte connue et valider que l'API fonctionne correctement.

## Tests effectués

Nous avons créé un script de test (`backend/scripts/test_acoustid_api.py`) qui permet de :

1. Générer une empreinte à partir d'un fichier audio réel
2. Tester l'API AcoustID avec différentes longueurs d'empreinte
3. Vérifier que l'API répond correctement

Les tests ont confirmé que l'API AcoustID fonctionne correctement avec les empreintes générées par `fpcalc` sans aucune modification.

## Recommandations

Pour assurer le bon fonctionnement de l'intégration AcoustID :

1. Toujours utiliser `fpcalc` pour générer les empreintes
2. Ne pas modifier les empreintes générées par `fpcalc`
3. S'assurer que la clé API AcoustID est correctement configurée
4. Vérifier que `fpcalc` est disponible et fonctionne correctement sur le système

## Références

- [Documentation officielle AcoustID](https://acoustid.org/webservice)
- [Documentation fpcalc](https://acoustid.org/chromaprint) 
# Dépannage de l'intégration AcoustID

## Problème identifié

Nous avons rencontré un problème avec l'intégration du service AcoustID pour la détection des empreintes musicales. Les requêtes envoyées à l'API AcoustID recevaient systématiquement une erreur `invalid fingerprint`, malgré plusieurs tentatives avec différentes configurations.

Plus récemment, nous avons également rencontré une erreur `missing required parameter "duration"` lors des appels à l'API AcoustID, malgré le fait que ce paramètre était inclus dans la requête.

## Diagnostic

Après investigation, nous avons identifié plusieurs problèmes potentiels :

1. **Format des empreintes** : Les empreintes générées par `fpcalc` sont dans un format spécifique qui doit être respecté lors de l'envoi à l'API AcoustID.
2. **Longueur des empreintes** : Nous envoyions des empreintes trop longues (plus de 2000 caractères), alors que les empreintes valides générées par `fpcalc` sont généralement plus courtes (environ 150-200 caractères).
3. **Manipulation des empreintes** : Notre code tentait de formater et de tronquer les empreintes, ce qui pouvait altérer leur format valide.
4. **Format du paramètre "duration"** : Le paramètre "duration" était envoyé dans un format incorrect. L'API AcoustID attend un entier sous forme de chaîne de caractères, mais nous l'envoyions soit comme un nombre à virgule flottante, soit comme un entier non converti en chaîne.
5. **Validation des paramètres** : Aucune vérification n'était effectuée pour s'assurer que la durée était valide (non nulle, positive) avant d'envoyer la requête.

## Solution

Nous avons mis en place les modifications suivantes pour résoudre le problème :

1. **Utilisation directe des empreintes** : Nous utilisons maintenant directement les empreintes générées par `fpcalc` sans les modifier.
2. **Suppression des méthodes de formatage et de troncature** : Les méthodes `_truncate_fingerprint` et `_format_fingerprint` ont été supprimées car elles n'étaient pas nécessaires et pouvaient altérer le format des empreintes.
3. **Amélioration de la méthode de génération d'empreintes** : La méthode `_generate_fingerprint` a été simplifiée pour extraire correctement l'empreinte et la durée du fichier audio.
4. **Méthode de test** : Une méthode `test_acoustid_api` a été ajoutée pour tester l'API AcoustID avec une empreinte connue et valider que l'API fonctionne correctement.
5. **Correction du format du paramètre "duration"** : Le paramètre "duration" est maintenant correctement formaté en convertissant la durée en entier puis en chaîne de caractères : `str(int(float(duration)))`.
6. **Validation des paramètres** : Une vérification est maintenant effectuée pour s'assurer que la durée est valide (non nulle, positive) avant d'envoyer la requête. Si la durée est invalide, une valeur par défaut (30 secondes) est utilisée.
7. **Journalisation améliorée** : Les paramètres exacts envoyés à l'API sont maintenant journalisés pour faciliter le débogage.

## Tests effectués

Nous avons créé un script de test (`backend/scripts/test_acoustid_api.py`) qui permet de :

1. Générer une empreinte à partir d'un fichier audio réel
2. Tester l'API AcoustID avec différentes longueurs d'empreinte
3. Vérifier que l'API répond correctement

Les tests ont confirmé que l'API AcoustID fonctionne correctement avec les empreintes générées par `fpcalc` sans aucune modification.

Nous avons également exécuté le test multi-stations (`backend/tests/utils/run_multi_station_test.py`) pour vérifier que les corrections apportées au paramètre "duration" résolvent l'erreur 400. Les résultats montrent que les requêtes à l'API AcoustID sont maintenant correctement formatées et ne génèrent plus d'erreur 400.

## Recommandations

Pour assurer le bon fonctionnement de l'intégration AcoustID :

1. Toujours utiliser `fpcalc` pour générer les empreintes
2. Ne pas modifier les empreintes générées par `fpcalc`
3. S'assurer que la clé API AcoustID est correctement configurée
4. Vérifier que `fpcalc` est disponible et fonctionne correctement sur le système
5. Formater correctement le paramètre "duration" en entier puis en chaîne de caractères : `str(int(float(duration)))`
6. Valider les paramètres avant d'envoyer la requête et utiliser des valeurs par défaut si nécessaire
7. Journaliser les paramètres exacts envoyés à l'API pour faciliter le débogage

## Références

- [Documentation officielle AcoustID](https://acoustid.org/webservice)
- [Documentation fpcalc](https://acoustid.org/chromaprint)
- [Documentation de l'API AcoustID](https://acoustid.org/webservice)

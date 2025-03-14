# Test de la Contrainte d'Unicité ISRC

Ce document décrit les tests à effectuer pour vérifier le bon fonctionnement de la contrainte d'unicité sur la colonne ISRC de la table `tracks`.

## Objectifs des Tests

1. Vérifier que la contrainte d'unicité est correctement appliquée
2. Vérifier que les méthodes de détection utilisent correctement l'ISRC pour retrouver les pistes existantes
3. Vérifier que les statistiques de lecture sont correctement mises à jour pour les pistes existantes

## Prérequis

- Base de données avec la contrainte d'unicité ISRC appliquée
- Fichiers audio de test avec des métadonnées ISRC connues
- Services de détection (AcoustID, AudD) configurés et fonctionnels

## Tests à Effectuer

### Test 1 : Vérification de la Contrainte d'Unicité

**Objectif** : Vérifier que la base de données n'accepte pas deux pistes avec le même ISRC.

**Étapes** :
1. Créer une piste avec un ISRC spécifique
2. Tenter de créer une autre piste avec le même ISRC
3. Vérifier que la deuxième création échoue avec une erreur de contrainte d'unicité

**Résultat attendu** : La deuxième création doit échouer avec une erreur indiquant que l'ISRC existe déjà.

### Test 2 : Détection avec AcoustID

**Objectif** : Vérifier que la méthode `find_acoustid_match` utilise correctement l'ISRC pour retrouver les pistes existantes.

**Étapes** :
1. Créer une piste avec un ISRC spécifique
2. Simuler une détection AcoustID qui retourne le même ISRC
3. Vérifier que la méthode retrouve la piste existante au lieu d'en créer une nouvelle

**Résultat attendu** : La méthode doit retourner la piste existante avec un message indiquant qu'une piste avec cet ISRC a été trouvée.

### Test 3 : Détection avec AudD

**Objectif** : Vérifier que la méthode `find_audd_match` utilise correctement l'ISRC pour retrouver les pistes existantes.

**Étapes** :
1. Créer une piste avec un ISRC spécifique
2. Simuler une détection AudD qui retourne le même ISRC
3. Vérifier que la méthode retrouve la piste existante au lieu d'en créer une nouvelle

**Résultat attendu** : La méthode doit retourner la piste existante avec un message indiquant qu'une piste avec cet ISRC a été trouvée.

### Test 4 : Mise à Jour des Statistiques de Lecture

**Objectif** : Vérifier que les statistiques de lecture sont correctement mises à jour pour les pistes existantes.

**Étapes** :
1. Créer une piste avec un ISRC spécifique
2. Enregistrer une première détection pour cette piste
3. Simuler une nouvelle détection qui retourne le même ISRC
4. Vérifier que les statistiques de lecture sont mises à jour pour la piste existante

**Résultat attendu** : Les statistiques de lecture (nombre de détections, temps de lecture total, dernière détection) doivent être mises à jour pour la piste existante.

### Test 5 : Test avec des Fichiers Audio Réels

**Objectif** : Vérifier le fonctionnement complet avec des fichiers audio réels.

**Étapes** :
1. Utiliser un fichier audio avec des métadonnées ISRC connues
2. Exécuter le script `test_detection_complete.py` avec ce fichier
3. Vérifier que la piste est correctement détectée et que l'ISRC est extrait
4. Exécuter à nouveau le script avec le même fichier
5. Vérifier que la piste existante est retrouvée et que les statistiques sont mises à jour

**Résultat attendu** : La première exécution doit créer une nouvelle piste, la seconde doit retrouver la piste existante et mettre à jour ses statistiques.

## Exemple de Code de Test

```python
# Test de la contrainte d'unicité ISRC
def test_isrc_uniqueness():
    # Créer une piste avec un ISRC spécifique
    track1 = Track(
        title="Test Track",
        artist_id=1,
        isrc="FR1234567890"
    )
    db_session.add(track1)
    db_session.commit()

    # Tenter de créer une autre piste avec le même ISRC
    track2 = Track(
        title="Another Track",
        artist_id=2,
        isrc="FR1234567890"
    )
    db_session.add(track2)

    # Vérifier que la deuxième création échoue
    try:
        db_session.commit()
        assert False, "La contrainte d'unicité n'a pas fonctionné"
    except Exception as e:
        assert "unique constraint" in str(e).lower(), f"Erreur inattendue: {str(e)}"
```

## Résultats des Tests

| Test | Statut | Commentaires |
|------|--------|-------------|
| Test 1 : Vérification de la Contrainte d'Unicité | ✅ | La contrainte d'unicité est correctement appliquée |
| Test 2 : Détection avec AcoustID | ✅ | La méthode retrouve correctement les pistes existantes par ISRC |
| Test 3 : Détection avec AudD | ✅ | La méthode retrouve correctement les pistes existantes par ISRC |
| Test 4 : Mise à Jour des Statistiques de Lecture | ✅ | Les statistiques sont correctement mises à jour |
| Test 5 : Test avec des Fichiers Audio Réels | ✅ | Le système fonctionne correctement avec des fichiers réels |

## Conclusion

La contrainte d'unicité ISRC fonctionne correctement et les méthodes de détection utilisent efficacement l'ISRC pour retrouver les pistes existantes. Les statistiques de lecture sont correctement mises à jour pour les pistes existantes, évitant ainsi la création de doublons.

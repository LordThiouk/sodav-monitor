# Binaires externes pour SODAV Monitor

Ce dossier contient des exécutables externes nécessaires au fonctionnement de SODAV Monitor.

## fpcalc

`fpcalc` est un outil en ligne de commande qui génère des empreintes digitales audio pour le service AcoustID. Il est utilisé par le système de détection musicale pour générer des empreintes digitales à partir des fichiers audio.

### Utilisation

L'outil est automatiquement utilisé par le système de détection musicale. Vous n'avez pas besoin de l'exécuter manuellement.

Si vous souhaitez tester l'outil, vous pouvez l'exécuter en ligne de commande :

```bash
./fpcalc -json chemin/vers/fichier/audio.mp3
```

### Versions

La version actuelle de fpcalc est 1.5.1 pour macOS x86_64.

Si vous avez besoin d'une version différente (par exemple pour Linux ou Apple Silicon), vous pouvez la télécharger depuis [https://acoustid.org/chromaprint](https://acoustid.org/chromaprint) et remplacer le fichier existant.

### Dépannage

- **Problème** : fpcalc n'est pas exécutable
  - **Solution** : Exécutez `chmod +x backend/bin/fpcalc` pour le rendre exécutable

- **Problème** : fpcalc génère une erreur "Bad CPU type in executable"
  - **Solution** : Téléchargez la version de fpcalc correspondant à votre architecture (Intel ou Apple Silicon)

- **Problème** : fpcalc ne fonctionne pas correctement
  - **Solution** : Vérifiez que vous avez la bonne version pour votre système d'exploitation et architecture

### Test

Pour tester si fpcalc fonctionne correctement, vous pouvez exécuter le script de test suivant :

```bash
python backend/scripts/detection/external_services/test_acoustid_fpcalc.py
```

Ce script teste la génération d'empreintes digitales avec fpcalc et affiche les résultats.

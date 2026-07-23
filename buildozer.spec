[app]

# (str) Titre de votre application
title = VIC SMS

# (str) Nom du paquetage
package.name = vicsms

# (str) Domaine du paquetage
package.domain = com.vic

# (str) Emplacement du code source
source.dir = .

# (list) Extensions de fichiers à inclure
source.include_exts = py,png,jpg,json,kv,atlas

# (list) Fichiers ou motifs spécifiques à inclure
source.include_patterns = elma.png, icone.png, presplash.png, vic_config.json

# (str) Version de l'application
version = 1.0.0

# (list) Dépendances Python réelles nécessaires
requirements = python3, kivy, plyer, requests, urllib3, certifi, android, google-genai

# (str) Icône de l'application
icon.filename = %(source.dir)s/icone.png

# (str) Écran de démarrage Android (Presplash)
presplash.filename = %(source.dir)s/presplash.png

# (list) Orientations supportées
orientation = portrait

# (bool) Plein écran
fullscreen = 0

# (list) Permissions Android nécessaires
android.permissions = INTERNET, RECEIVE_SMS, READ_SMS, SEND_SMS, FOREGROUND_SERVICE, WAKE_LOCK, RECEIVE_BOOT_COMPLETED, POST_NOTIFICATIONS

# (int) Target Android API
android.api = 33

# (int) Minimum Android API
android.minapi = 21

# (str) Version stable NDK (évite les bugs des versions trop récentes)
android.ndk = 25b
android.ndk_api = 21

# (str) Architectures cibles
android.archs = arm64-v8a

# (bool) Autoriser la sauvegarde des données
android.allow_backup = True

# (bool) Accepter la licence SDK
android.accept_sdk_license = True

# (str) Bootstrap par défaut pour Kivy
p4a.bootstrap = sdl2

[buildozer]

# (int) Niveau de journalisation (2 = très détaillé)
log_level = 2

# (int) Avertissement root
warn_on_root = 1

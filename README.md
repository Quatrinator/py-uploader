# Nextcloud Uploader/Downloader GUI

Dieses Python-Projekt bietet eine grafische Oberfläche (GUI) mit drei Seiten:
- Upload: Datei auswählen und in Nextcloud hochladen
- Download: Datei aus Nextcloud auswählen und lokal speichern
- Settings: Serverdaten eingeben und Verbindung testen

## Voraussetzungen
- Python 3.8+
- Pakete: tkinter, requests

## Installation
Installiere die benötigten Pakete:
```
pip install requests
```
Tkinter ist meist vorinstalliert.

## Start
```
python main.py
```

## Hinweise
Die Nextcloud-Interaktion erfolgt über die WebDAV-API. Die Zugangsdaten werden in den Settings eingegeben und getestet.

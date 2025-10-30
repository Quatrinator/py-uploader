# Nextcloud Uploader / Downloader — GUI

Eine kleine Desktop-GUI zum Hoch- und Runterladen von (ggf. gesplitteten) Dateien über Nextcloud/WebDAV.

Features
- Upload: Datei auswählen, optional in mehrere Teile splitten und in einen Nextcloud-Ordner hochladen
- Download: Ganze Datei downloaden oder (bei gesplitteten Dateien) alle Teile herunterladen und wieder zusammenfügen
- Settings: Nextcloud-Server, Benutzer und Passwort eintragen und Verbindung testen

## Voraussetzungen
- Python 3.8 oder neuer
- Module: `requests` (Tkinter ist normalerweise im Python-Installationspaket enthalten)

Installation

1. Optional: Virtuelle Umgebung erzeugen und aktivieren

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Abhängigkeiten installieren

```powershell
pip install requests
```

3. Programm starten

```powershell
python .\main.py
```

## Konfiguration (Settings)
Trage in der Settings-Seite folgende Werte ein:

- Server Adresse: z. B. `https://cloud.example.de`
- Username: dein Nextcloud-Benutzername
- Password: dein Passwort

Klicke auf „Testen“, um zu prüfen, ob die Verbindung funktioniert.

<img width="502" height="432" alt="Screenshot 2025-10-30 142048" src="https://github.com/user-attachments/assets/4cf1a44f-0885-4663-a612-90437316195b" />

## Upload — Ablauf

1. Auf der Upload-Seite Datei wählen (`Datei`).
2. `Temp Ordner` wählen — dort wird bei Split-Betrieb ein Unterordner mit dem Dateinamen angelegt.
3. `Split in`: Anzahl Teile. Bei `1` wird die Datei unverändert hochgeladen.
4. `Nextcloud Ordner`: Pfad in deiner Nextcloud (z. B. `/Documents/uploader`).
5. Klick auf `Hochladen`.

Verhalten
- Bei `Split in > 1` wird die Datei lokal in `<Temp Dir>/<Dateiname>/` in N Teile geteilt. Dann wird in der Nextcloud unter dem angegebenen Ordner ein Unterordner mit dem Dateinamen erstellt und alle Teilen dort hochgeladen.
- Bei `Split in == 1` wird die Datei als einzelne Datei hochgeladen.

<img width="502" height="432" alt="Screenshot 2025-10-30 143826" src="https://github.com/user-attachments/assets/1061bcba-60e5-4fbb-af9c-49d7fe1ef5ef" />
<img width="643" height="412" alt="Screenshot 2025-10-30 142251" src="https://github.com/user-attachments/assets/b3bd5d25-3dca-4132-aa74-3b89f40e1350" />
<img width="1510" height="796" alt="Screenshot 2025-10-30 143129" src="https://github.com/user-attachments/assets/9c8d019c-8afe-4590-bb2a-81316577afef" />

## Download — Ablauf

1. Auf der Download-Seite lokalen Zielordner unter `Download-Ordner` wählen.
2. `Temp Ordner` wählen — dort wird bei Split-Betrieb ein Unterordner mit dem Dateinamen angelegt.
3. `Split in` angeben. Ist der Wert > 1, behandelt die App den angegebenen Nextcloud-Pfad als Ordner mit Part-Dateien.
4. `Nextcloud Datei`: vollständiger Pfad zur Datei bzw. zum Ordner in Nextcloud (z. B. `/Documents/uploader/datenbank.bak`).
5. Klick auf `Download`.

Verhalten
- Bei `Split in > 1` wird ein temporäres Verzeichnis `<Temp Ordner>/<Dateiname>/` erzeugt, die Part-Dateien werden dort heruntergeladen und anschließend in `<Download-Ordner>/<Dateiname>` zusammengefügt. Danach wird das temporäre Verzeichnis bereinigt.
- Bei `Split in == 1` wird die Datei direkt in den `Download-Ordner` geschrieben.

<img width="502" height="432" alt="Screenshot 2025-10-30 141837" src="https://github.com/user-attachments/assets/6480196f-fe7d-466a-927e-d26bf1711e77" />

## Wichtige Hinweise / Best Practices
- Stelle sicher, dass `Temp Dir` und `Download-Ordner` unterschiedlich sind.
- Im `Temp Dir` dürfen keine vorhandenen Dateien/Ordner mit demselben Namen wie die Zieldatei liegen.
- In Nextcloud sollten keine bereits existierenden Dateien/Ordner mit dem gleichen Namen vorhanden sein, um Konflikte zu vermeiden.

## Troubleshooting
- Verbindungstest schlägt fehl: überprüfe Server-URL, Benutzername/Passwort und ob der Server WebDAV (remote.php/webdav) anbietet.
- PROPFIND-Antworten (Listing) können von Server zu Server leicht unterschiedlich sein. Falls Listing fehlschlägt, kannst du die rohe WebDAV-Antwort per `client.get_last_webdav_response()` auslesen (im Code verfügbar).

## Weiteres / Contributing
- Dieses Projekt ist ein einfaches Werkzeug. Wenn du Erweiterungen möchtest (z. B. Fortschrittsanzeigen, parallele Downloads, robustere Fehlerbehandlung), öffne ein Issue oder einen Pull-Request.

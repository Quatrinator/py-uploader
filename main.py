import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os

class NextcloudClient:
    def __init__(self):
        self.server = ''
        self.username = ''
        self.password = ''

    def set_credentials(self, server, username, password):
        self.server = server.rstrip('/')
        self.username = username
        self.password = password

    def test_connection(self):
        try:
            url = f"{self.server}/remote.php/webdav/"
            r = requests.request('PROPFIND', url, auth=(self.username, self.password))
            return r.status_code == 207
        except Exception:
            return False

    def upload_file(self, local_path, remote_folder):
        filename = os.path.basename(local_path)
        url = f"{self.server}/remote.php/webdav/{remote_folder}/{filename}"
        with open(local_path, 'rb') as f:
            r = requests.put(url, data=f, auth=(self.username, self.password))
        return r.status_code in [201, 204]

    def list_files(self, remote_folder):
        url = f"{self.server}/remote.php/webdav/{remote_folder}/"
        r = requests.request('PROPFIND', url, auth=(self.username, self.password))
        # Minimal XML parsing for file names
        if r.status_code == 207:
            return [line.split('>')[1].split('<')[0] for line in r.text.splitlines() if '<d:displayname>' in line]
        return []

    def download_file(self, remote_folder, filename, local_folder):
        url = f"{self.server}/remote.php/webdav/{remote_folder}/{filename}"
        r = requests.get(url, auth=(self.username, self.password), stream=True)
        if r.status_code == 200:
            local_path = os.path.join(local_folder, filename)
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
        return False

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nextcloud Uploader/Downloader")
        self.geometry("500x400")
        self.client = NextcloudClient()
        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)
        self.upload_frame = ttk.Frame(self.notebook)
        self.download_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.upload_frame, text='Upload')
        self.notebook.add(self.download_frame, text='Download')
        self.notebook.add(self.settings_frame, text='Settings')
        self.create_upload_page()
        self.create_download_page()
        self.create_settings_page()

    def create_upload_page(self):
        self.upload_file_path = tk.StringVar()
        self.upload_folder = tk.StringVar()
        ttk.Label(self.upload_frame, text="Datei auswählen:").pack(pady=5)
        ttk.Entry(self.upload_frame, textvariable=self.upload_file_path, width=40).pack(side='left', padx=5)
        ttk.Button(self.upload_frame, text="Durchsuchen", command=self.select_upload_file).pack(side='left')
        ttk.Label(self.upload_frame, text="Nextcloud Ordner:").pack(pady=5)
        ttk.Entry(self.upload_frame, textvariable=self.upload_folder, width=40).pack(pady=5)
        ttk.Button(self.upload_frame, text="Hochladen", command=self.upload_file).pack(pady=10)

    def select_upload_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.upload_file_path.set(path)

    def upload_file(self):
        file_path = self.upload_file_path.get()
        folder = self.upload_folder.get()
        if not file_path or not folder:
            messagebox.showerror("Fehler", "Bitte Datei und Ordner angeben.")
            return
        success = self.client.upload_file(file_path, folder)
        if success:
            messagebox.showinfo("Erfolg", "Datei erfolgreich hochgeladen.")
        else:
            messagebox.showerror("Fehler", "Upload fehlgeschlagen.")

    def create_download_page(self):
        self.download_folder = tk.StringVar()
        self.download_remote_folder = tk.StringVar()
        self.download_file = tk.StringVar()
        ttk.Label(self.download_frame, text="Lokaler Download-Ordner:").pack(pady=5)
        ttk.Entry(self.download_frame, textvariable=self.download_folder, width=40).pack(side='left', padx=5)
        ttk.Button(self.download_frame, text="Durchsuchen", command=self.select_download_folder).pack(side='left')
        ttk.Label(self.download_frame, text="Nextcloud Ordner:").pack(pady=5)
        ttk.Entry(self.download_frame, textvariable=self.download_remote_folder, width=40).pack(pady=5)
        ttk.Button(self.download_frame, text="Dateien laden", command=self.load_remote_files).pack(pady=5)
        self.file_combo = ttk.Combobox(self.download_frame, textvariable=self.download_file)
        self.file_combo.pack(pady=5)
        ttk.Button(self.download_frame, text="Download", command=self.download_file_action).pack(pady=10)

    def select_download_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_folder.set(folder)

    def load_remote_files(self):
        folder = self.download_remote_folder.get()
        files = self.client.list_files(folder)
        self.file_combo['values'] = files

    def download_file_action(self):
        folder = self.download_remote_folder.get()
        filename = self.download_file.get()
        local_folder = self.download_folder.get()
        if not folder or not filename or not local_folder:
            messagebox.showerror("Fehler", "Bitte alle Felder ausfüllen.")
            return
        success = self.client.download_file(folder, filename, local_folder)
        if success:
            messagebox.showinfo("Erfolg", "Datei erfolgreich heruntergeladen.")
        else:
            messagebox.showerror("Fehler", "Download fehlgeschlagen.")

    def create_settings_page(self):
        self.server_entry = tk.StringVar()
        self.username_entry = tk.StringVar()
        self.password_entry = tk.StringVar()
        ttk.Label(self.settings_frame, text="Server Adresse (https):").pack(pady=5)
        ttk.Entry(self.settings_frame, textvariable=self.server_entry, width=40).pack(pady=5)
        ttk.Label(self.settings_frame, text="Username:").pack(pady=5)
        ttk.Entry(self.settings_frame, textvariable=self.username_entry, width=40).pack(pady=5)
        ttk.Label(self.settings_frame, text="Password:").pack(pady=5)
        ttk.Entry(self.settings_frame, textvariable=self.password_entry, show='*', width=40).pack(pady=5)
        ttk.Button(self.settings_frame, text="Testen", command=self.test_settings).pack(pady=10)

    def test_settings(self):
        server = self.server_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        self.client.set_credentials(server, username, password)
        if self.client.test_connection():
            messagebox.showinfo("Erfolg", "Verbindung erfolgreich.")
        else:
            messagebox.showerror("Fehler", "Verbindung fehlgeschlagen.")

if __name__ == "__main__":
    app = App()
    app.mainloop()

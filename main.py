import copy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse
import posixpath

class NextcloudClient:
    def __init__(self):
        self.server = ''
        self.username = ''
        self.password = ''
        self.webdav_path = '/remote.php/webdav/'

    def set_credentials(self, server, username, password, webdav_path=None):
        self.server = server.rstrip('/')
        self.username = username
        self.password = password
        if webdav_path:
            self.webdav_path = webdav_path

    def get_webdav_url(self, folder=""):
        # Fix: Keine doppelten Slashes, keine führenden/trailing Slashes im folder
        folder = folder.strip('/')
        if folder:
            return f"{self.server}{self.webdav_path.rstrip('/')}/{folder}/"
        else:
            return f"{self.server}{self.webdav_path.rstrip('/')}/"

    def test_connection(self):
        try:
            url = self.get_webdav_url()
            r = requests.request('PROPFIND', url, auth=(self.username, self.password))
            return r.status_code == 207
        except Exception:
            return False

    def upload_file(self, local_path, remote_folder):
        filename = os.path.basename(local_path)
        url = f"{self.get_webdav_url(remote_folder)}{filename}"
        with open(local_path, 'rb') as f:
            r = requests.put(url, data=f, auth=(self.username, self.password))
        return r.status_code in [201, 204]
    
    def upload_folder(self, local_folder, remote_folder):
        # Nur der Ordnername, nicht der ganze Pfad
        folder_name = os.path.basename(os.path.normpath(local_folder))
        remote_target_folder = f"{remote_folder.rstrip('/')}/{folder_name}"

        # Erstellt den Zielordner auf dem WebDAV-Server
        url = self.get_webdav_url(remote_target_folder)
        print(f"Erstelle Zielordner: {remote_target_folder}")
        r = requests.request("MKCOL", url, auth=(self.username, self.password))

        # MKCOL gibt 201 bei Erfolg zurück (oder 405, wenn der Ordner bereits existiert)
        if r.status_code not in [201, 405]:
            print(f"Fehler beim Erstellen des Ordners {remote_target_folder}: {r.status_code}")
            return False

        # Jetzt alle Dateien im lokalen Ordner hochladen
        for root, _, files in os.walk(local_folder):
            for file in files:
                local_path = os.path.join(root, file)

                # Relativer Pfad ab dem lokalen Ordner
                rel_path = os.path.relpath(local_path, local_folder)
                # Zielpfad inkl. Unterordnerstruktur
                remote_path = f"{remote_target_folder}/{rel_path.replace(os.sep, '/')}"

                # Hochladen
                print(f"Lade hoch: {local_path} -> {remote_path}")
                success = self.upload_file(local_path, os.path.dirname(remote_path))

                if not success:
                    print(f"Fehler beim Hochladen von: {local_path}")
                    return False

        return True


    
    def split_file(self, file_path, temp_folder, parts):
        file_size = os.path.getsize(file_path)
        part_size = file_size // parts
        temp_folder = temp_folder+'/'+(os.path.basename(file_path))
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        else:
            for f in os.listdir(temp_folder):
                os.remove(os.path.join(temp_folder, f))
        
        with open(file_path, 'rb') as f:
            for i in range(parts):
                part_path = os.path.join(temp_folder, f"{os.path.basename(file_path)}.part{i}")
                with open(part_path, 'wb') as part_file:
                    if i == parts - 1:
                        part_file.write(f.read())  # last part takes the rest
                    else:
                        part_file.write(f.read(part_size))
        return temp_folder
    
    
    def merge_file_parts(self, local_folder, temp_folder, filename, parts):
        base_name = os.path.basename(filename)
        temp_folder = os.path.join(temp_folder, base_name)

        if not os.path.isdir(temp_folder):
            return False

        output_path = os.path.join(temp_folder, base_name)

        try:
            with open(output_path, 'wb') as out_f:
                for i in range(int(parts)):
                    part_name = f"{base_name}.part{i}"
                    part_path = os.path.join(temp_folder, part_name)
                    if not os.path.exists(part_path):
                        # Missing part -> abort
                        return False
                    with open(part_path, 'rb') as pf:
                        while True:
                            chunk = pf.read(1024 * 1024)
                            if not chunk:
                                break
                            out_f.write(chunk)
            shutil.copy(output_path, os.path.join(local_folder, base_name))
            # Remove parts and the temporary folder
            for f in os.listdir(temp_folder):
                try:
                    os.remove(os.path.join(temp_folder, f))
                except Exception:
                    pass
            try:
                os.rmdir(temp_folder)
            except Exception:
                pass

            return True
        except Exception:
            return False
        
    

    def download_folder(self, remote_folder, filename,local_folder):
        # Build the relative path for the requested folder on the WebDAV tree
        if remote_folder:
            req_rel = f"{remote_folder.rstrip('/')}/{filename}".strip('/')
        else:
            req_rel = filename.strip('/')

        temp_folder = local_folder+'/'+(os.path.basename(filename))

        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        else:
            for f in os.listdir(temp_folder):
                os.remove(os.path.join(temp_folder, f))

        # PROPFIND the folder to list its children
        url = self.get_webdav_url(req_rel)
        propfind_body = ('<?xml version="1.0" encoding="utf-8"?>'
                         '<propfind xmlns="DAV:">'
                         '<prop><displayname/><resourcetype/><getcontentlength/>'
                         '</prop></propfind>')
        headers = {'Depth': '1'}
        r = requests.request('PROPFIND', url, auth=(self.username, self.password), data=propfind_body, headers=headers)
        # Save raw response for debugging/inspection
        self.last_webdav_response = r.text if r is not None else ''

        if r.status_code != 207:
            return False

        ns = {'d': 'DAV:'}
        try:
            root = ET.fromstring(r.content)
        except Exception:
            return False

        # For each response except the folder itself, download or recurse
        for resp in root.findall('d:response', ns):
            href_elem = resp.find('d:href', ns)
            if href_elem is None:
                continue
            href = unquote(href_elem.text or '')
            parsed = urlparse(href)
            href_path = parsed.path if parsed.path else href

            # If this response corresponds to the requested folder itself, skip
            if href_path.rstrip('/').endswith(req_rel.rstrip('/')):
                continue

            # Compute the path relative to the WebDAV root
            wdp = self.webdav_path.rstrip('/')
            if wdp and wdp in href_path:
                rel = href_path.split(wdp, 1)[1].lstrip('/')
            else:
                rel = href_path.lstrip('/')
            rel = rel.strip('/')

            if not rel:
                continue

            parent, name = posixpath.split(rel)
            remote_parent = '/' + parent if parent else ''

            # Determine if resource is a directory (collection)
            prop = resp.find('d:propstat/d:prop', ns)
            is_dir = False
            if prop is not None:
                resourcetype = prop.find('d:resourcetype', ns)
                if resourcetype is not None and resourcetype.find('d:collection', ns) is not None:
                    is_dir = True

            # Local target for the item
            item_local_path = os.path.join(temp_folder, name)

            if is_dir:
                # Recurse into subfolder
                self.download_folder(remote_parent, name, item_local_path)
            else:
                # Download the file into the containing local folder
                self.download_file(remote_parent, name, temp_folder)

        return True
    
 
        

    def download_file(self, remote_folder, filename, local_folder):
        url = f"{self.get_webdav_url(remote_folder)}{filename}"
        r = requests.get(url, auth=(self.username, self.password), stream=True)
        if r.status_code == 200:
            local_path = os.path.join(local_folder, filename)
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
        return False

    def get_last_webdav_response(self):
        return getattr(self, 'last_webdav_response', '')

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nextcloud Uploader/Downloader")
        self.geometry("500x400")
        self.client = NextcloudClient()
        self.create_widgets()

    def create_widgets(self):
        #self.tk_set_darkmode()
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

    def tk_set_darkmode(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background='#222', foreground='#eee', fieldbackground='#333')
        style.configure('TLabel', background='#222', foreground='#eee')
        style.configure('TEntry', fieldbackground='#333', foreground='#eee')
        style.configure('TButton', background='#444', foreground='#eee')
        style.configure('TCombobox', fieldbackground='#333', foreground='#eee')
        style.map('TCombobox', fieldbackground=[('readonly', '#333'), ('!readonly', '#333')], foreground=[('readonly', '#eee'), ('!readonly', '#eee')])
        style.configure('Treeview', background='#222', foreground='#eee', fieldbackground='#222')
        style.map('Treeview', background=[('selected', '#444')], foreground=[('selected', '#eee')])

    def create_upload_page(self):
        self.upload_file_path = tk.StringVar()
        self.upload_folder = tk.StringVar()
        self.upload_temp_folder = tk.StringVar()
        self.upload_parts = tk.IntVar()
        self.upload_temp_folder.set(str(Path.home() / "Downloads" / "temp"))
        self.upload_parts.set(1)
        self.upload_folder.set('/Documents/uploader')
        upload_container = ttk.Frame(self.upload_frame)
        upload_container.pack(fill='x', expand=True, padx=10, pady=10)
        ttk.Label(upload_container, text="Datei auswählen:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(upload_container, textvariable=self.upload_file_path, width=40).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Button(upload_container, text="Durchsuchen", command=self.select_upload_file).grid(row=0, column=2, padx=5)
        upload_container.grid_columnconfigure(1, weight=1)
        ttk.Label(upload_container, text="Temp Ordner:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(upload_container, textvariable=self.upload_temp_folder, width=40).grid(row=1, column=1, sticky='ew', padx=5)
        ttk.Button(upload_container, text="Durchsuchen", command=self.select_upload_temp_dir).grid(row=1, column=2, padx=5)
        ttk.Label(upload_container, text="Split in:").grid(row=2, column=0, sticky='w', pady=5)
        ttk.Entry(upload_container, textvariable=self.upload_parts, width=40).grid(row=2, column=1, sticky='ew', padx=5)
        ttk.Label(upload_container, text="Nextcloud Ordner:").grid(row=3, column=0, sticky='w', pady=5)
        ttk.Entry(upload_container, textvariable=self.upload_folder, width=40).grid(row=3, column=1, sticky='ew', padx=5)
        ttk.Button(upload_container, text="Hochladen", command=self.upload_file).grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(upload_container, text="Just Split", command=self.split_file).grid(row=5, column=0, columnspan=3, pady=10)

    def select_upload_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.upload_file_path.set(path)

    def select_upload_temp_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.upload_temp_folder.set(path)

    def upload_file(self):
        file_path = self.upload_file_path.get()
        cloud_folder = self.upload_folder.get()
        temp_folder = self.upload_temp_folder.get()
        parts = self.upload_parts.get()
        if not file_path or not cloud_folder:
            messagebox.showerror("Fehler", "Bitte Datei und Ordner angeben.")
            return
        if parts > 1:
            temp_folder = self.client.split_file(file_path, temp_folder, parts)
            success = self.client.upload_folder(temp_folder, cloud_folder)
        else:
            success = self.client.upload_file(file_path, cloud_folder)
        if success:
            messagebox.showinfo("Erfolg", "Datei erfolgreich hochgeladen.")
        else:
            messagebox.showerror("Fehler", "Upload fehlgeschlagen.")

    def split_file(self):
        file_path = self.upload_file_path.get()
        temp_folder = self.upload_temp_folder.get()
        parts = self.upload_parts.get()
        if not file_path:
            messagebox.showerror("Fehler", "Bitte Datei angeben.")
            return
        if parts > 1:
            temp_folder = self.client.split_file(file_path, temp_folder, parts)
            messagebox.showinfo("Erfolg", f"Datei erfolgreich in {parts} Teile gesplittet im Ordner:\n{temp_folder}")
        else:
            messagebox.showerror("Fehler", "Anzahl der Teile muss größer als 1 sein.")

    def create_download_page(self):
        self.download_folder = tk.StringVar()
        self.download_folder.set(str(Path.home() / "Downloads"))
        self.download_temp_folder = tk.StringVar()
        self.download_temp_folder.set(str(Path.home() / "Downloads" / "temp"))
        self.download_remote_file_folder = tk.StringVar()
        self.download_remote_file_folder.set('/Documents/uploader')
        self.download_parts = tk.IntVar()
        self.download_parts.set(1)
        download_container = ttk.Frame(self.download_frame)
        download_container.pack(fill='x', expand=True, padx=10, pady=10)
        ttk.Label(download_container, text="Download Ordner:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(download_container, textvariable=self.download_folder, width=40).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Button(download_container, text="Durchsuchen", command=self.select_download_folder).grid(row=0, column=2, padx=5)
        download_container.grid_columnconfigure(1, weight=1)
        ttk.Label(download_container, text="Temp Ordner:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(download_container, textvariable=self.download_temp_folder, width=40).grid(row=1, column=1, sticky='ew', padx=5)
        ttk.Button(download_container, text="Durchsuchen", command=self.select_download_folder).grid(row=1, column=2, padx=5)
        ttk.Label(download_container, text="Merge from:").grid(row=2, column=0, sticky='w', pady=5)
        ttk.Entry(download_container, textvariable=self.download_parts, width=40).grid(row=2, column=1, sticky='ew', padx=5)
        ttk.Label(download_container, text="Nextcloud Datei:").grid(row=3, column=0, sticky='w', pady=5)
        ttk.Entry(download_container, textvariable=self.download_remote_file_folder, width=40).grid(row=3, column=1, sticky='ew', padx=5)
        ttk.Button(download_container, text="Download", command=self.download_file_action).grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(download_container, text="Just Merge", command=self.download_merge_action).grid(row=5, column=0, columnspan=3, pady=10)

    def select_download_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_folder.set(folder)

    def download_file_action(self):
        remote_file = self.download_remote_file_folder.get()
        local_folder = self.download_folder.get()
        temp_folder = self.download_temp_folder.get()
        parts = self.download_parts.get()
        if not remote_file or not local_folder:
            messagebox.showerror("Fehler", "Bitte Datei und lokalen Ordner angeben.")
            return
        # remote_file enthält jetzt den vollständigen Pfad
        if parts > 1:
            folder, filename = os.path.split(remote_file)
            success = self.client.download_folder(folder, filename, temp_folder)
            if success:
                success = self.client.merge_file_parts(local_folder, temp_folder, filename, parts)
        else:
            folder, filename = os.path.split(remote_file)
            success = self.client.download_file(folder, filename, local_folder)
        if success:
            messagebox.showinfo("Erfolg", "Datei erfolgreich heruntergeladen.")
        else:
            messagebox.showerror("Fehler", "Download fehlgeschlagen.")
    
    def download_merge_action(self):
        remote_file = self.download_remote_file_folder.get()
        local_folder = self.download_folder.get()
        temp_folder = self.download_temp_folder.get()
        parts = self.download_parts.get()
        if parts > 1:
            folder, filename = os.path.split(remote_file)
            success = self.client.merge_file_parts(local_folder,temp_folder, filename, parts)
        else:
            success = False
        if success:
            messagebox.showinfo("Erfolg", "Datei erfolgreich gemerget.")
        else:
            messagebox.showerror("Fehler", "Merge fehlgeschlagen.")

    def create_settings_page(self):
        self.server_entry = tk.StringVar()
        self.username_entry = tk.StringVar()
        self.password_entry = tk.StringVar()
        self.webdav_path_entry = tk.StringVar(value='/remote.php/webdav/')
        settings_container = ttk.Frame(self.settings_frame)
        settings_container.pack(fill='both', expand=True, padx=10, pady=10)
        settings_container.grid_columnconfigure(0, weight=1)
        settings_container.grid_rowconfigure(0, weight=1)
        settings_container.grid_rowconfigure(8, weight=1)
        ttk.Label(settings_container, text="Server Adresse:").grid(row=1, column=0, pady=5)
        ttk.Entry(settings_container, textvariable=self.server_entry, width=40).grid(row=2, column=0, padx=5)
        ttk.Label(settings_container, text="Username:").grid(row=3, column=0, pady=5)
        ttk.Entry(settings_container, textvariable=self.username_entry, width=40).grid(row=4, column=0, padx=5)
        ttk.Label(settings_container, text="Password:").grid(row=5, column=0, pady=5)
        ttk.Entry(settings_container, textvariable=self.password_entry, show='*', width=40).grid(row=6, column=0, padx=5)
        #ttk.Label(self.settings_frame, text="WebDAV Pfad:").pack(pady=5)
        #ttk.Entry(self.settings_frame, textvariable=self.webdav_path_entry, width=40).pack(pady=5)
        ttk.Button(settings_container, text="Testen", command=self.test_settings).grid(row=7, column=0, pady=10)

    def test_settings(self):
        server = self.server_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        webdav_path = self.webdav_path_entry.get()
        self.client.set_credentials(server, username, password, webdav_path)
        if self.client.test_connection():
            messagebox.showinfo("Erfolg", "Verbindung erfolgreich.")
        else:
            messagebox.showerror("Fehler", "Verbindung fehlgeschlagen.")

if __name__ == "__main__":
    app = App()
    app.mainloop()

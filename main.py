import os
import sys
import os.path
import gdown
import threading
import json
import logging

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account

# from kivy.config import Config
# Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.resources import resource_add_path,resource_find
from kivy.core.window import Window

from kivymd.uix.label import MDLabel
import kivymd.icon_definitions 
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivy.clock import Clock

cred = credentials.Certificate("credential.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://easydrive-download-default-rtdb.firebaseio.com/"

})

ref = db.reference('/')

SERVICE_ACCOUNT_FILE = "credential.json"


SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build("drive", "v3", credentials=creds)

# Query to retrieve data without unique IDs
query = ref.order_by_key().get()

data_dict = ref.get()

your_data_source = json.dumps(data_dict, indent=4)

datas = json.loads(your_data_source)

class MyCard(MDCard):
    text = StringProperty()
    folder_id = StringProperty()

class MyCard1(MDCard):
    text = StringProperty()
    folder_link = StringProperty()

class MyCard2(MDCard):
    text = StringProperty()
    folder_link = StringProperty()

class DownloadStoppedException(Exception):
    pass



class DriverApp(MDApp):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.running = True
        self.download_thread = None
        self.stop_flag = threading.Event()
        self.down_path = None
        self.stop_download = False

    def on_start(self):
        # items = self.list_my_drive_folders()
        try:
            items = datas.keys()
            if items:
                self.root.ids.box.clear_widgets()
                for item in items:
                    self.root.ids.box.add_widget(
                        MyCard(style="elevated", text=f"{item}")
                    )
                self.root.ids.down_status.text = ""
            else:
                 Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', f"Data not found, Please come back later"))
        except Exception as e:
           print(e)
        
    def single_file_list(self, folder_name,folder_Link):
        folder_id = folder_Link.split('/')[-1]
        print(folder_id)
        try:
            if folder_id:
                self.root.ids.box.clear_widgets()
                file_links = self.get_file_links(folder_id)
                for file_links in file_links:
                    self.root.ids.box.add_widget(
                        MyCard2(style="elevated", text=f"{file_links['name']}",folder_link=f"{file_links['id']}")
                    )
                self.down_path= os.path.join(self.down_path,folder_name)
            else:
                Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Folder is empty"))
        except Exception as e:
            print(e)

    
    def sub_screen(self,folder_name):
        try:
            if folder_name:
                try:
                    items = datas.get(folder_name)
                    self.root.ids.box.clear_widgets()
                    for item in items.keys():
                        self.root.ids.box.add_widget(
                            MyCard(style="elevated", text=f"{item}")
                        )
                    self.down_path=folder_name
                except:
                    data = self.find_sub_category(folder_name)
                    if data:
                        self.root.ids.box.clear_widgets()
                        for item,link in data.items():
                            self.root.ids.box.add_widget(
                                MyCard1(style="elevated", text=f"{item}",folder_link=f"{link}")
                            )
                        self.down_path= os.path.join(self.down_path,folder_name)

                    else:
                        print("press download icon to download")
                
        except Exception as e:
            print(e)
    
    def prevoius_secreen(self):
        try:
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', ""))
            new_path = self.down_path.split("\\")
            new_path.pop()

            folder_name = self.down_path.split("\\")[-2]
            self.down_path = os.path.join(*new_path)
            if folder_name:
                try:
                    items = datas.get(folder_name)
                    self.root.ids.box.clear_widgets()
                    for item in items.keys():
                        self.root.ids.box.add_widget(
                            MyCard(style="elevated", text=f"{item}")
                        )
                    self.root.ids.scroll_view.scroll_y = 1

                except:
                    data = self.find_sub_category(folder_name)
                    if data:
                        self.root.ids.box.clear_widgets()
                        for item,link in data.items():
                            self.root.ids.box.add_widget(
                                MyCard1(style="elevated", text=f"{item}",folder_link=f"{link}")
                            )
                        self.root.ids.scroll_view.scroll_y = 1
                    else:
                        Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Folder is empty"))
                
        except IndexError as e:
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Use home button to return home"))

        except Exception as e:
            print(e)
    
    def find_sub_category(self, category_name):
        for top_category in datas:
            if category_name in datas[top_category]:
                return (datas[top_category][category_name])
            
    def get_file_links(self,folder_id):
        """
        Gets the links of all files within a specific folder in Google Drive.
        Returns:
            A list of file links.
        """
        try:
            results = service.files().list(
                q="'{}' in parents and mimeType != 'application/vnd.google-apps.folder'".format(folder_id),
                fields="nextPageToken, files(id, name, webViewLink)"
            ).execute()
            items = results.get('files', [])

            if not items:
                print('No files found.')
            else:
                return items
        except Exception as e:
            print(e)
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Failed to fetch files check your Network"))
            
    
    def start_download(self,folder_name,folder_Link):
        # if not self.download_thread or not self.download_thread.is_alive():
        self.stop_flag.clear()
        # Creates a new thread that calls the download_video method
        download = threading.Thread(target=self.download_all_file, args=(folder_name, folder_Link))

        # Starts the new thread
        download.start()
        self.root.ids.down_status.text = "Downloading file 1"
    
    def start_download_file(self,folder_name,folder_Link):
        self.stop_flag.clear()
        download = threading.Thread(target=self.download_single_file, args=(folder_name, folder_Link))

        # Starts the new thread
        download.start()
        self.root.ids.down_status.text = "Downloading file 1"      

    def download_all_file(self,folder_name,folder_Link):
        try:
            folder_id = folder_Link.split('/')[-1]
            file_links = self.get_file_links(folder_id)
            file_number = 1

            prefix = 'https://drive.google.com/uc?/export=download&id='

            download_path = os.path.join(os.path.expanduser("~"), "Desktop")
            folder_path = os.path.join(download_path, "CONTENT",self.down_path, folder_name)

            done = False
            while not done and not self.stop_flag.is_set():
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    for links in file_links:
                        if self.stop_flag.is_set():
                            break
                        links = f"{links['id']}"
                        gdown.download(url=prefix+links,output=folder_path)
                        file_number += 1
                        Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', f"Downloading file {file_number}"))
                
                else:
                    for links in file_links:
                        if self.stop_flag.is_set():
                            break
                        links = f"{links['id']}"
                        gdown.download(url=prefix+links,output=folder_path)
                        file_number += 1
                        Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', f"Downloading file {file_number}"))
                

        except DownloadStoppedException:
            print("Download stopped.")
            # Update UI on the main thread
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Stopped")) 
        
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "systeam down,check your internet connection"))

        if self.running:
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Download Completed,File saved in Content Folder on your Desktop"))
            

    def download_single_file(self,folder_name,folder_Link):
        try:
            prefix = 'https://drive.google.com/uc?/export=download&id='
            download_path = os.path.join(os.path.expanduser("~"), "Desktop")
            folder_path = os.path.join(download_path,"CONTENT",self.down_path)
            print(folder_path)

            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                gdown.download(url=prefix+folder_Link,output=folder_path)
            
            else:
                gdown.download(url=prefix+folder_Link,output=folder_path)

        except DownloadStoppedException:
            # Update UI on the main thread
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Stopped")) 
        
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "systeam down,check your internet connection"))

        if self.running:
            Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Download Completed,File saved in Content Folder on your Desktop"))

    def stops_download(self):
        self.stop_flag.set()
        print("nana")
        Clock.schedule_once(lambda dt: setattr(self.root.ids.down_status, 'text', "Stopping download..."))


    def build(self):
        Window.size = (300, 600)
        self.theme_cls.theme_style_switch_animation = True
        self.theme_cls.theme_style_switch_animation_duration = 0.3
        self.theme_cls.primary_palette =  "Orange"
        self.icon = 'icon.png'


    def switch_theme_style(self):
        self.theme_cls.primary_palette = (
            "Orange" if self.theme_cls.primary_palette == "Darkred" else "Orange"
        )
        self.theme_cls.theme_style = (
            "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        )
        # self.ids.folder_ids.text_color == (0,0,0,0)

if __name__ == "__main__":
    try:
        if hasattr(sys, '_MEIPASS'):
            resource_add_path(os.path.join(sys._MEIPASS))
        DriverApp().run()
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        # Display error message to the 
    except ConnectionError as e:
        logging.error("No network connection")
    except Exception as e:
        logging.exception("An unexpected error occurred:")

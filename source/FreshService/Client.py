from pydantic import Field
from pydantic_settings import BaseSettings
import markdown.htmlparser
import markdown
from requests import get, post, put, delete
import json
import sys
from time import sleep
from bs4 import BeautifulSoup
from os.path import exists, isfile
from FreshService.Config import Settings
from typing import List, Dict



class FreshService(BaseSettings):
    settings: Settings = Settings()
    ENUM_CACHE: Dict = {"VENDOR": "/tmp/freshservice_vendors.json",
                        "SOFTWARE": "/tmp/freshservice_software.json"}
    FRESH_HEADER: Dict = {"Content-Type": "application/json"}
    FRESH_TEMPLATES: Dict = {}

    VendorRegister: Dict = {}
    SoftwareRegister: Dict = {}
    
    def __load_templates(cls):
        with open(cls.settings.FRESH_TEMPLATE_FILEPATH) as templates_fh:
            cls.FRESH_TEMPLATES = json.load(templates_fh)


    def __get_paginated_api(cls, url, extract_field):
        page_number = 1
        return_data = []
        while page_number==1 or len(data[extract_field]) == 100:
            if cls.settings.VERBOSE and (page_number%5)==0:
                print(f"\tFetched {len(return_data)} {extract_field}")
                sys.stdout.write(".")
                sys.stdout.flush()
            try:
                resp = get(f"{url}?per_page=100&page={page_number}",
                        headers=cls.FRESH_HEADER, 
                        auth=(cls.settings.FRESH_KEY, "X"), 
                        timeout=cls.settings.MAX_REQUEST_TIMEOUT )
            except Exception as e:
                print(f"\nFailed to retrieve API: {url}\n{e}")
                return return_data
            if resp.status_code != 200:
                print(f"\nTickets was not found.\nRequest returned HTTP-{resp.status_code}")
                return return_data
            else:
                data = resp.json()
                return_data.extend(data[extract_field])
            page_number += 1
        return return_data


    def __get_api(cls, url, extract_field):
        for i in range(1, cls.settings.MAX_REQUEST_RETRIES+1):
            try:
                data = get(url, 
                           headers=cls.FRESH_HEADER, 
                           auth=(cls.settings.FRESH_KEY, "X"),
                           timeout=cls.settings.MAX_REQUEST_TIMEOUT)
                return data.json()[extract_field]
            except Exception as e:
                print(f"Failed to retrieve APIi {i}/{cls.settings.MAX_REQUEST_RETRIES}: {url}\n{e}")
                sleep(2)
        return {}


    def __create_new_ticket(cls, ticket_object):
        resp = post(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/tickets", 
                    headers=cls.FRESH_HEADER, 
                    json=ticket_object,
                    auth=(cls.settings.FRESH_KEY, "X"))
        if resp.status_code != 201:
            print(f"Ticket was not created.\nResponse code {resp.status_code},\nmessage: {resp.json()}")
        else:
            print(f"Ticket successfully created")
            print(resp.json())

    
    def __delete_software(cls, software_id_list:list[int]=[]):
        for software_id in software_id_list:
            count = len(cls.SoftwareRegister[software_id]["users"]) + len(cls.SoftwareRegister[software_id]["installs"]) + len(cls.SoftwareRegister[software_id]["licenses"])
            if count > 0:
                continue
            resp = delete(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/applications/{software_id}",
                          headers=cls.settings.FRESH_HEADER,
                          auth=(cls.settings.FRESH_KEY, "X"),
                          timeout=5)
            if resp.status_code != 204:
                print(f"Could not delete: {cls.VendorRegister[cls.SoftwareRegister[software_id]['publisher_id']]['name']} - {cls.SoftwareRegister[software_id]['name']}")
                return False
            else:
                print(f"Deleted: {cls.VendorRegister[cls.SoftwareRegister[software_id]['publisher_id']]['name']} - {cls.SoftwareRegister[software_id]['name']}")
        return True


    def __load_cache(cls, CACHE_TYPE:str):
        if CACHE_TYPE not in cls.ENUM_CACHE:
            raise KeyError(f"Key '{CACHE_TYPE}' does not exist")
        print(f"Loading cache: {CACHE_TYPE}")
        try:
            with open(cls.ENUM_CACHE[CACHE_TYPE], "r") as cache_fh:
                if CACHE_TYPE == "VENDOR":
                    temp_data = json.load(cache_fh)
                elif CACHE_TYPE == "SOFTWARE":
                    temp_data = json.load(cache_fh)
                return temp_data
        except Exception as e:
            print(e)
        return {}
            

    def __save_cache(cls, CACHE_TYPE):
        if CACHE_TYPE not in cls.ENUM_CACHE:
            raise KeyError(f"Key '{CACHE_TYPE}' does not exist")
        print(f"Saving cache: {CACHE_TYPE}")
        try:
            with open(cls.ENUM_CACHE[CACHE_TYPE], "w") as cache_fh:
                if CACHE_TYPE == "VENDOR":
                    json.dump(cls.VendorRegister, cache_fh)
                elif CACHE_TYPE == "SOFTWARE":
                    json.dump(cls.SoftwareRegister, cache_fh)
                return True
        except Exception as e:
            print(e)
        return False


    def get_vendors(cls, update_cache:bool=False):
        print("Fetching: Vendors")
        if not update_cache:
            cls.VendorRegister = cls.__load_cache(CACHE_TYPE="VENDOR")
        
        if update_cache or not cls.VendorRegister:
            cls.VendorRegister.update({"UNREGISTERED": {"name": "UNREGISTERED", "software":[]}})
            vendor_list = cls.__get_paginated_api(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/vendors", "vendors")
            for vendor in vendor_list:
                cls.VendorRegister.update({vendor["id"]: {"name": vendor["name"], "software":[]}})
            cls.__save_cache("VENDOR")


    def get_software(cls, vendor_id_list:list[str]=[], software_id_list:list[str]=[], update_cache:bool=False):
        print("Fetching: Applications")
        if not update_cache:
            cls.SoftwareRegister = cls.__load_cache(CACHE_TYPE="SOFTWARE")
            
        if update_cache or not cls.SoftwareRegister:
            software_list = cls.__get_paginated_api(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/applications", "applications")
            for software in software_list:
                software["id"] = str(software["id"])
                if not software["publisher_id"]:
                    software["publisher_id"] = "UNREGISTERED"
                else:
                    software["publisher_id"] = str(software["publisher_id"])
                cls.SoftwareRegister.update({software["id"]:{
                                                "name": software["name"],
                                                "publisher_id": software["publisher_id"],
                                                "category": software["category"], 
                                                "status": software["status"],
                                                "users": [],
                                                "installs": [],
                                                "licenses": []}
                                            })
            cls.__save_cache("SOFTWARE")
        for software_id, software in cls.SoftwareRegister.items():
            cls.VendorRegister[software["publisher_id"]]["software"].append(software_id)


    def get_software_users(cls, software_id_list:list[str]=[]):
        print("Expanding applications w/users")
        for software_id in software_id_list:
            data = cls.__get_paginated_api(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/applications/{software_id}/users/e", "application_users")
            cls.SoftwareRegister[software_id] = [{"user": app["user_id"],
                                                "license": app["license_id"],
                                                "state": app["state"], 
                                                "last_use": app["last_used"]} for app in data]


    def get_software_licenses(cls, software_id_list:list[str]=[]):
        print("Expanding applications w/users")
        for software_id in software_id_list:
            data = cls.__get_paginated_api(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/applications/{software_id}/licenses", "licenses")
            cls.SoftwareRegister[software_id]["licenses"] = [{"license": app["id"], "contract_id": app["contract_id"]} for app in data]


    def get_software_installs(cls, software_id_list:list[str]=[]):
        print("Expanding applications w/users")
        for software_id in software_id_list:
            data = cls.__get_paginated_api(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/applications/{software_id}/installations/", "installations")
            for app in data:
                asset_info = cls.__get_api(f"https://{cls.settings.FRESH_DOMAIN}/api/v2/assets/{app['installation_machine_id']}?include=type_fields", "asset")
                lcl_description = None
                if asset_info and "description" in asset_info and asset_info["description"]:
                    lcl_description = BeautifulSoup(asset_info["description"], "lxml").text.replace("\n", "  |  ").strip()
                lcl_asset_info = None
                if asset_info and "asset_state_11000765764" in asset_info["type_fields"]:
                    lcl_asset_info = asset_info["type_fields"]["asset_state_11000765764"]
                cls.SoftwareRegister[software_id]["installs"].append({"path": app["installation_path"],
                                                        "version": app["version"], 
                                                        "user": app["user_id"],
                                                        "name": asset_info["name"] if asset_info else None,
                                                        "description": lcl_description,
                                                        "status": lcl_asset_info,
                                                        "machine": app["installation_machine_id"]
                                                    })


    def list_software(cls, vendor_id_list:List[str]=[], software_id_list:List[str]=[]):
        if not vendor_id_list and not software_id_list:
            for vendor_id, vendor in cls.VendorRegister.items():
                print(f"{vendor_id} - {vendor['name']}")
                for software_id in vendor['software']:
                    print(f"\t{software_id} - {cls.SoftwareRegister[software_id]['name']}")        
        elif vendor_id_list:
            for vendor_id in vendor_id_list:
                print(f"{vendor_id} - {cls.VendorRegister[vendor_id]['name']}")
                for software_id in cls.VendorRegister[vendor_id]['software']:
                    if software_id_list and software_id not in software_id_list:
                        continue
                    print(f"\t{software_id} - {cls.SoftwareRegister[software_id]['name']}")
        elif software_id_list:
            for software_id in software_id_list:
                print(f"{cls.SoftwareRegister[software_id]['publisher_id']} - {cls.VendorRegister[cls.SoftwareRegister[software_id]['publisher_id']]['name']} - {software_id} - {cls.SoftwareRegister[software_id]['name']}")


    def filter_software(cls, filter_software:List[str]=[]):
        software_ids = []
        for key,software in cls.SoftwareRegister.items():
            for filter in filter_software:
                if filter in software["name"].lower():
                    software_ids.append(key)
                    break
        return software_ids


    def filter_vendors(cls, filter_vendor:List[str]=[]):
        vendor_ids = []
        for key,vendor in cls.VendorRegister.items():
            for filter in filter_vendor:
                if filter in vendor["name"].lower():
                    vendor_ids.append(key)
                    break
        return vendor_ids


    def list_vendors(cls, vendor_id_list:List[str]=[]):
        if vendor_id_list:
            for vendor_id in vendor_id_list:
                print(f"{vendor_id} - {cls.VendorRegister[vendor_id]['name']}")
        else:
            for key, vendor in cls.VendorRegister.items():
                print(f"{key} - {vendor['name']}")


    def list_templates(cls):
        cls.__load_templates()
        print("Defined FreshService template")
        for template_key in cls.FRESH_TEMPLATES:
            print(f"\t{template_key}: {cls.FRESH_TEMPLATES[template_key]['subject']}")
    

    def generate_ticket(cls, subject: str, message: str, template_name:str = "DEFAULT"):
        cls.__load_templates()

        if template_name not in cls.FRESH_TEMPLATES:
            print(f"Template not found: '{template_name}'")
            cls.list_templates()
            return
        
        ticket_object = cls.FRESH_TEMPLATES["DEFAULT"]
        ticket_object["email"] = cls.settings.FRESH_DEFAULT_CONTACT_EMAIL
        ticket_object["cc_emails"].append(cls.settings.FRESH_DEFAULT_CONTACT_EMAIL)
        ticket_object["department_id"] = cls.settings.FRESH_DEFAULT_DEPT_ID
        ticket_object["group_id"] = cls.settings.FRESH_DEFAULT_GROUP_ID
        ticket_object["category"] = cls.settings.FRESH_DEFAULT_CATEGORY

        ticket_object["subject"] = subject.strip() if subject else cls.settings.FRESH_DEFAULT_SUBJECT
        
        for key,value in cls.FRESH_TEMPLATES[template_name].items():
            ticket_object.update({key:value})

        if exists(message) and isfile(message):
            with open(message) as message_fh:
                ticket_object["description"] = markdown.markdown(message_fh.read().strip())
        else:
            ticket_object["description"] = markdown.markdown(message.strip())
        
        if not ticket_object["description"].strip():
            raise ValueError("Missing ticket content: description")
        
        print(json.dumps(ticket_object, indent=2))

        #cls.__create_new_ticket(ticket_object=ticket_object)
        

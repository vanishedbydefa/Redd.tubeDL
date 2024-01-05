import os
import time
import re
import requests
from bs4 import *
import cloudscraper


from database import check_db_exists

def get_time():
    return time.strftime('[%H:%M:%S]')

def get_timestamp():
    return time.time()


def create_urls(page_from:int, category:str):
    if page_from == None:
        page_from = 1
    url = "http://www.redd.tube"
    page_url = url+"/category/"+category+"/"+str(page_from)


    scraper = cloudscraper.CloudScraper()
    response = scraper.get(page_url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all elements with class 'row' (adjust as per the class name in your HTML)
        links = soup.find_all('a', class_='nav-link')
        names = soup.find_all('h4', class_='h5 g-color-black g-font-weight-600 g-mb-10 g-mt-5 g-color-primary--hover text-truncate')

        # Extract content inside every 'row' class
        video_links = []
        for i,link in enumerate(links):
            _link = str(link.get('href'))
            if _link[:6] == "/video":
                time.sleep(5)
                video_page_response = scraper.get(url + str(link.get('href')))
                if video_page_response.status_code == 200:
                    soup = BeautifulSoup(video_page_response.content, 'html.parser')
                    video_mp4_link = soup.find_all('source')
                    print(video_mp4_link[0].get("src"))
                    if len(video_mp4_link) > 1:
                        print("Unknown links found on videos page")
                        continue
                    elif len(video_mp4_link) < 1:
                        print("No video link found")
                        continue
                    else:
                        try:
                            video_links.append([names[i].text,_link[7:], video_mp4_link[0].get("src")])
                        except IndexError:
                            print(f"ERROR: No name found for video {_link}")
                else:
                    print('Failed to fetch the webpage')
            else:
                links.remove(link)
        return video_links
    elif response.status_code == 429:
        print('You are downloading too fast and redd.tube temporary blocked you')
        return False
    else:
        print('Failed to fetch the webpage')
    return None


def check_path_exists(path:str, create=False):
    '''
    Check wether path exists or not.
    If path do not exist but create=True,
    create a directory.
    '''
    path_exist = os.path.exists(path)
    if path_exist:
        return True

    #path do not exist, try to create it
    if create:
        try:
            os.makedirs(path)
            return True
        except OSError as e:
            print(f"Failed to create directory: {path}")
            print(f"Error: {e}")
            return False
    return False


def initial_checks(param_path:str, db_path:str, category:str):
    ##check specified path to folder and create if it do not exist
    if check_path_exists(param_path, create=True):
        print(f'    - Folder path at {param_path} is valid')
    else:
        print(f"\nError:\nThe folder where to store downloaded videos "
            f"do not exist and couldn't be created. Please check \n"
            f"the correctness of the provided path: "
            f"{param_path}.")
        exit(1)
    
    ##check if the db exist and create if it do not exist
    check_db_exists(db_path, category)


def exe_helper():
    path = input("Enter path where to store the images: ")
    path = str(path)
    print("Path set to: ", path)

    while True:
        try:
            threads = input("Enter a number of threads to download [1-10]: ")
            threads = int(threads)
            if threads <= 0 or threads >10:
                print("Invalid input! Please enter a number between 1 and 10")
                continue
            print("Threads set to: ", threads)
            break
        except ValueError:
            print("Invalid input! Please enter a number between 1 and 10")

    while True:
        force = input("Do you want to force download even an image may already exist? [y/n]: ")
        if force not in ["y", "Y", "j", "J", "yes", "Yes", "n", "N", "no", "No"]:
            print("Type 'y' to force download or 'n' to do not: ")
            continue
        elif force in ["y", "Y", "j", "J", "yes", "Yes"]:
            force = True
            break
        elif force in ["n", "N", "no", "No"]:
            force = False
            break
    
    while True:
        beginning = input("Do you want to start downloading from 0? [y/n]: ")
        if beginning not in ["y", "Y", "j", "J", "yes", "Yes", "n", "N", "no", "No"]:
            print("Type 'y' to not continue where you stoped last time or 'n' to do so: ")
            continue
        elif beginning in ["y", "Y", "j", "J", "yes", "Yes"]:
            beginning = True
            break
        elif beginning in ["n", "N", "no", "No"]:
            beginning = False
            break

    category = input("Which category you wish to download videos from?: ")

    while True:
        proxie = input("Do you want to use a proxie? [y/n]: ")
        if proxie not in ["y", "Y", "j", "J", "yes", "Yes", "n", "N", "no", "No"]:
            print("Type 'y' to force download or 'n' to do not: ")
            continue
        elif proxie in ["y", "Y", "j", "J", "yes", "Yes"]:
            proxie = input("Input proxies IP: ")
            break
        else:
            proxie = None
            break
    return path, threads, force, beginning, category, proxie
        

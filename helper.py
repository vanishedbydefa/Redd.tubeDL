import os
import time
from bs4 import *
import cloudscraper
import string
import unicodedata
import random


from database import check_db_exists, check_db_entry_exists

def get_time():
    return time.strftime('[%H:%M:%S]')

def get_timestamp():
    return time.time()

def clean_filename(filename):
    valid_chars = "-_() %s%s" % (string.ascii_letters, string.digits)
    cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
    cleaned_filename = ''.join(c for c in cleaned_filename if c in valid_chars)
    cleaned_filename = cleaned_filename.replace(' ', '')  # Remove spaces
    cleaned_filename = cleaned_filename.replace('.', '')  # Remove dots
    if cleaned_filename == "" or len(cleaned_filename) <= 3:
        cleaned_filename += "_"
        cleaned_filename += ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
    return cleaned_filename


def create_urls(page_from:int, category:str, db_path:str, path:str, force:bool):
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

        # Find all video elements but ignore the featured ones
        link_container = soup.find('section', class_='container g-pb-40')
        soup = BeautifulSoup(link_container.prettify(), 'html.parser')

        links = soup.find_all('a', class_='nav-link')
        names = soup.find_all('h4', class_='h5 g-color-black g-font-weight-600 g-mb-10 g-mt-5 g-color-primary--hover text-truncate')

        # Filter non video urls
        for link in links:
            if str(link.get('href'))[:6] != "/video":
                links.remove(link)
        
        # Check for already downloaded videos to reduce requests
        if not force:
            for i,name in enumerate(names):
                cleaned_filename = clean_filename(name.text)
                db_entry_exist = check_db_entry_exists(db_path, category, name=cleaned_filename)
                file_exist = check_path_exists(f'{path}/{cleaned_filename}.mp4')
                if db_entry_exist and file_exist:
                    names.remove(name)
                    links.pop(i)
                    print(f'INFO: "{cleaned_filename}" already in DB')

        # Extract content inside every 'row' class
        video_links = []
        for i,link in enumerate(links):
            _link = str(link.get('href'))
            time.sleep(4)
            video_page_response = scraper.get(url + str(link.get('href')))
            if video_page_response.status_code == 200:
                soup = BeautifulSoup(video_page_response.content, 'html.parser')
                video_mp4_link = soup.find_all('source')
                print(f'Added {names[i].text} = {video_mp4_link[0].get("src")} to the queue')
                if len(video_mp4_link) > 1:
                    print("Unknown links found on videos page")
                    continue
                elif len(video_mp4_link) < 1:
                    print("No video link found")
                    continue
                else:
                    try:
                        video_links.append([clean_filename(names[i].text),_link[7:], video_mp4_link[0].get("src")])
                    except IndexError:
                        print(f"ERROR: No name found for video {_link}")
            else:
                print('Failed to fetch the webpage')
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
        

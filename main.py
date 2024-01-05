import argparse
import threading
import queue
import requests
import re
import signal
import time
import sys
import os

from helper import get_time,initial_checks, create_urls, get_timestamp, check_path_exists, exe_helper
from database import insert_or_update_entry, check_db_entry_exists, get_max_page_from_db

STOP_THREADS = False

threads = []

db_semaphore = threading.Semaphore(1)
threads_remove_semaphore = threading.Semaphore(1)
threads_semaphore = None

def download_video(url:list, path:str, db_path:str, category:str, page:int, force:bool, proxie:dict):
    global db_semaphore
    title = url[0]
    vid_id = url[1]
    vid_url = url[2]

    # Check if db entry exist in case download is not forced
    if not force and check_db_entry_exists(db_path, category, vid_id):
        return True
    
    #TODO check if 429

    # Download the image, save it and add entry to DB
    r = requests.get(vid_url, headers = {'User-agent': 'faproulette-dl'}, proxies=proxie)
    if r.status_code == 200:         
        file_extension = ".mp4"

        # Check if image with this name already exist
        if check_path_exists(f"{path}/{title}{file_extension}"):
            title += str(vid_id[:5])

        # After checking above condition, Image Download start
        with open(f"{path}/{title}{file_extension}", "wb+") as f:
            f.write(r.content)

        # Write data to db
        db_semaphore.acquire()
        insert_or_update_entry(db_path, vid_id, title, category, page, get_timestamp(), vid_url)
        db_semaphore.release()
    else:
        print("Download failed")
    return True

def video_downloader(path:str, db_path:str, category:str, page:int, force:bool, url_queue, proxie):
    '''
    Put a url from the queue of urls and
    download it. Return and join thread if queue
    is empty. 
    '''
    global STOP_THREADS
    if not STOP_THREADS:
        try:
            time.sleep(2)
            url = url_queue.get(timeout=1)  # Get a URL from the queue
            if not download_video(url, path, db_path, category, page, force, proxie):
                url_queue.task_done()
                if STOP_THREADS:
                    return
                print("Downloading too fast. Shutting down now!                               ")
                STOP_THREADS = True
                threads_semaphore.release()
                return
            url_queue.task_done()
        except queue.Empty:
            pass
    threads_semaphore.release()
    return

# Function to gracefully stop the program on CTRL + C
def stop_program(signum, frame, url_queue):
    global STOP_THREADS, threads, threads_semaphore, threads_remove_semaphore
    STOP_THREADS = True
    if signum != None:
        print("Ctrl + C detected. Emptying queue")
    else:
        print("Internal Call for program termination")

    print("Clearing queue: ", end="")
    url_queue.mutex
    while not url_queue.empty():
        url_queue.get()
        url_queue.task_done()
    print("Done")

    print("Clearing threads: ", end="")
    time.sleep(2)
    threads_remove_semaphore.acquire()
    for thread in threads:
            thread.join()
            threads.remove(thread)
            threads_semaphore.release()
    threads_remove_semaphore.release()
    print("Done")

    print(f"{get_time()} Thanks for using Faproulette-Downloader")
    sys.exit(0)


def main():
    global STOP_THREADS
    parser = argparse.ArgumentParser(prog='Faproulette-Downloader', description='Download all faproulettes on faproulette.co', epilog='https://github.com/vanishedbydefa')
    parser.add_argument('-p', '--path', default=str(os.getcwd()), type=str, help='Path to store downloaded images')
    parser.add_argument('-t', '--threads', choices=range(1, 11), default=3, type=int, help='Number of threads downloading images')
    parser.add_argument('-f', '--force', action='store_true', help='Overwrite existing images if True')
    parser.add_argument('-b', '--beginning', action='store_true', help='Start downloading from 0')
    parser.add_argument('-c', '--category', type=str, help='category to download videos from', required=True)
    parser.add_argument('-x', '--proxie', type=str, default=None, help='Enter proxies IP/domain to circumvent 429 errors. Http Proxies only!')

    args = parser.parse_args()
    param_path = args.path       
    param_threads = args.threads
    param_force = args.force
    param_beginning = args.beginning
    param_category = args.category
    param_proxie = args.proxie

    # Check if running as exe
    if sys.argv[0][-4:] == ".exe":
        if not check_path_exists(param_path+"\\main.exe", create=False):
            print("Please start program in the folder where main.exe is stored")
            sys.exit(0)
        param_path, param_threads, param_force, param_beginning, param_category, param_proxie = exe_helper()

    # Set remaining args, may modified in case running the exe
    db_path = param_path + "\\video_data.db"
    if param_proxie != None: 
        proxie = {'http': 'http://' + param_proxie + ':80'}
    else:
        proxie = None

    # Startup checks
    print(f'{get_time()} Running startup checks to ensure correct downloading:')
    initial_checks(param_path, db_path, param_category)
    print(f'{get_time()} Start downloading with {param_threads} threads into "{param_path}"')
    print('\n\nExit the Program with CTRL + C - This exits safely but may needs some time to finish running threads\n\n')

    # Create a queue with the video URLs from current page
    start_page = 1
    if not param_beginning:
        start_page = get_max_page_from_db(db_path, param_category) + 1
    
    while not STOP_THREADS:
        print(f'{get_time()} Downloading page: {str(start_page)}')

        url_queue = queue.Queue()
        urls = create_urls(page_from=start_page, category=param_category, db_path=db_path, path=param_path, force=param_force)
        if urls == False:
            print("Terminating program")
            STOP_THREADS = True
            return
        elif urls == None:
            print("Unknown error occured, program will continue")

        for url in urls:
            url_queue.put(url)

        # Thread logic
        global threads_semaphore, threads, threads_remove_semaphore
        threads_semaphore = threading.Semaphore(param_threads)

        while int(url_queue.qsize()) != 0:
            print(f"Remaining videos: {str(url_queue.qsize())} get downloaded by {str(param_threads)}/{str(len(threads))} Threads      ", end='\r')
            threads_semaphore.acquire()
            thread = threading.Thread(target=video_downloader, args=(param_path, db_path, param_category, start_page, param_force, url_queue, proxie,))
            thread.start()
            threads.append(thread)
            
            for thread in threads:
                if not thread.is_alive():
                    thread.join()
                    threads_remove_semaphore.acquire()
                    threads.remove(thread)
                    threads_remove_semaphore.release()

            # Register signal handler for Ctrl + C
            signal.signal(signal.SIGINT, lambda sig, frame: stop_program(sig, frame, url_queue))

            if STOP_THREADS:
                stop_program(None, None, url_queue)

        threads_remove_semaphore.acquire()
        for thread in threads:
            thread.join()
            threads.remove(thread)
            threads_semaphore.release()
        threads_remove_semaphore.release()
        
        print(f"{get_time()} All threads terminated")
        start_page += 1
    print(f"{get_time()} Program done")

main()    

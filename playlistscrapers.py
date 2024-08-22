import math
import os
import smtplib
import statistics
import sys
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from threading import Thread

import pandas as pd
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def append_row(df, row):
    return pd.concat([df, pd.DataFrame([row], columns=row.index)]
                     ).reset_index(drop=True)


def send_email_notification(recipient, subject, message, attachment_path):
    sender_email = 'aidanalrawi@icloud.com'
    smtp_key = 'H7qhF8DV2ysktrv0'
    recipient_email = recipient

    # Setup the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    # Attach the CSV file
    with open(attachment_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        f'attachment; filename= {os.path.basename(attachment_path)}'
    )
    msg.attach(part)

    # Connect to the SMTP server
    try:
        server = smtplib.SMTP('smtp-relay.brevo.com', 587)
        server.starttls()
        server.login(sender_email, smtp_key)
    except Exception as e:
        print("Failed to connect to SMTP server:", e)
        return False

    # Send the email
    try:
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email notification sent successfully to:", recipient_email)
        return True
    except Exception as e:
        print("Failed to send email:", e)
        return False
    finally:
        server.quit()


def convert_seconds_to_time_str(seconds):
    minutes = math.floor(seconds / 60)
    seconds = math.floor(seconds % 60)
    return f"{minutes}m:{seconds}s"


def extract_after_last_slash(url):
    parts = url.split('/')
    return parts[-1]


def parse_img_link(link):
    """
    This function takes in the image link and returns the song page
    :param link:
    :return:

    Example
    https://assets.soundcharts.com/song/c/6/a/399221ee-3a6c-454c-ae79-23024d428f30.jpg
    https://app.soundcharts.com/app/song/399221ee-3a6c-454c-ae79-23024d428f30/playlists?playlist-categories=algorithmic.charts.curators_listeners.editorial.algotorial.major.this_is
    """
    link: str = extract_after_last_slash(link.get_attribute("src")).rstrip(".jpg")
    result = "https://app.soundcharts.com/app/song/" + link + "/overview"
    return result


def parse_rank(rank):
    return [s.text for s in rank]


def scroll(driver, scroll_amount):
    if scroll_amount == 0:
        return
    try:
        time.sleep(0.5)
        element = WebDriverWait(driver, 10).until(
            lambda drvr: drvr.find_element(By.CSS_SELECTOR, "div.sc-fjdPjP.bJUVjG.custom-scrollbar"))
        if element:
            driver.execute_script("arguments[0].scrollTop += arguments[0].scrollHeight*0.2*arguments[1]", element,
                                  scroll_amount)
            time.sleep(0.5)
    except Exception:
        print("Could not scroll")


def extract_names(names):
    joined_names = []
    result = ""
    for name in names:
        if name == "•":
            result += "/"
        else:
            if result:
                if result[-1] == "•":
                    result += "/"
                else:
                    joined_names.append(result)
                    result = name
            else:
                result += name

    joined_names.append(result)

    return joined_names


class Link:
    def __init__(self, chart_type, country, platform, filters=None, custom_url=None):
        charts = {
            "spotify": "",
            "apple-music": "top-100-global",
            "shazam": "shazam-top-200-world",
            "soundcloud": "all-genres"
        }
        self.filters_dict = {
            # "no_labels": "eyJmbHQiOiJTZWxmIHJlbGVhc2VkfFVua25vd24ifQ%3D%3D",
            "no_labels": "eyJmc2ciOiJBTExfR0VOUkVTIiwiZmx0IjoiU2VsZiByZWxlYXNlZHxVbmtub3duIn0%3D",

        }
        self.chart = charts[platform]
        self.chart_type = chart_type
        self.country = country
        self.platform = platform
        self.filters = self.filters_dict[filters] if filters else ""

        self.link_string = f"https://app.soundcharts.com/app/market/charts?chart={self.chart}&chart_type={self.chart_type}&country={self.country}"
        if self.platform == "spotify":
            self.link_string += "&period=1"
        if self.filters:
            self.link_string += f"&filters={self.filters}"
        self.link_string += f"&platform={self.platform}"

        if custom_url:
            self.link_string = custom_url


def remove_substring_from_string(substring, string):
    return string.replace(substring, "")


def parse_labels(labels):
    labels = [div.text for div in labels]
    labels = [remove_substring_from_string("Unknown", label) for label in labels]
    labels = [remove_substring_from_string("Self released", label) for label in labels]
    labels = [label.replace("\n", "-") for label in labels]
    return labels


def parse_genre(genre):
    songs_and_genres = [div.text for div in genre]

    genre_list = ["Pop", "Rock", "Hip Hop", "Rap", "R&B", "Soul", "Jazz", "Blues", "Country", "Folk", "Reggae", "Dance",
                  "Electronic",
                  "Classical", "Metal", "Punk", "Indie", "Alternative", "World", "Latin", "K-Pop", "J-Pop", "Anime",
                  "Soundtrack",
                  "Children's Music", "Electro", "Latin", "Asian", "R&B", "Soul", "Funk", "Disco", "House", "Techno",
                  "Trance", "Dubstep",
                  "African", "American", "Asian", "European", "Indian", "Middle Eastern", "Oceanian", "Caribbean",
                  "Latin American",
                  "Instrumental", "Spirituals", "Spoken", "Sports", "Others", "Unknown", "Mena"]

    def remove_before_first_newline(s):
        parts = s.split("\n")  # split the string into two parts at the first newline
        parts = [part.strip() for part in parts if part in genre_list]
        return "-".join(parts)  # join the parts back together with a hyphen

    genres = [remove_before_first_newline(song) for song in songs_and_genres]
    return genres


def parse_songs(songs_and_genre):
    songs_and_genres = [div.text for div in songs_and_genre]
    songs = [div.split("\n", 1)[0] for div in songs_and_genres]
    return songs


def take_data_return_df(driver) -> pd.DataFrame():
    """
    This function extracts data from a webpage and returns it as a pandas DataFrame.

    Parameters:
    driver (webdriver): The selenium webdriver instance to interact with the webpage.

    Returns:
    pd.DataFrame: A DataFrame containing the extracted data from the webpage.

    """

    # CSS selectors for different elements on the webpage
    general_css_selector = {
        "songs": "div.sc-eTuwsz.jWHscE",
        "artists": "div.sc-esOvli.cfpVgy",
        "links": "img.sc-epnACN.ksrdaN",
        "rank": "div.sc-ihiiSJ.jCUAzS",
        "labels": "div.sc-iBfVdv.iCudrb",
        "change": "div.sc-gGCbJM.fAEtBo",
        "genre": "div.sc-eTuwsz.jWHscE"
    }

    # Find elements on the webpage using the CSS selectors
    songs = driver.find_elements(By.CSS_SELECTOR, general_css_selector["songs"])
    links = driver.find_elements(By.CSS_SELECTOR, general_css_selector["links"])
    artists = driver.find_elements(By.CSS_SELECTOR, general_css_selector["artists"])
    rank = driver.find_elements(By.CSS_SELECTOR, general_css_selector["rank"])
    labels = driver.find_elements(By.CSS_SELECTOR, general_css_selector["labels"])
    change = driver.find_elements(By.CSS_SELECTOR, general_css_selector["change"])
    genre = driver.find_elements(By.CSS_SELECTOR, general_css_selector["genre"])

    # Check if all elements have the same length
    if len(songs) == len(artists) == len(links) == len(rank) == len(labels) == len(change) == len(genre):
        # Parse the elements into lists
        songs = parse_songs(songs)
        links = [parse_img_link(link) for link in links]
        artists = extract_names([div.text for div in artists])
        rank = parse_rank(rank)
        labels = parse_labels(labels)
        change = [div.text for div in change]
        genre = parse_genre(genre)

        # Create a dataframe with the parsed data
        df = pd.DataFrame()
        df["rank"] = rank
        df["Song"] = songs
        df["Artists"] = artists
        df["Labels"] = labels
        df["Link"] = links
        df["Change"] = change
        df["Genre"] = genre

        return df

    else:
        print("Songs:", len(songs), "Artists:", len(artists), "Links:", len(links), "Rank:", len(rank),
              "Labels:", len(labels), "Change:", len(change), "Genre:", len(genre))


def parse_webpage(driver, url) -> pd.DataFrame():
    """
    This function parses a webpage and extracts relevant data into a pandas DataFrame.

    Parameters:
    driver (webdriver): The selenium webdriver instance to interact with the webpage.
    url (str): The URL of the webpage to parse.

    Returns:
    pd.DataFrame: A DataFrame containing the parsed data from the webpage.

    """

    # Navigate to the specified URL
    driver.get(url)

    # Pause the execution for 6 seconds to allow the webpage to load
    time.sleep(6)

    result = []

    # Scroll the webpage 5 times to load more data
    scroll_count = 7
    for _ in range(scroll_count):
        # Pause the execution for 0.25 seconds between each scroll
        time.sleep(0.25)

        # Scroll the webpage and append the extracted data to the result list
        scroll(driver, 1)
        result.append(take_data_return_df(driver))

    # Concatenate all the dataframes in the result list into a single dataframe
    result_df = pd.concat(result, axis=0)

    # Remove songs with specified labels and more than 30 days on chart
    result_df = remove_songs_with_labels_from_df(result_df)

    # Filter out songs with more than 1 artist
    result_df = result_df[~result_df["Artists"].str.contains("\n")]
    # Remove duplicate songs, keeping only the first occurrence
    result_df = result_df.drop_duplicates(subset="Song", keep="first")

    print("Parsing webpage (Successful) ->")
    print(url)
    return result_df


def login_to_new_driver(detach=False) -> webdriver.Chrome():
    while True:
        try:
            options = Options()
            if detach:
                options.add_experimental_option("detach", True)

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            driver.get("https://app.soundcharts.com/login")
            driver.maximize_window()

            # Find the username and password input fields by name
            username_input = driver.find_element(By.NAME, "email")
            password_input = driver.find_element(By.NAME, "password")

            # Enter username and password
            username_input.send_keys("jhlevy01@gmail.com")
            password_input.send_keys("pogg4$33a!")

            # Find and click the login button
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()

            print("Logged in")
            # Wait for the page to load
            time.sleep(15)

            if "app.soundcharts.com/login" not in driver.current_url:
                print("Successfully logged in")
                return driver

        except Exception:
            print("Could not log in, trying again in 5 seconds")
            time.sleep(5)


def remove_songs_with_labels_from_df(df):
    labels_to_remove = ["sony", 'umg', 'warner', 'independent', 'universal', 'warner music', 'sony music',
                        'universal music', "yzy", "Island",
                        "Def Jam",
                        "Republic", "Interscope", "Atlantic", "Columbia", "Capitol", "RCA", "Epic", "Sony Music",
                        "Warner Music", ]
    # Remove songs with labels in the list, check with lowercase
    for label in labels_to_remove:
        df = df[~df["Labels"].str.lower().str.contains(label.lower())]

    return df


def change_to_spotify(link):
    link = link.replace("overview", "trends")
    return link


def locate_and_move_to_spotify_chart(driver):
    charts = WebDriverWait(driver, 4).until(
        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "path.recharts-curve.recharts-line-curve")))
    charts = min(charts, key=lambda x: x.location['x'] + x.location['y'])
    ActionChains(driver).move_to_element(charts).perform()
    tooltip_size = charts.size
    return tooltip_size


def get_streams(link, driver) -> (str, str, str):
    attempts = 0
    while attempts < 3:
        streams = ""
        total_streams = []
        try:
            attempts += 1
            driver.get(link)
            time.sleep(5)

            # Find the parent element and move to it
            tooltip_size = locate_and_move_to_spotify_chart(driver)

            # Find the child element which holds the stream data
            mouse_shifts = 14
            for _ in range(mouse_shifts):
                # Move the mouse horizontally by 20% of the tooltip wrapper size
                if streams:
                    horizontal_move = tooltip_size['width'] * 0.04
                    ActionChains(driver).move_by_offset(horizontal_move, 0).perform()

                child_elements = driver.find_elements(By.CSS_SELECTOR, "div.sc-laTMn.ktlmrZ")
                child_elements = [element.text for element in child_elements][0].split("\n")
                date, daily_streams = child_elements[0], child_elements[-1]
                daily_streams = daily_streams.split(" ")[-1].replace(",", "")
                streams += f"{date} - {daily_streams}\n"

                if len(child_elements) > 2:
                    total_streams.append(child_elements[1].split(" ")[-1].replace(",", ""))

            if not total_streams:
                total_streams.append("0")

            return streams, total_streams[-1], get_artist_page_link(driver)

        except Exception as e:
            print("Could not get streams for:" + link)
            if attempts == 3:
                return "Error", "Error", "Error"


def get_artist_page_link(driver):
    artist_page_link = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "a.sc-EHOje.iAfflV"))).get_attribute("href")
    return artist_page_link


def get_spotify_followers_and_total_fans(link, driver):
    fans = ""
    spotify = ""
    try:
        driver.get(link)
        time.sleep(5)
        followers = WebDriverWait(driver, 10).until(
            lambda drvr: drvr.find_elements(By.CSS_SELECTOR, "div.sc-dBaXSw.bHhScY.social-evolution-details.clickable"))
        followers = [div.text for div in followers]
        spotify_followers = [follower for follower in followers if "spotify" in follower.lower()]

        if spotify_followers:
            spotify = spotify_followers[0].split("\n")[1].replace(",", "")

        total_fans = driver.find_element(By.CSS_SELECTOR, "div.sc-dUjcNx.VujJl")
        if total_fans and "Total fans" in total_fans.text:
            total_fans = total_fans.text.split("\n")[1].replace(",", "")
            fans = total_fans

    except Exception:
        print("Could not get total fans or followers for:" + link)

    return spotify, fans


def parse_streams_into_columns(df):
    try:
        if df.empty:
            return None
        # Split the "Streams" column into separate columns for each date
        streams_df = df["Streams"].str.split("\n", expand=True)
        streams_df = pd.DataFrame(streams_df)
        streams_df.drop(streams_df.columns[-1], axis=1, inplace=True)

        # Extract column names from first row with all the dates
        # Find a full row with dates
        for i in range(len(streams_df)):
            if streams_df.iloc[i].str.contains(" - ").all():
                date_df = streams_df.iloc[i:]
                break

        # Set the first row as the column names
        streams_df.columns = date_df.iloc[0].str.split(" - ", expand=True)[0]

        # Drop last column
        streams_df = streams_df.drop(streams_df.columns[-1], axis=1)

        # Remove the dates from cells
        streams_df = streams_df.map(lambda x: x.split(" - ")[-1] if x else x)
        streams_df = streams_df.map(
            lambda x: x.replace(",", "") if isinstance(x, str) and x.replace(",", "").isdigit() else x)
        streams_df = streams_df.apply(pd.to_numeric, errors='coerce')

        last_day = streams_df[streams_df.columns[-1]]
        last_3_days_avg = streams_df[streams_df.columns[-3:]].mean(axis=1)

        temp_3_day = ((last_day - streams_df[streams_df.columns[-4]]) / streams_df[streams_df.columns[-4]] * 100)
        temp_5_day = (last_day - streams_df[streams_df.columns[-6]]) / streams_df[streams_df.columns[-6]] * 100
        temp_10_day = (last_day - streams_df[streams_df.columns[-11]]) / streams_df[streams_df.columns[-11]] * 100

        new_df = pd.DataFrame()
        new_df["Yesterday"] = streams_df[streams_df.columns[-2]]
        new_df["3_day_avg"] = last_3_days_avg
        new_df["3_day_%_change"] = temp_3_day
        new_df["5_day_%_change"] = temp_5_day
        new_df["10_day_%_change"] = temp_10_day

        for column in new_df.columns:
            # round if the value is a float and not infinite
            new_df[column] = new_df[column].apply(lambda x: round(x, 2) if x and not math.isinf(x) else x)

        return new_df
    except Exception as e:
        print("Could not parse streams into columns")
        print(e)


def reverse_streams_column(df):
    streams = df["Streams"]
    streams = streams.str.split("\n")
    streams = [stream[::-1] for stream in streams]
    streams = ["\n".join(stream) for stream in streams]
    streams = [stream.replace("\n - \n", "") for stream in streams]
    df["Streams"] = streams
    df['Streams'] = df['Streams'].apply(lambda x: x.lstrip(" - \n"))
    return df


def remove_duplicates_based_on_song_and_link(df):
    df["Song"] = df["Song"].astype(str)
    df["Link"] = df["Link"].astype(str)

    df = df[~df['Song'].duplicated(keep='first')]
    df = df[~df['Link'].duplicated(keep='first')]

    df.drop_duplicates(subset="Song", inplace=True, keep="first")
    df.drop_duplicates(subset="Link", inplace=True, keep="first")

    return df


def get_extra_song_chart_data(driver, extra_country_list, results_dict):
    ####
    # Extra tasks to get genre specific data from apple music
    # US, UK, Canada, Estonia, Ukraine, Lithuania, Latvia, Austria, Kazakhstan, Bulgaria, Hungary, Czechia
    alternative_chart_dict = {
        "US": "152",
        "GB": "153",
        "CA": "101",
        "EE": "108",
        "UA": "259",
        "LT": "124",
        "LV": "123",
        "AT": "92",
        "KZ": "272",
        "BG": "99",
        "HU": "118",
        "CZ": "105"
    }
    dance_chart_dict = {
        "US": "129",
        "GB": "128",
        "CA": "94",
        "EE": "99",
        "UA": "485",
        "LT": "111",
        "LV": "109",
        "AT": "90",
        "KZ": "517",
        "BG": "93",
        "HU": "104",
        "CZ": "96"
    }

    for country in extra_country_list:
        alternative_link = f"https://app.soundcharts.com/app/market/charts?chart=alternative-{alternative_chart_dict[country]}&chart_type=song&country={country}&platform=apple-music"
        dance_link = f"https://app.soundcharts.com/app/market/charts?chart=dance-{dance_chart_dict[country]}&chart_type=song&country={country}&platform=apple-music"
        try:
            df = parse_webpage(driver, alternative_link)
            # Add the country and platform to the dataframe
            df["Country"] = country
            df["Platform"] = "apple-music"
            df["Genre"] = "Alternative"
            results_dict[f"{country}_{alternative_link}"] = df

            df = parse_webpage(driver, dance_link)
            df["Country"] = country
            df["Platform"] = "apple-music"
            df["Genre"] = "Dance"
            results_dict[f"{country}_{dance_link}"] = df

        except Exception as e:
            print(e)


def print_progress(time_remaining_dict, task_time_list, index, row, thread_number, df):
    # Calculate the time remaining
    task_time_avg = statistics.mean(task_time_list[-10:])
    time_remaining_dict[thread_number] = task_time_avg * (len(df) - int(index))
    time_remaining_string = convert_seconds_to_time_str(statistics.mean(time_remaining_dict.values()))
    print(
        f"Thread {thread_number} getting stats for {row['Song']} | {index}/{len(df)} | {time_remaining_string} remaining")


def collect_data_from_playlist(driver, link, results_dict):
    attempts = 0
    while attempts < 2:
        try:
            df = parse_webpage(driver, link)
            results_dict[f"{link}"] = df
            break
        except Exception as e:
            print(e)
            print(f"Could not get data for {link} retrying...")
            attempts += 1


def run_thread(playlist_list, thread_number):
    global final_df, time_remaining_dict

    # Start the webdriver and login
    driver = login_to_new_driver(detach=False)

    results_dict = {}

    for playlist in playlist_list:
        collect_data_from_playlist(driver, playlist, results_dict)

    # Concatenate all the dataframes in the results dictionary into a single dataframe
    df = pd.concat(results_dict.values(), axis=0)

    # Change the link to spotify
    df['Link'] = df['Link'].apply(change_to_spotify)
    df = remove_duplicates_based_on_song_and_link(df)

    # Randomly shuffle the row order
    df = df.sample(frac=1).reset_index(drop=True)

    task_time_list = [5]

    # Loop through each row in the df and get the streams/total streams/followers/fans
    for index, row in df.iterrows():
        if row["Song"] not in final_df["Song"].values and row["Link"] not in final_df["Link"].values:
            try:
                start_time = time.time()

                # Get the daily streams and total streams
                daily_streams, total_streams, artist_page_link, *_ = get_streams(row["Link"], driver)
                # Add entire row to the dataframe
                row['Streams'] = daily_streams
                row['Total_Streams'] = total_streams
                # Cast the total streams to numeric
                row['Total_Streams'] = pd.to_numeric(row['Total_Streams'], errors='coerce')

                # Get the spotify followers and total fans
                spotify_followers, fans, *_ = get_spotify_followers_and_total_fans(artist_page_link, driver)
                row['Followers'] = spotify_followers
                row['Total_Fans'] = fans

                # Cast the followers and total fans to numeric
                row['Followers'] = pd.to_numeric(row['Followers'], errors='coerce')
                row['Total_Fans'] = pd.to_numeric(row['Total_Fans'], errors='coerce')

                final_df = append_row(final_df, row)

                end_time = time.time()

                task_time_list.append(end_time - start_time)
                print_progress(time_remaining_dict, task_time_list, index, row, thread_number, df)

            except Exception as e:
                print(f"Thread {thread_number} could not get stats for {row['Song']}")

    print(f"Finished getting stats for all songs on thread {thread_number}")


def apply_final_filters_and_formatting(df):
    if df.empty:
        print("No songs that match filters. Cant make csv. Exiting.")
        sys.exit(0)

    # Concat the streams columns with the original dataframe
    df = pd.concat([df, parse_streams_into_columns(df)], axis=1)

    df = df[df['Total_Fans'] < 100_000]
    df = df[df['Total_Streams'] < 5_000_000]
    df = df[df["3_day_avg"] > 2000]

    df = remove_duplicates_based_on_song_and_link(df)
    # Reverse the streams column
    df = reverse_streams_column(df)

    desired_order = ['Link', 'Labels', 'Artists', 'Followers',
                     'Total_Fans', 'Song', 'rank', 'Total_Streams', 'Streams', 'Yesterday',
                     '3_day_avg', '3_day_%_change', '5_day_%_change', '10_day_%_change']

    # Reorder the columns
    return df[desired_order]


def run_with_threading(playlist_list, number_of_threads):
    # List to store the threads
    threads = []

    # If the number of threads is greater than the length of the country list, reduce the number of threads
    number_of_threads = min(number_of_threads, len(playlist_list))

    # Calculate the number of tasks per thread
    tasks_per_thread = len(playlist_list) // number_of_threads
    extra_tasks = len(playlist_list) % number_of_threads

    start = 0

    for i in range(number_of_threads):
        end = start + tasks_per_thread + (1 if i < extra_tasks else 0)

        t = Thread(target=run_thread,
                   args=(playlist_list[start:end], i))
        t.start()
        threads.append(t)

        start = end

    for t in threads:
        t.join()

    global final_df
    final_df = apply_final_filters_and_formatting(final_df)

    completion_time = time.strftime("%Y-%m-%d %H-%M")
    file_path = f'playlist {completion_time}.csv'
    time.sleep(1)
    final_df.to_csv(file_path, index=False)
    print("Saved to csv: " + file_path)

    send_email_notification("jhlevy01@gmail.com", 'Playlist Scraping: SUCCESS',
                            'Your program is complete with no issues. Please check the results.',
                            file_path)

    send_email_notification("aidanalrawi@icloud.com",
                            'Playlist Scraping: SUCCESS',
                            'Your program is complete with no issues. Please check the results.',
                            file_path)


def read_playlist_input_csv():
    playlist_df = pd.read_csv("playlist_input.csv")
    playlist_list = playlist_df['Link'].tolist()
    print("Playlist list read from csv")
    return playlist_list


if __name__ == "__main__":
    global final_df, time_remaining_dict
    time_remaining_dict = {}
    # Make a df with a column for the song
    final_df = pd.DataFrame(columns=["Song", "Link"])
    pd.set_option('display.max_columns', 500)

    playlist_list = read_playlist_input_csv()

    run_with_threading(playlist_list,
                       number_of_threads=4)

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import chromedriver_autoinstaller
import time
import logging
import pendulum
import pandas
from sqlalchemy import create_engine
from airflow.models import Variable


def delayed_send_keys(element, key, occurrence, delay):
    """
    Description: Selenium util method for delayed web browser interactions.
    :param element: Selenium.WebElement
    :param key: Selenium.Keys element
    :param occurrence: Number of times ket is inputted.
    :param delay: Time delay in seconds.
    """
    for i in range(occurrence):
        # isinstance(key, Keys)
        if key != "click":
            element.send_keys(key)
        else:
            element.click()
    time.sleep(delay)


def fetch_credentials():
    """
    Description: Fetches spotify login creds from secrets.yaml file.
    :return: email(str): Email for Spotify login.
             password(str): Password for Spotify login.
    """
    credentials_dict = {"spotify_email": {Variable.get("spotify_email")},
                        "spotify_password": {Variable.get("spotify_password")}}
    email = credentials_dict["spotify_email"]
    password = credentials_dict["spotify_password"]
    return email, password


def get_driver():
    """
    Description: Creates selenium web driver for web scraping.
    :return: driver(Selenium.WebDriver): Driver object used to navigate web pages.
    """
    # Web Driver Configurations
    hub_url = "http://my-selenium-grid-driver:4444"
    options = Options()
    options.add_argument("--disable-dev-shm-usage")
    """
    Disabled additional options while creating scraper.
    options.add_argument("--headless=new")
    options.add_argument("--incognito")
    options.add_argument('--disable-blink-features=AutomationControlled')
    """
    driver = webdriver.Remote(command_executor=hub_url, options=options)
    driver.get('https://spotify.com')
    driver.fullscreen_window()
    time.sleep(5)
    logging.info(driver.title)
    return driver


def is_logged_in(driver):
    """
    Description: Checks if the log-in button is available on screen.
                 Indicates whether the user is logged in already or not.
    :param driver:
    :return:
    """
    # Click on log-in button
    web_buttons = driver.find_elements(By.XPATH, '//button')
    login_button = None
    for button in web_buttons:
        if button.text == "Log in":
            login_button = button
    return login_button


def log_in(driver, login_button):
    """
    Description: Handle logging user in.
    :param driver: Selenium.WebDriver object for navigating web page.
    """
    delayed_send_keys(login_button, "click", 1, 5)
    email, password = fetch_credentials()
    email_field = driver.find_element(By.XPATH, '//input[contains(@id, "login-username")]')
    password_field = driver.find_element(By.XPATH, '//input[contains(@id, "login-password")]')
    delayed_send_keys(email_field, email, 1, 2)
    delayed_send_keys(password_field, password, 1, 2)
    delayed_send_keys(password_field, Keys.ENTER, 1, 7)
    driver.fullscreen_window()


def fetch_playing_song(driver):
    """
    Description: Scrapes spotify footer bar for currently playing song.
    :param driver: Selenium.WebDriver object for navigating web page.
    :return: current_song(str): Name of currently playing song.
             artist(str): Associated artist name.
             current_time(datetime): Time when fetched.
    """
    footer = driver.find_element(By.XPATH, '//footer')
    # Check if a song is being played
    player_controls = footer.find_element(By.CLASS_NAME, 'player-controls__buttons')
    player_control_buttons = player_controls.find_elements(By.XPATH, './/button')
    current_time = pendulum.now()
    is_paused = False
    for buttons in player_control_buttons:
        if buttons.get_attribute("aria-label") == "Play":
            is_paused = True
    # If paused, return no song being played
    if is_paused:
        return None, None, current_time
    # Otherwise, fetch song and artist data
    footer_divs = footer.find_elements(By.XPATH, ".//div")
    current_song = None
    for div_content in footer_divs:
        if div_content.get_attribute("data-testid") == 'now-playing-widget':
            current_song = div_content.get_attribute("aria-label")
    current_song = current_song.split("Now playing: ")[1]
    current_song = current_song.split('by ')
    current_song, artist = current_song[0], current_song[1]
    return current_song, artist, current_time


def upload_df_to_db(conn_string, table_name, df):
    """
    Descripition: Uploads a given df with data to our db.
    :param conn_string: A connection object used to interact with db.
    :param table_name: The table we are uploading to.
    :param df: The df with data we will be uploading.
    :return: The resulting shape of the dataframe after uploading.
    """
    db = create_engine(conn_string)
    conn = db.connect()
    df.to_sql(table_name, con=conn, if_exists='append', method='multi', index=False)
    return df.shape


def save_current_driver_session(driver):
    """
    Description: Testing if we can reuse a driver session to reduce api calls.
    :param driver:
    :return:
    """
    url = driver.command_executor._url
    session_id = driver.session_id
    print(url, session_id)
    return url, session_id


def scrape_song():
    conn_string = (f'postgresql://{Variable.get("user")}:'
                   f'{Variable.get("password")}'
                   f'@host.docker.internal:{Variable.get("port")}/'
                   f'{Variable.get("database")}')
    print("Get Driver")
    driver = get_driver()

    print("Testing if I can save and reuse a driver")
    save_current_driver_session(driver)

    print("Log In")
    login_button = is_logged_in(driver)
    print(login_button)
    if login_button:
        log_in(driver, login_button)
    else:
        driver.refresh()

    print("Get Current Song")
    current_song, artist, current_time = fetch_playing_song(driver)
    print(f"Song: {current_song}")
    print(f"Artist: {artist}")
    print(f"Time: {current_time}")
    print(current_time.to_datetime_string())

    spotify_df = pd.DataFrame.from_dict({'time_played': [str(current_time.to_datetime_string())],
                                         'song': [current_song],
                                         'artist': [artist]})
    df_shape = upload_df_to_db(conn_string, 'played_songs', spotify_df)
    print(f"Uploaded data: {df_shape}")
    print("Quitting Driver")
    driver.quit()

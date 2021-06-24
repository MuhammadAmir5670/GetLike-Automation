# importing the required libraries
import os
import sys
import re
from loguru import logger
from contextlib import contextmanager
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, \
    ElementClickInterceptedException, NoSuchWindowException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidArgumentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys


chrome_profile_path = {"--user-data-dir": "/home/amir/.config/google-chrome", "--profile-directory": "Default"}
BASE_DIR = os.path.abspath("./")
CHROME_DRIVER = os.path.join(BASE_DIR, 'chromedriver')


class BrowserBot:
    def __init__(self, url):
        self.preference = {}
        self.url = url
        self.__options = webdriver.ChromeOptions()
        self.driver = self.show()
        self.base_window = self.driver.current_window_handle

    @property
    def options(self):
        return self.__options

    @options.setter
    def options(self, value):
        pattern = r"^(?P<key>--[\w\-]+)=?(?P<value>.*)"
        regex = re.compile(pattern)
        if regex.match(value):
            self.__options.add_argument(value)

    def show(self):
        self.set_preferences()
        self.use_default_user()
        try:
            driver = webdriver.Chrome(CHROME_DRIVER, chrome_options=self.options)
        except InvalidArgumentException:
            sys.exit("the specified chrome user instance is already in use")
        driver.get(self.url)
        return driver

    def use_default_user(self):
        self.options = "--user-data-dir={}".format(chrome_profile_path['--user-data-dir'])
        self.options = '--profile-directory={}'.format(chrome_profile_path['--profile-directory'])

    def headless_option(self):
        self.options = "--headless"

    def set_preferences(self):
        """
        Method for setting the chrome options
        """
        self.pref_translate_to()
        self.options.add_experimental_option("prefs", self.preference)

    def pref_translate_to(self):
        """
        Method for translating the response web page's language to english
        """
        self.preference["translate_whitelists"] = {"ru": "en"}
        self.preference["translate"] = {"enabled": "True"}

    def async_wait_until(self, condition, condition_params=tuple(), wait=60):
        try:
            return WebDriverWait(self.driver, wait).until(
                condition(*condition_params)
            )
        except TimeoutException as exc:
            logger.error(exc)
            return None

    def async_get_element(self, locator, wait=60, exceptions=None):
        exceptions = exceptions if exceptions else []
        exceptions.append(StaleElementReferenceException)

        try:
            return self.async_wait_until(EC.presence_of_element_located, (locator,), wait)
        except tuple(exceptions) as exc:
            logger.error(exc)
            return None

    def element_exist(self, find_by, value):
        try:
            return self.driver.find_element(find_by, value)
        except NoSuchElementException:
            return False

    @contextmanager
    def wait_for_new_window(self, handles_before):
        new_window = self.async_wait_until(new_window_is_opened, (handles_before,), wait=10)
        try:
            yield new_window
        except NoSuchWindowException:
            logger.warning("No new Window exist id :{}".format(new_window))
        else:
            if self.driver.current_window_handle == new_window:
                self.driver.close()
        finally:
            self.driver.switch_to.window(self.base_window)

    def scroll_to_load_content(self):
        body = self.driver.find_element_by_tag_name("body")
        body.send_keys(Keys.END)
        sleep(1)
        body.send_keys(Keys.HOME)


# CUSTOM EXPECTED CONDITIONS
class find_elements_in_sequence(object):
    def __init__(self, locator, sequence):
        self.locator = locator
        self.elements = sequence

    def __call__(self, driver):
        for element in self.elements:
            try:
                return driver.find_element(self.locator, element)
            except NoSuchElementException:
                continue
        else:
            return False


class element_is_clicked(object):
    def __init__(self, element):
        self.element = element

    def __call__(self, driver):
        try:
            self.element.click()
            return True
        except (ElementClickInterceptedException, StaleElementReferenceException):
            return False


class url_changes(object):
    def __init__(self, to):
        self.url = to

    def __call__(self, driver):
        if driver.current_url == self.url:
            return True
        else:
            driver.get(self.url)
            return False


class new_window_is_opened:
    def __init__(self, handles_before):
        self.handles_before = handles_before

    def __call__(self, driver):
        new_handles = driver.window_handles
        if len(new_handles) > len(self.handles_before):
            new_windows = list(set(driver.window_handles) - set(self.handles_before))
            assert len(new_windows) == 1, "more then one new windows are opened."
            return new_windows[0]
        else:
            return False


class language_is_english:
    def __init__(self, element):
        self.element = element
        self.prev_text = ""

    def __call__(self, driver):
        text = self.element.text
        if self.prev_text != text:
            self.prev_text = text
            for char in text:
                if ord(char) > 122:
                    break
            else:
                return text
            return False

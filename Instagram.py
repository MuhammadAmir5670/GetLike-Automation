from selenium.webdriver.common.by import By
from Browser import BrowserBot, url_changes, find_elements_in_sequence, element_is_clicked
from loguru import logger
import sys


# DECORATORS
def login_required(inner_func):
    def wrapper(self):
        if not self.logged_in:
            self.login()
        inner_func(self)

    return wrapper


def preserve_current_url(inner_func):
    def wrapper(self):
        base_url = self.driver.current_url
        return_value = inner_func(self)
        if self.driver.current_url != base_url:
            self.driver.get(base_url)
        return return_value

    return wrapper


class InstaBot(BrowserBot):
    # ***************** Instagram Page Elements **********************
    FOLLOW_BUTTON_01 = '//*[@id="react-root"]/section/main/div/header/section/div[1]/div[1]/div/div/div/span/span[1]/button'
    FOLLOW_BUTTON_02 = '//*[@id="react-root"]/section/main/div/header/section/div[1]/div[2]/div/div/div/span/span[1]/button'
    MESSAGE_BUTTON_01 = '//*[@id="react-root"]/section/main/div/header/section/div[1]/div[1]/div/div[1]/button'
    MESSAGE_BUTTON_02 = '//*[@id="react-root"]/section/main/div/header/section/div[1]/div[2]/div/div[1]/button'
    LikeButton = '//*[@id="react-root"]/section/main/div/div[1]/article/div[3]/section[1]/span[1]/button'
    ACCOUNT_RESTRICTED = './/body/div[contains(concat(" ",normalize-space(@class)," ")," RnEpo ")][contains(concat(" ",normalize-space(@class)," ")," Yx5HN ")]/div/div/div/div[contains(concat(" ",normalize-space(@class)," ")," mt3GC ")]/button[contains(concat(" ",normalize-space(@class)," ")," aOOlW ")][contains(concat(" ",normalize-space(@class)," ")," bIiDR ")]'
    PAGE_NOT_AVAILABLE = '//*[@id="react-root"]/section/main/div/div/h2'

    def __init__(self, data, driver=None, url=None):
        if isinstance(driver, BrowserBot):
            self.__dict__ = driver.__dict__.copy()
        else:
            super(InstaBot, self).__init__(url=url)

        self.username, self.password = data.get("Instagram").values()
        self.logged_in = self.is_logged_in()

    @preserve_current_url
    def is_logged_in(self):
        user_url = "https://www.instagram.com/{}/".format(self.username)
        is_changed = self.async_wait_until(url_changes, condition_params=(user_url,))
        sequence = ['//*[@id="react-root"]/section/nav/div[2]/div/div/div[3]/div/span/a[1]/button',
                    '//*[@id="react-root"]/section/main/div/header/section/div[1]/div[1]/a']

        if is_changed:
            element = self.async_wait_until(find_elements_in_sequence, condition_params=(By.XPATH, sequence))
            state = element.text.lower() if element else None
            if state == "log in":
                return False
            elif state == "edit profile":
                return True
            return False

    @preserve_current_url
    def login(self):
        logger.info("logging in to user account: {}".format(self.username))
        if not self.logged_in:
            # selecting form elements
            self.driver.get("https://www.instagram.com/accounts/login/")
            username = self.async_get_element((By.XPATH, '//*[@id="loginForm"]/div/div[1]/div/label/input'))
            password = self.async_get_element((By.XPATH, '//*[@id="loginForm"]/div/div[2]/div/label/input'))

            # clearing the input fields
            username.clear()
            password.clear()

            # filling in the username and password details
            username.send_keys(self.username)
            password.send_keys(self.password)

            self.driver.find_element_by_xpath('//*[@id="loginForm"]/div/div[3]/button').click()
            sequence = ['//*[@id="react-root"]/section/main/div/div/div/section/div/button',
                        '//*[@id="react-root"]/section/main/section/div[3]/div[1]/div/div/div[3]/button/div',
                        '//*[@id="slfErrorAlert"]'
                        ]

            element = self.async_wait_until(find_elements_in_sequence, condition_params=(By.XPATH, sequence))
            if element and element.text.lower() == "save info":
                self.logged_in = True
                element.click()
                return

            if element and element.text.lower() == "switch":
                self.logged_in = True
                return

            logger.warning(element.text.lower())
            sys.exit()

    @login_required
    def follow(self):
        sequence = [self.FOLLOW_BUTTON_01, self.FOLLOW_BUTTON_02, self.MESSAGE_BUTTON_01, self.MESSAGE_BUTTON_02, self.PAGE_NOT_AVAILABLE, self.ACCOUNT_RESTRICTED]
        while True:
            element = self.async_wait_until(find_elements_in_sequence, condition_params=(By.XPATH, sequence))

            if element is None:
                element = self.driver.find_element_by_tag_name("body")
                state = element.text.lower()
                if state == "oops, an error occurred.":
                    self.driver.refresh()
                return False

            state = element.text.lower()

            if state == "follow":
                clicked = self.async_wait_until(element_is_clicked, condition_params=(element,), wait=1)
                if clicked:
                    sequence.remove(self.FOLLOW_BUTTON_01)
                    sequence.remove(self.FOLLOW_BUTTON_02)
            elif state == "message":
                return True
            elif state == "report a problem":
                raise AccountRestricted("Operation Unsuccessful: accounts activity restricted.")
            elif state == "sorry, this page isn't available.":
                raise PageNotAvailable("Invalid URL: the user account you are trying to access does not exits.")
            else:
                break

    @login_required
    def like(self):
        element = self.async_get_element(locator=(By.XPATH, self.LikeButton), wait=10)
        clicked = self.async_wait_until(element_is_clicked, condition_params=(element,), wait=1)
        if clicked:
            return True
        return False


class AccountRestricted(Exception):
    pass


class PageNotAvailable(Exception):
    pass

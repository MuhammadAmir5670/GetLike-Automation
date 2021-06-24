# importing the required libraries
import re
from loguru import logger
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from Browser import BrowserBot, element_is_clicked, language_is_english
from Instagram import InstaBot, PageNotAvailable, AccountRestricted


class GetLikeBot(BrowserBot):
    URL = "https://getlike.io/"

    def __init__(self, data):
        super(GetLikeBot, self).__init__(url=self.URL)
        self.username, self.password = data.get("GetLike").values()
        self.__tasks = []
        self.handlers = {"instagram": InstaBot(data, driver=self)}

    def __call__(self):
        self.login()
        self.start_instagram_tasks()

    @property
    def tasks(self):
        return self.__tasks

    @tasks.setter
    def tasks(self, task):
        if isinstance(task, InstaTask):
            self.__tasks.append(task.info())

    def fetch_tasks(self, task_handler):
        """
        Method for fetching the -- IDs of all available tasks
        """
        self.scroll_to_load_content()
        logger.info('Fetching task...........')
        tasks = []
        elements = self.driver.find_elements_by_css_selector('div.js-tpl-tasks-list > article.task_item')
        for element in elements:
            tasks.append(task_handler(element=element, controller=self))
        return tasks

    def login(self):
        """
        Method for Logging in the get like account
        """
        self.async_get_element(locator=(By.LINK_TEXT, "To come in")).click()

        if not self.is_login():
            # selecting form elements
            name = self.driver.find_element_by_id("User_loginLogin")
            password = self.driver.find_element_by_id("User_passwordLogin")

            # clearing the input fields
            name.clear()
            password.clear()

            # filling in the username and password details
            name.send_keys(self.username)
            password.send_keys(self.password)

            if self.element_exist(find_by=By.XPATH, value='//*[@id="RecaptchaField1"]'):
                logger.warning(
                    "recaptcha is given please solve it by yourself and and hit login you have 5 minutes to do so.")
                logger.warning("after successful login Bot will again take the control.")
                self.async_wait_until(EC.url_to_be, (f"{self.URL}tasks/my/",), 5 * 60)
            else:
                self.driver.find_element_by_name("submitLogin").click()

            return self.is_login()

        return True

    def is_login(self):
        """Method for checking the current page is dashboard page or not"""
        return self.driver.current_url == f"{self.URL}tasks/my/"

    def start_instagram_tasks(self):
        self.async_get_element((By.XPATH, '//*[@id="tasks-page"]/div[6]/nav/div/div[2]/ul[1]/li[2]/a')).click()
        while True:
            tasks = self.fetch_tasks(task_handler=InstaTask)
            for task in tasks:
                try:
                    task.start()
                    logger.info(task)
                    self.tasks = task
                except AccountRestricted:
                    logger.error("AccountRestricted: Instagram has restricted certain activities on your account.")
                    break

            self.load_more()

    def load_more(self):
        logger.info('Loading New Tasks')
        self.driver.find_element_by_xpath('//*[@id="task_more"]/button').click()


class InstaTask(GetLikeBot):
    regex = re.compile(r"(?P<prefix>task-item-)(?P<id>\d+)")
    # ***************** GetLike Page Elements **********************
    TASK_BUTTON_SELECTOR = '#task-item-{} > div > div > div > div.media-right.media-middle.task-btn > {}'
    TASK_TYPE_SELECTOR = '#task-item-{} > div > div > div > div.media-body.media-middle.full-width > div > div > h3'
    LOAD_MORE_SELECTOR = '#task_more > button'
    NOTIFY_POPUP_SELECTOR = '#tasks-page > div.notify.notify-top-right > div'

    def __init__(self, element, controller):
        if not isinstance(controller, GetLikeBot):
            super(InstaTask, self).__init__(data={})
            raise ValueError("bot should be an instance of GetLikeBot class")

        self.__dict__ = controller.__dict__.copy()
        self.element = element
        self.id = int(self.regex.search(self.element.get_attribute("id")).group("id"))
        self.status = self.button.text
        self.completed = False
        self.type = self.driver.find_element_by_css_selector(self.TASK_TYPE_SELECTOR.format(self.id)).text.lower()
        self.message = ""

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, value):
        value = value.lower()
        regex = re.compile(r"\d\.\d+")
        if regex.match(value):
            self.__status = "pending"
        elif value.lower() == "check":
            self.__status = "started"
        else:
            self.completed = True
            self.__status = value

    @property
    def button(self):
        try:
            return self.element.find_element_by_css_selector(self.TASK_BUTTON_SELECTOR.format(self.id, "a"))
        except NoSuchElementException:
            return self.element.find_element_by_css_selector(self.TASK_BUTTON_SELECTOR.format(self.id, "span"))

    def start(self):
        while not self.completed:
            handles_before = self.driver.window_handles
            if self.async_wait_until(element_is_clicked, condition_params=(self.button,)):
                task = self.get_task_executor()

                # task will be None for unknown tasks
                if task is None:
                    self.message = "unknown Task is identified"
                    break

                with self.wait_for_new_window(handles_before) as new_window:
                    if new_window is not None:
                        self.driver.switch_to.window(new_window)
                        try:
                            task()
                        except PageNotAvailable:
                            self.message = "PageNotAvailable: the Page you are accessing does not exist."
                            break

                self.message = self.verify_task_state()
                self.status = self.async_wait_until(language_is_english, (self.button, ))

    def get_task_executor(self):
        logger.info('determining task type.........')
        if 'follow' in self.type or 'subscribe' in self.type:
            return getattr(self.handlers.get("instagram"), "follow")
        elif 'like' in self.type:
            return getattr(self.handlers.get("instagram"), "like")
        else:
            return None

    def verify_task_state(self):
        logger.info('determining task state.......')
        if self.async_wait_until(element_is_clicked, condition_params=(self.button,)):
            element = self.async_get_element(locator=(By.CSS_SELECTOR, self.NOTIFY_POPUP_SELECTOR), wait=10)
            if element:
                text = self.async_wait_until(language_is_english, (element, ))
                if not re.search(r'execution not confirmed', text):
                    return text
                else:
                    return self.verify_task_state()

    def info(self):
        return [self.id, self.type, self.status, self.completed, self.message]

    def __str__(self):
        return "Task: {} - {} | {} - {}".format(self.id, self.completed, self.status, self.message)

    def __repr__(self):
        return "<Insta Task: {} | status - {}>".format(self.id, self.status)

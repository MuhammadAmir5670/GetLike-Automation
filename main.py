import os
import json

from collections import defaultdict
from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException, WebDriverException
from loguru import logger
from tabulate import tabulate

from GetLike import GetLikeBot


# creating the title bar function
def title_bar():
    os.system('clear')  # for windows

    # title of the program
    print()
    print("\t**********************************************")
    print("\t*****           GetLike Bot              *****")
    print("\t**********************************************")


# creating the user main menu function
def mainMenu():
    while True:
        title_bar()
        print()
        print("\t**************  Welcome Menu  ****************")
        print()
        print("\t[1] Add GetLike account")
        print("\t[2] Start Instagram Task")
        print("\t[3] Start Twitter Task")
        print("\t[4] Quit")

        try:
            choice = int(input("\tEnter Choice: "))

            if choice == 1:
                add_account()
            elif choice == 2:
                start_instagram_task()
            elif choice == 3:
                start_twitter_task()
            elif choice == 4:
                print("\n\t", " Thank You ".center(47, "*"), sep="")
                break
            else:
                print("Invalid Choice. Enter 1-4")
        except ValueError:
            print("Invalid Choice. Enter 1-4\n Try Again")
    exit()


def add_account():
    os.system("clear")
    accounts = ["GetLike", "Instagram", "Twitter"]
    data = defaultdict(dict)
    with open("accounts.json", "r+") as file:
        file = json.load(file)
        for account in accounts:
            print()
            print(f"{account}'s Account")
            username = input("Enter User Name:...")
            password = input("Enter Password:....")

            data[account] = {"username": username, "password": password}

        file.append(data)

        with open("accounts.json", "w") as output:
            json.dump(file, output, indent=4)


def start_instagram_task():
    os.system("clear")
    with open("accounts.json") as file:
        file = json.load(file)
        for data in file:
            try:
                browser = GetLikeBot(data)
                browser.login()
                browser.start_instagram_tasks()
            except (InvalidSessionIdException, NoSuchWindowException, WebDriverException):
                logger.error("Browser has been closed by some external process.")
                print("\n", tabulate(browser.tasks, headers=["Id", "Task", "Status", "Completed", "Message"]))
                break
        input("Press Enter to Continue:...")


def start_twitter_task():
    logger.info("twitter handler is not available yet")


def main():
    mainMenu()


if __name__ == "__main__":
    main()

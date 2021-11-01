import datetime
import os
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import asyncio


class TwitchError(Exception):
    pass


class TwitchSearchError(Exception):
    pass


def get_chrome_options():
    if os.name == 'nt':
        user_data = 'G:\\Twitch\\gits\\kryabot-core\\twitch-chrome-data'
    else:
        user_data = os.getenv('SECRET_DIR', '')
        user_data += 'twitch-chrome-data'

    options = webdriver.ChromeOptions()
    options.headless = True
    options.add_argument('--user-data-dir={}'.format(user_data))
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    return options


def get_driver():
    # TODO: Lock mechanism
    if os.name == 'nt':
        driver = webdriver.Chrome(executable_path=r'C:\Users\Oskar\Downloads\chromedriver_win32\chromedriver.exe', options=get_chrome_options())
    else:
        driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options=get_chrome_options())

    return driver


async def twitch_gift_to_user(target_channel: str, target_nickname: str):
    return await asyncio.to_thread(gift_to_user, target_channel, target_nickname)


def interactive_login():
    username = input('Enter username:')
    password = input('Enter password:')

    driver = get_driver()
    driver.get('https://www.twitch.tv/subs/{}'.format(username))
    sleep(2)

    try:
        tries = 0
        while True:
            if tries > 20:
                raise TwitchSearchError('Failed to find login button')

            tries += 1
            sleep(1)
            try:
                buttons = driver.find_elements_by_xpath("//*[contains(text(), 'Log in')]")
                if buttons:
                    buttons[0].click()
                    break
            except Exception as ex:
                pass

        tries = 0
        while True:
            if tries > 20:
                raise TwitchSearchError('Input for nickname not found')

            tries += 1
            sleep(1)
            try:
                nickname_input = driver.find_element_by_id('login-username')
                if nickname_input:
                    nickname_input.send_keys(username)
                    break
            except Exception as ex:
                pass

        tries = 0
        while True:
            if tries > 20:
                raise TwitchSearchError('Input for password not found')

            tries += 1
            sleep(1)
            try:
                password_input = driver.find_element_by_id('password-input')
                if password_input:
                    password_input.send_keys(password)
                    break
            except Exception as ex:
                pass

        tries = 0
        while True:
            if tries > 20:
                raise TwitchSearchError('Login button not found')

            tries += 1
            sleep(1)
            try:
                login_button = driver.find_element_by_css_selector('button[data-a-target=passport-login-button]')
                if login_button:
                    login_button.click()
                    break
            except Exception as ex:
                pass

        sleep(3)
        oauth_code = input('Enter oauth token:')
        actions = ActionChains(driver)
        actions.send_keys(oauth_code)
        actions.perform()

        # tries = 0
        # while True:
        #     if tries > 20:
        #         raise TwitchSearchError('Oauth token input field not found')
        #
        #     tries += 1
        #     sleep(1)
        #     try:
        #         oauth_token = driver.find_element_by_css_selector('button[data-a-target=tw-input][autocomplete=one-time-code][inputmode=numeric]')
        #         if oauth_token:
        #
        #             break
        #     except Exception as ex:
        #         pass

        tries = 0
        while True:
            if tries > 20:
                raise TwitchSearchError('Oauth submit button not found')

            tries += 1
            sleep(1)
            try:
                login_button = driver.find_element_by_css_selector('button[screen=two_factor][target=submit_button]')
                if login_button:
                    login_button.click()
                    break
            except Exception as ex:
                pass
    except TwitchSearchError as search_error:
        driver.save_screenshot("{}_interactive_login_error.png".format(datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")))
        raise TwitchSearchError


def gift_to_user(target_channel: str, target_nickname: str):
    driver = get_driver()
    driver.get('https://www.twitch.tv/subs/{}'.format(target_channel))
    try:
        click_web_buttons(driver, target_nickname)
        return True, None
    except TwitchSearchError as search_error:
        # Save screenshot for debug reasons
        driver.save_screenshot("{}_gift_search_error_{}_{}.png".format(datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S"), target_channel, target_nickname))
        return False, 'SEARCH_ERROR'
    except TwitchError as twitch_error:
        return False, str(twitch_error)
    finally:
        driver.quit()

    return False, None


def click_web_buttons(driver, target_nickname):
    tries = 0
    print('searching for gifting option for specific user')
    while True:
        if tries > 20:
            raise TwitchSearchError('Gift to specific viewer option not found')

        tries += 1
        sleep(1)
        try:
            buttons = driver.find_elements_by_xpath("//*[contains(text(), 'Gift a specific viewer')]")
            if buttons:
                buttons[0].click()
                break
        except Exception as ex:
            pass

    print('searching for user input')
    tries = 0
    while True:
        if tries > 20:
            raise TwitchSearchError('Input for nickname not found')

        tries += 1
        sleep(1)
        try:
            nickname_input = driver.find_element_by_id('dropdown-search-input')
            if nickname_input:
                nickname_input.send_keys(target_nickname)
                sleep(3)

                break
        except Exception as ex:
            pass

    print('Searching for proposed options')
    tries = 0
    while True:
        if tries > 20:
            raise TwitchError('User {} not found!'.format(target_nickname))

        tries += 1
        sleep(1)
        try:
            list_box = driver.find_element_by_class_name('simplebar-scroll-content')
            if not list_box:
                print('list box is none')
                continue

            options = list_box.find_elements_by_tag_name('button')
            if not options:
                continue

            found_user = False
            for option in options:
                if str(option.get_attribute('data-user_name')).lower() == target_nickname.lower():
                    option.click()
                    found_user = True
                    break

            if found_user:
                break
            else:
                print('User {} not found yet'.format(target_nickname))
        except Exception as ex:
            print(ex)
            pass

    # try:
    #     checkbox = driver.find_elements_by_xpath("//*[contains(text(), 'Gift Anonymously')]")
    #         # driver.find_element_by_css_selector("div[innerText='Gift Anonymously']")
    #     if checkbox:
    #         checkbox[0].click()
    # except Exception as checkbot_exception:
    #     print(checkbot_exception)
    #     pass

    tries = 0
    while True:
        if tries > 20:
            raise TwitchSearchError('Gift button not found after user selection')

        tries += 1
        sleep(1)
        try:
            gift_button = driver.find_element_by_css_selector(
                'button[data-test-selector=checkout-gift-subscribe-button]')
            if gift_button:
                print('found gift button')
                if not gift_button.is_enabled():
                    print('button is disabled, searching for reason')
                    # Disabled button
                    disabled_reason = driver.find_element_by_css_selector(
                        'p[data-test-selector=gift-eligibility-message-selector]')
                    if disabled_reason and disabled_reason.text:
                        raise TwitchError(disabled_reason.text)
                else:
                    gift_button.click()
                    break
        except TwitchError as twitch_error:
            raise twitch_error
        except Exception as ex:
            pass

    tries = 0
    while True:
        if tries > 20:
            raise TwitchSearchError('Failed to find purchase button')

        tries += 1
        sleep(1)
        try:
            purchase_button = driver.find_element_by_css_selector('button[data-a-target=spm-complete-purchase-button]')
            if purchase_button and purchase_button.is_enabled():
                purchase_button.click()
                break
        except Exception as ex:
            pass

    tries = 0
    while True:
        if tries > 30:
            raise TwitchSearchError('Purchase was not successful!')

        tries += 1
        sleep(1)
        try:
            success = driver.find_elements_by_xpath("//*[contains(text(), 'Purchase Successful')]")
            if success:
                break
        except Exception as ex:
            pass
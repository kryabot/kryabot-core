import os
from time import sleep

from selenium import webdriver
import asyncio
import base64


def get_chrome_options():
    options = webdriver.ChromeOptions()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    return options


def scrape_screenshot_word_cloud(data) -> bytes:
    if os.name == 'nt':
        driver = webdriver.Chrome(executable_path=r'C:\Users\Oskar\Downloads\chromedriver_win32\chromedriver.exe', options=get_chrome_options())
    else:
        driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options=get_chrome_options())

    driver.get('https://wordcloud.timdream.org/#base64-list:{}'.format(base64.b64encode(data.encode('utf-8')).decode('utf-8')))

    # Wait for generation of result
    sleep(5)

    # hide not needed elements
    driver.execute_script("document.getElementsByClassName('navbar')[0].setAttribute('hidden','');")
    driver.execute_script("document.getElementById('wc-sns-push').setAttribute('hidden','');")

    result = driver.get_screenshot_as_png()
    driver.quit()
    return result


async def get_word_cloud_screenshot(data) -> bytes:
    # Run blocking method in thread to avoid blocking main asyncio thread
    return await asyncio.to_thread(scrape_screenshot_word_cloud, data)


async def test_twitch(db, channel_id: int):
    rows = await db.searchTwitchMessages(channel_id, '%')
    words = {}
    request_data = ""
    for record in rows:
        line = record['message']
        word_list = line.split(' ')
        for word in word_list:
            if word in words.keys():
                words[word] += 1
            else:
                words[word] = 1

    sorted_words = dict(sorted(words.items(), key=lambda item: item[1], reverse=True))

    i = 0
    for word in sorted_words.keys():
        if i > 200:
            break
        i += 1
        request_data += '{}\t{}\n'.format(sorted_words[word], word)

    return await get_word_cloud_screenshot(request_data)
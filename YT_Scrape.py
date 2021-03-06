from __future__ import print_function, unicode_literals
import re
import six
import os

from pyfiglet import Figlet, figlet_format
from pprint import pprint
from PyInquirer import style_from_dict, Token, prompt, Validator, ValidationError
from termcolor import colored
import argparse

from src_code import (entire_channel, get_channel_details, get_api_key, create_new, load_history,
                      get_playlist_videos, most_watched, early_views, generate_download,
                      sync_generate_download)


def log1(string, color, figlet=False):
    if colored:
        if not figlet:
            six.print_(colored(string, color))
        else:
            six.print_(colored(figlet_format(
                string, font='doom'), color))
    else:
        six.print_(string)


style = style_from_dict({
    Token.QuestionMark: '#E91E63 bold',
    Token.Selected: '#673AB7 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#2196f3 bold',
    Token.Question: '',
})


class NumberValidator(Validator):
    def validate(self, document):
        try:
            int(document.text)
        except ValueError:
            raise ValidationError(
                message='Please enter a number',
                cursor_position=len(document.text))  # Move cursor to end


questions = [
    {
        'type': 'confirm',
        'name': 'database',
        'message': 'Do you want to create a new database (default=No, if you already have one)',
        'default': False
    },
    {
        'type': 'input',
        'name': 'key',
        'message': 'Please enter your Youtube API key',
    },
    {
        'type': 'list',
        'name': 'operation',
        'message': 'What do you want to do?',
        'choices': ['Sync and generate download', 'Scrape a Channel', 'Scrape a Single Playlist',
                    'Load Your History', 'Most Watched Video', 'Early Viewed Video',
                    'Generate Download List', 'Find oldest videos on a topic', ],
        'filter': lambda val: val.lower()
    },
    {
        'type': 'list',
        'name': 'channel',
        'message': 'Select Further \n Scraping all videos for a big channel will surpass your free API Limit',
        'choices': ['Scrape Everything for a channel', 'Just Channel Stats (Individual video stats are not scraped)'],
        'when': lambda answers: answers['operation'] == 'scrape a channel'
    },
    {
        'type': 'input',
        'name': 'channelID',
        'message': 'Enter the Channel ID',
        'when': lambda answers: answers['operation'] == 'scrape a channel' and answers['Channel'] != ''
    },
    {
        'type': 'input',
        'name': 'playlistID',
        'message': 'Enter the Playlist ID',
        'when': lambda answers: answers['operation'] == 'scrape a single playlist'
    },
    {
        'type': 'list',
        'name': 'download',
        'message': 'What should the list contain?',
        'choices': ['Videos from a single Channel', 'Videos from entire database'],
        'when': lambda answers: answers['operation'] == 'generate download list in reverse order'
    },
    {
        'type': 'confirm',
        'name': 'import',
        'message': 'Do you want to import your video_history into main table(tb_videos) too? ',
        'default': False,
        'when': lambda answers: answers['operation'] == 'load your history'
    },
]


def main():
    log1("Youtube_Scraper", color="blue", figlet=True)
    print('Please Choose the desired Options, option can be stored in property file')
    print('Press "ctrl+C" to escape at any point\n')

    answers = prompt(questions, style=style)

    if answers['database'] == True:
        create_new()

    get_api_key(answers['key'])

    if answers['operation'] == 'Sync and generate download':
        sync_generate_download()

    elif answers['operation'] == 'Find oldest videos on a topic':
        os.system("python oldest_videos.py -h")

    elif answers['operation'] == 'scrape a channel':
        if answers['channel'] == 'Just Channel Stats (Individual video stats are not scraped)':
            get_channel_details(answers['channelID'])
        elif answers['channel'] == 'Scrape Everything for a channel':
            entire_channel(answers['channelID'])

    elif answers['operation'] == 'scrape a single playlist':
        get_playlist_videos(answers['playlistID'])

    elif answers['operation'] == 'load your history':
        if answers['import'] == True:
            res = 'y'
        elif answers['import'] == False:
            res = 'n'
        print("Please Wait ...")
        load_history(res)

    elif answers['operation'] == 'most watched video':
        print("If your watch history is not loaded in database, it will give empty result")
        print("Please enter, How many items to retrieve e.g. 10 for Top 10 \n")
        n = int(input())
        most_watched(n)

    elif answers['operation'] == 'early viewed video':
        print("If your watch history is not loaded in database, it will give empty result")
        print("Please enter, How many items to retrieve e.g. 10 for Top 10 \n")
        n = int(input())
        early_views(n)

    elif answers['download'] == 'Videos from a single Channel':
        print("It will list videos that are marked 'Is-Good' and is present in your database")
        chc = input("Please enter the channel ID \t")
        print("Please enter, How many items the list will contain (default=50) \n")
        n = int(input())
        generate_download([chc], n)
    elif answers['download'] == 'Videos from entire database':
        print("It will list videos that are marked 'Is-Good' and is present in your database")
        chc = ''
        print("Please enter, How many items the list will contain (default=50)\n")
        n = int(input())
        generate_download([chc], n)

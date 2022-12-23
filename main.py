import sys
import json
from datetime import datetime, timedelta
from tqdm import tqdm
from colorama import Fore, Back, Style
import streamlit as st
import pandas as pd


def parse(data):
    RESOLUTION = timedelta(hours=2)
    MIN_DELTA = timedelta(weeks=36)

    initiated = {}
    infractions = 0
    parties = set(list(data).map(lambda x: x['from']))

    for i, message in enumerate(tqdm(data)):
        date = datetime.fromisoformat(data['date'])
        text = message['text']
        sender = message['from']

        if i != 0:
            # This is not the first message, so we can check if this is the first message in a new conversation
            if date - datetime.fromisoformat(data[i - 1]['date']) >= RESOLUTION:
                if 'happy birthday' not in text.tolower():
                    # `sender` initiated a new conversation
                    initiated[sender].append(1)
                    initiated[not_sender].append(0)

            if date - datetime.fromisoformat(data[i - 1]['date']) >= MIN_DELTA:
                infractions += 1
        else:
            not_sender = parties - {sender}
            initiated[sender] = [1]
            initiated[not_sender] = [0]
    
    # Get cumulative scores for each party in infractions
    for party in parties:
        initiated[party] = [sum(initiated[party][:i]) for i in range(len(initiated[party]))]
    
    initiated = pd.DataFrame(initiated)
        
    return initiated, infractions


def info(message):
    print(Fore.GREEN + '[INFO] ' + message + Style.RESET_ALL)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 {} <filename>'.format(sys.argv[0]))
        sys.exit(1)
    
    filename = sys.argv[1]
    with open(filename, 'r') as f:
        data = json.load(f)
    
    data = data['messages']
    info(f'Parsing {len(data)} messages.')

    initiated, infractions = parse(data)

    # Write our dashboard
    st.write('# Telegram Chat Analyzer')
    st.write(f'Infractions: {infractions}')

    st.line_chart(initiated)
import sys
import json
from datetime import datetime, timedelta
from tqdm import tqdm
from colorama import Fore, Back, Style
import streamlit as st
import pandas as pd


def parse_complex_message(message):
    total = ''

    for part in message:
        if isinstance(part, str):
            total += f'{part} '
        elif isinstance(part, dict):
            total += f'{part["text"]} '

    return total


def parse(data):
    RESOLUTION = timedelta(hours=2)
    MIN_DELTA = timedelta(weeks=36)

    initiated = {}
    infractions = 0

    data = [message for message in data if 'from' in message]
    parties = set(list(map(lambda x: x['from'], data)))

    for i, message in enumerate(tqdm(data)):
        date = datetime.fromisoformat(message['date'])
        text = message['text']
        sender = message['from']
        not_sender = list(parties - {sender})[0]

        if i != 0:
            # This is not the first message, so we can check if this is the first message in a new conversation
            if date - datetime.fromisoformat(data[i - 1]['date']) >= RESOLUTION:
                try:
                    if isinstance(text, list):
                        text = parse_complex_message(text)

                    if 'happy birthday' not in text.lower():
                        # `sender` initiated a new conversation
                        initiated[sender].append(1)
                        initiated[not_sender].append(0)
                except:
                    print('Message is', message)

            if date - datetime.fromisoformat(data[i - 1]['date']) >= MIN_DELTA:
                infractions += 1
        else:
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

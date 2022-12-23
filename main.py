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


def parse(data, resolution=2):
    RESOLUTION = timedelta(hours=resolution)
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
    initiated_forward = {}
    initiated_backward = {}
    for party in parties:
        initiated_forward[party] = [sum(initiated[party][:i]) / (i if i != 0 else i + 1) * 100 for i in range(1, len(initiated[party]))]
        initiated_backward[party] = [sum(initiated[party][-i:]) / (i if i != 0 else i + 1) * 100 for i in range(1, len(initiated[party]))]
    
    initiated_forward = pd.DataFrame(initiated_forward)
    initiated_backward = pd.DataFrame(initiated_backward)
        
    return initiated_forward, initiated_backward, infractions


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

    st.write('# Telegram Chat Analyzer')
    st.write('## Settings')

    threshold = st.number_input('New conversation threshold (in hours):', min_value=1, max_value=24, value=2)
    initiated_forward, initiated_backward, infractions = parse(data, threshold)

    # Write our dashboard
    st.write('## Stats')
    st.write(f'You exchanged a total of {len(data)} messages!')
    st.write(f'You had {len(initiated_forward)} conversations!')

    st.write('## Infractions')
    st.write('An infraction is where neither party has communicated for over 9 months. This is BAD.')

    if infractions == 0:
        st.write('Woohoo! You have no infractions.')
    else:
        st.write(f'Uh oh! You have {infractions} infractions.')

    st.write('## Initiation percentage')
    st.write('This is a graph of the percentage of conversations each of you initiated. For a healthy friendship, both lines should stay above 25%.')
    st.write('### Starting from the beginning')
    st.line_chart(initiated_forward)
    st.write('### Starting from the end')
    st.line_chart(initiated_backward)

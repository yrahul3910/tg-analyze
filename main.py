import argparse
from math import perm
import sys
import json
from datetime import datetime, timedelta

from colorama import Fore, Style
from tqdm import tqdm
import pandas as pd
import streamlit as st
import pendulum


def get_parsed_results(initiated, parties):
    initiated_bools = { party: [x[0] for x in initiated[party]] for party in parties }

    # Get cumulative scores for each party in infractions
    initiated_forward = {}
    initiated_backward = {}
    for party in parties:
        initiated_forward[party] = [
            sum(initiated_bools[party][:i]) / (i if i != 0 else i + 1) * 100
            for i in range(1, len(initiated_bools[party]))
        ]
        initiated_backward[party] = [
            sum(initiated_bools[party][-i:]) / (i if i != 0 else i + 1) * 100
            for i in range(1, len(initiated_bools[party]))
        ]

    initiated_forward = pd.DataFrame(initiated_forward)
    initiated_backward = pd.DataFrame(initiated_backward)

    return initiated_forward, initiated_backward


def is_trivial_message(message: str) -> bool:
    trivial_messages = ["happy birthday", "merry christmas", "happy new year"]
    return any([x in message.lower() for x in trivial_messages])


def parse_complex_message(message):
    total = ""

    for part in message:
        if isinstance(part, str):
            total += f"{part} "
        elif isinstance(part, dict):
            total += f'{part["text"]} '

    return total


def parse_telegram(data, resolution=2):
    RESOLUTION = timedelta(hours=resolution)
    MIN_DELTA = timedelta(weeks=36)
    MIN_MESSAGES = 10

    initiated = {}
    infractions = 0

    data = [message for message in data if "from" in message]
    parties = set(list(map(lambda x: x["from"], data)))

    conv_start = 0
    prev_sender = None

    for i, message in enumerate(tqdm(data)):
        date = datetime.fromisoformat(message["date"])
        text = message["text"]
        sender = message["from"]
        not_sender = list(parties - {sender})[0]

        if i != 0:
            # This is not the first message, so we can check if this is the first message in a new conversation
            if date - datetime.fromisoformat(data[i - 1]["date"]) >= RESOLUTION and sender != data[i - 1]["from"]:
                try:
                    if isinstance(text, list):
                        text = parse_complex_message(text)

                    if not is_trivial_message(text):
                        # Check the number of messages in the previous conversation
                        if i - conv_start < MIN_MESSAGES and prev_sender is not None:
                            # Previous conversation was too short
                            initiated[prev_sender].pop()
                            not_prev_sender = list(parties - {prev_sender})[0]
                            initiated[not_prev_sender].pop()

                        # `sender` initiated a new conversation
                        initiated[sender].append((1, date))
                        initiated[not_sender].append((0, date))

                        prev_sender = sender
                        conv_start = i
                except:
                    print("Message is", message)

            if date - datetime.fromisoformat(data[i - 1]["date"]) >= MIN_DELTA:
                infractions += 1
        else:
            initiated[sender] = [(1, date)]
            initiated[not_sender] = [(0, date)]
    
    last_sent = {}
    for party in parties:
        # Instagram orders them newest first, so we can just iterate through the list
        for i in range(len(initiated[party])):
            if initiated[party][i][0] == 1:
                last_sent[party] = initiated[party][i][1]
                break

    return *get_parsed_results(initiated, parties), infractions, last_sent


def parse_instagram(data, resolution=2):
    RESOLUTION = timedelta(hours=resolution)
    MIN_DELTA = timedelta(weeks=36)
    MIN_MESSAGES = 10

    initiated = {}
    infractions = 0

    parties = set(list(map(lambda x: x["sender_name"], data)))

    for i, message in enumerate(tqdm(data)):
        if "content" not in message:
            continue

        date = datetime.fromtimestamp(message["timestamp_ms"] / 1000.)
        text = message["content"]
        sender = message["sender_name"]
        not_sender = list(parties - {sender})[0]

        conv_start = 0
        prev_sender = None

        if i != 0:
            # This is not the first message, so we can check if this is the first message in a new conversation
            if datetime.fromtimestamp(data[i - 1]["timestamp_ms"] / 1000.) - date >= RESOLUTION and sender != prev_sender:
                try:
                    # Check that this is not a reel
                    if "share" in message and "instagram.com" in message["share"]:
                        continue

                    if not is_trivial_message(text):
                        # Check the number of messages in the previous conversation
                        if i - conv_start < MIN_MESSAGES and prev_sender is not None:
                            # Previous conversation was too short
                            initiated[prev_sender].pop()
                            not_prev_sender = list(parties - {prev_sender})[0]
                            initiated[not_prev_sender].pop()

                        # `sender` initiated a new conversation
                        initiated[sender].append((1, message["timestamp_ms"] / 1000.))
                        initiated[not_sender].append((0, message["timestamp_ms"] / 1000.))

                        prev_sender = sender
                        conv_start = i
                except:
                    print("Message is", message)
                    raise

            if abs(date - datetime.fromtimestamp(data[i - 1]["timestamp_ms"] / 1000.)) >= MIN_DELTA:
                infractions += 1
        else:
            initiated[sender] = [(1, message["timestamp_ms"] / 1000.)]
            initiated[not_sender] = [(0, message["timestamp_ms"] / 1000.)]

    last_sent = {}
    for party in parties:
        # Instagram orders them newest first, so we can just iterate through the list
        for i in range(len(initiated[party])):
            if initiated[party][i][0] == 1:
                last_sent[party] = initiated[party][i][1]
                break

    return *get_parsed_results(initiated, parties), infractions, last_sent


def parse(data, source="telegram", resolution=2):
    if source == "telegram":
        return parse_telegram(data, resolution)
    elif source == "instagram":
        return parse_instagram(data, resolution)
    else:
        print("Invalid source.")
        sys.exit(1)


def info(message):
    print(Fore.GREEN + "[INFO] " + message + Style.RESET_ALL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze your chat logs.")
    parser.add_argument("filename", type=str, help="The filename of the chat log.")
    parser.add_argument(
        "-i",
        "--instagram",
        action="store_true",
        help="Whether the chat log is from Instagram.",
    )
    parser.add_argument(
        "-t",
        "--telegram",
        action="store_true",
        help="Whether the chat log is from Telegram.",
    )
    args = parser.parse_args()

    if args.instagram == args.telegram:
        print("Please specify whether the chat log is from Instagram or Telegram.")
        sys.exit(1)

    filename = args.filename
    with open(filename, "r") as f:
        data = json.load(f)

    if args.instagram:
        source = "instagram"
    else:
        source = "telegram"

    data = data["messages"]
    info(f"Parsing {len(data)} messages.")

    st.write("# Telegram Chat Analyzer")
    st.write("## Settings")

    threshold = st.number_input(
        "New conversation threshold (in hours):", min_value=1, max_value=60, value=2
    )
    initiated_forward, initiated_backward, infractions, last_sent = parse(data, source, threshold)

    # Write our dashboard
    st.write("## Stats")
    st.write(f"You exchanged a total of {len(data)} messages!")
    st.write(f"You had {len(initiated_forward)} conversations!")

    st.write("## Infractions")
    st.write(
        "An infraction is where neither party has communicated for over 9 months. This is BAD."
    )

    if infractions == 0:
        st.write("Woohoo! You have no infractions.")
    else:
        st.write(f"Uh oh! You have {infractions} infractions.")

    st.write("## Initiation percentage")
    st.write(
        "This is a graph of the percentage of conversations each of you initiated. For a healthy friendship, both lines should stay above 25%."
    )

    st.write("## Last started conversations")
    for party in last_sent:
        time_last_sent = pendulum.from_timestamp(last_sent[party]).to_formatted_date_string()
        time_since = pendulum.from_timestamp(last_sent[party]).diff_for_humans()
        st.write(f"* {party} last started a conversation on {time_last_sent} ({time_since}).")

    st.write("### Starting from the beginning")
    st.line_chart(initiated_forward)
    st.write("### Starting from the end")
    st.line_chart(initiated_backward)

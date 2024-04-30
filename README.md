# Chat Analyzer

This program analyzes chat logs for the percentage of non-trivial conversations that each party initiated. Currently, Instagram and Telegram are supported.

To run:

```
streamlit run main.py -- [-i | -t] [path to json]
```

At least one of `-i` and `-t` are required. The former specifies that the JSON is from Instagram, and the latter specifies that the log is from Telegram.

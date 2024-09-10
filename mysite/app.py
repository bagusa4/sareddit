import os
from dotenv import load_dotenv, find_dotenv
import random
import streamlit as st
import praw
import pandas as pd
import numpy as np
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

#load environment variables
load_dotenv(find_dotenv("prawconfig.env"))

# REDDIT CREDENTIALS
REDDIT_CLIENT_ID = st.secrets["REDDIT"]["CLIENT_ID"] if st.secrets["REDDIT"]["CLIENT_ID"] else os.getenv("REDDIT_CLIENT_ID")
REDDIT_USER_AGENT = st.secrets["REDDIT"]["USER_AGENT"] if st.secrets["REDDIT"]["USER_AGENT"] else os.getenv("REDDIT_USER_AGENT")
REDDIT_REDIRECT_URI = st.secrets["REDDIT"]["REDIRECT_URI"] if st.secrets["REDDIT"]["REDIRECT_URI"] else os.getenv("REDDIT_REDIRECT_URI")

# Initialize NLTK
nltk.download('all')
analyzer = SentimentIntensityAnalyzer()
def analyze_sentiment(text):
    sentences = nltk.sent_tokenize(text)
    neg = []
    neu = []
    pos = []
    compound = []
    for sentence in sentences:
        sentiment_scores = analyzer.polarity_scores(sentence)
        neg.append(sentiment_scores['neg'])
        neu.append(sentiment_scores['neu'])
        pos.append(sentiment_scores['pos'])
        compound.append(sentiment_scores['compound'])
    avg_sentiment_scores = {
        'neg': np.mean(neg),
        'neu': np.mean(neu),
        'pos': np.mean(pos),
        'compound': np.mean(compound)
    }
    return avg_sentiment_scores

# Initialize PRAW
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=None,
    user_agent=REDDIT_USER_AGENT,
    redirect_uri=REDDIT_REDIRECT_URI,
)

# Set Title
st.title("SAReddit")
st.header("Sentiment Analysis - Reddit", divider=True)

st.subheader("Reddit Authentication", divider=True)
# Initialize PRAW Reddit Authentication
try:
    auth_url = reddit.auth.url(scopes=["identity", "read"], state=str(random.randint(0, 65000)))
    st.link_button("Auth Reddit", url=auth_url)
except Exception as e:
    st.error(f"An error occurred during authentication: {e}")

# Handle the redirect after OAuth authorization
if 'code' in st.query_params:
    code = st.query_params['code']
    # Complete the authentication process with PRAW
    refresh_token = reddit.auth.authorize(code) 
    st.session_state['refresh_token'] = refresh_token  # Store for later use
    st.success("Authentication successful!")
# If authenticated, create a Reddit instance with the refresh token
if 'refresh_token' in st.session_state:
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=None,
        user_agent=REDDIT_USER_AGENT,
        refresh_token=st.session_state['refresh_token']
    )
    st.write("Authenticated Reddit instance ready!")

st.header("What Insight That You Want ?", divider=True)
# Initialize Parameter For Data Collections
srtitle = st.text_input("SubReddit Title", "All")
sortby = st.selectbox("Sort by", ("Hot", "New", "Top", "Rising", "Search"), index=1)
search = st.text_input("Search Query", disabled=(sortby != "Search"))
limit = st.number_input("Limit", min_value=10)

if sortby == "Hot":
    subreddit = reddit.subreddit(srtitle).hot(limit=limit)
elif sortby == "New":
    subreddit = reddit.subreddit(srtitle).new(limit=limit)
elif sortby == "Top":
    subreddit = reddit.subreddit(srtitle).top(limit=limit)
elif sortby == "Rising":
    subreddit = reddit.subreddit(srtitle).rising(limit=limit)
else:
    subreddit = reddit.subreddit(srtitle).search(search, limit=limit)

if subreddit:
    data = []
    for submission in subreddit:
        s = {
            'id': submission.id,
            'title': submission.title,
            'score': submission.score,
            'body': submission.selftext
        }
        for comment in submission.comments:
            c = {
                'id': comment.id,
                'body': comment.body,
                'score': comment.score
            }
            data.append(c)
        data.append(s)

    df = pd.DataFrame(data)
    def sentiment_score(row):
        if row['title'] == None:
            return analyze_sentiment(row['body'])
        else:
            return analyze_sentiment(str(row['title'])+str(row['body']))
    sentiment_score = df.apply(sentiment_score, axis=1, result_type='expand')
    df = pd.concat([df, sentiment_score], axis=1)

    sentiment_counts = df[['neg', 'neu', 'pos', 'compound']].sum()
    sentiment_percentages = (sentiment_counts / sentiment_counts.sum() * 100).to_frame().T
    
    st.header("Data Chart", divider=True)
    st.write('''
        The compound value is basically the normal of the 3 values negative, positive and neutral.
        So if the compound value leans towards negative then the overall sentiment is negative,
        if the compound value leans towards positive then the overall sentiment is positive.
    ''')
    st.caption(":orange[Compound], :red[Negative], :blue[Neutral], :green[Positive]")
    st.bar_chart(
        data=sentiment_percentages,
        x_label="Category", 
        y_label="Percentage",
        color=['#ffbd45', '#ff4b4b', '#60b4ff', '#3dd56d'],
        stack=False
    )

    st.header("Data Table", divider=True)
    st.dataframe(df)
else:
    st.write("No data available.")

st.header("About", divider=True)
st.write("Hello world!. Created by [@bagusa4](https://github.com/logicxscale/sareddit). Made with :heart:.")

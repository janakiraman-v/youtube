# ------------------------------------------YOUTUBE DATA HARVESTING AND WAREHOUSING-------------------------------------------#
import streamlit as st
from streamlit_option_menu import option_menu
from pyyoutube import Api

# mongoDB imports
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import pandas as pd

# mysql imports
import mysql.connector
import sqlalchemy
from sqlalchemy import create_engine
import pymysql

import re
import plotly.express as px
import isodate

import isodate


api = Api(api_key="AIzaSyCsWVlOilgxmrN9RVg4A6mOKVKiJcHdOXw")

# CREATING A CONNECTION IN MONGODB
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["Youtube_data"]
collection = db.youtube

# CREATING A CONNECTION IN SQL
connect = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root"
)
print(connect)
mycursor = connect.cursor(buffered=True)
# mycursor.execute("USE youtube_db")
engine = create_engine('mysql+pymysql://root:root@localhost:3306/youtube_db?charset=utf8mb4', echo=False)


# PUSHING THE YOUTUBE DATA TO MONGODB
def push_to_mongo(pd_youtube):
    push_status = collection.insert_one(pd_youtube)
    return push_status


# EXTRACTING CHANNEL NAMES AND STORED IN MONGODB
def extract_channel_names():
    channel_names = []
    documents = collection.find()
    for document in documents:
        position_key = 1
        for key, value in document.items():
            if position_key % 2 == 0:
                channel_names.append(value)
                break
            position_key += 1
    return channel_names


# EXTRACTING CHANNEL DETAILS
def get_channel_details(channel_id):
    # channel
    channel = api.get_channel_info(channel_id=channel_id)
    channel_name = channel.items[0].to_dict()["snippet"]["title"]
    full_details_to_store = {}

    full_details_to_store[channel_name] = {
        "channel_name": channel_name,
        "channel_id": channel.items[0].to_dict()['id'],
        "video_count": channel.items[0].to_dict()['statistics']['videoCount'],
        "channel_views": channel.items[0].to_dict()['statistics']['viewCount'],
        "channel_description": channel.items[0].to_dict()["snippet"]["description"],

        "playlists": {},
        "videos": {},
        "comments": {}
    }

    # playlist
    playlists_by_channel = api.get_playlists(channel_id=channel_id, count=5)
    for playlist in playlists_by_channel.items:
        full_details_to_store[channel_name]["playlists"][playlist.to_dict()["id"]] = {
            "playlist_id": playlist.to_dict()["id"],
            "channel_id": playlist.to_dict()['snippet']['channelId'],
            "playlist_title": playlist.to_dict()["snippet"]["title"],
            "videos": []
        }

    # video
    playlist_dict = {}
    for i in [i.id for i in playlists_by_channel.items]:
        if i not in playlist_dict:
            playlist_dict[i] = api.get_playlist_items(playlist_id=i, count=5)
    for key, val in playlist_dict.items():
        for videos in val.items:
            full_details_to_store[channel_name]["playlists"][key]["videos"] += [videos.contentDetails.videoId]
    for key, val in playlist_dict.items():
        for i in val.items:
            vid_dict = {}
            if i.contentDetails.videoId not in full_details_to_store[channel_name]["videos"]:
                video_details = api.get_video_by_id(video_id=i.contentDetails.videoId)
                if len(video_details.items) > 0:
                    video_dict = video_details.items[0].to_dict()
                    vid_dict["video_id"] = i.contentDetails.videoId
                    vid_dict["channel_id"] = channel_id
                    vid_dict["video_name"] = video_dict['snippet']['title']
                    vid_dict["video_description"] = video_dict['snippet']['description']
                    vid_dict["published_at"] = video_dict['snippet']['publishedAt']
                    vid_dict["view_count"] = video_dict['statistics']['viewCount']
                    vid_dict["like_count"] = video_dict['statistics']['likeCount']
                    vid_dict["dislike_count"] = video_dict['statistics']['dislikeCount']
                    vid_dict["comment_count"] = video_dict['statistics']['commentCount']
                    vid_dict["duration"] = video_dict['contentDetails']['duration']
                    vid_dict["thumbnail"] = video_dict['snippet']['thumbnails']
                    vid_dict["caption_status"] = video_dict['contentDetails']['caption']
                    vid_dict["comments"] = []
                    full_details_to_store[channel_name]["videos"][i.contentDetails.videoId] = vid_dict

    # comment
    for video_id in full_details_to_store[channel_name]["videos"]:
        com_dict = {}
        comment_dict = api.get_comment_threads(video_id=video_id, count=5)
        for comment in comment_dict.items:
            video_id = comment.to_dict()['snippet']['videoId']
            comment_id = comment.to_dict()['snippet']['topLevelComment']['id']
            full_details_to_store[channel_name]["videos"][video_id]["comments"] += [comment_id]
            com_dict["channel_id"] = channel_id
            com_dict["Video_id"] = video_id
            com_dict["Comment_Id"] = comment_id
            com_dict["Comment_Text"] = comment.to_dict()['snippet']['topLevelComment']['snippet']['textOriginal']
            com_dict["Comment_Author"] = comment.to_dict()['snippet']['topLevelComment']['snippet']['authorDisplayName']
            com_dict["Comment_PublishedAt"] = comment.to_dict()['snippet']['topLevelComment']['snippet']['publishedAt']
            full_details_to_store[channel_name]["comments"][comment_id] = com_dict

    return {"channel_name": full_details_to_store[channel_name]["channel_name"],
            "data": full_details_to_store[channel_name]}



# MIGRATE TO SQL
def migrate_to_sql(channel_name):
    channel_data = collection.find({"channel_name": channel_name})[0]

    channel_df = pd.DataFrame([[channel_data["data"]["channel_name"], channel_data["data"]["channel_id"],
                                channel_data["data"]["video_count"], channel_data["data"]["channel_views"],
                                channel_data["data"]["channel_description"]]],
                              columns=["Channel_Name", "Channel_Id", "Video_Count", "Channel_Views",
                                       "Channel_Description"])
    channel_df.to_sql('channel', engine, if_exists='append', index=False,
                      dtype={"Channel_Name": sqlalchemy.types.VARCHAR(length=225),
                             "Channel_Id": sqlalchemy.types.VARCHAR(length=225),
                             "Channel_Views": sqlalchemy.types.BigInteger,
                             "Channel_Description": sqlalchemy.types.TEXT})

    playlist = []
    for key, val in channel_data["data"]["playlists"].items():
        playlist.append([key, val["channel_id"], val["playlist_title"]])
    playlist_df = pd.DataFrame(playlist, columns=["Playlist_Id", "Channel_Id", "Playlist_Title"])
    playlist_df.to_sql('playlist', engine, if_exists='append', index=False,
                       dtype={"Playlist_Id": sqlalchemy.types.VARCHAR(length=225),
                              "Channel_Id": sqlalchemy.types.VARCHAR(length=225),
                              "Playlist_Title": sqlalchemy.types.VARCHAR(length=225)})

    video = []
    for key, val in channel_data["data"]["videos"].items():
        video.append([key, val['channel_id'], val["video_name"], val["video_description"], val["published_at"],
                      val["view_count"], val["like_count"], val["dislike_count"], val["comment_count"], val["duration"],
                      val["caption_status"]])
    video_df = pd.DataFrame(video,
                            columns=["Video_Id", 'Channel_Id', "Video_Name", "Video_Description", 'Published_date',
                                     'View_Count', 'Like_Count', 'Dislike_Coun', 'Comment_Count', 'Duration',
                                     'Caption_Status'])
    video_df.to_sql('video', engine, if_exists='append', index=False,
                    dtype={'Video_Id': sqlalchemy.types.VARCHAR(length=225),
                           'Channel_Id': sqlalchemy.types.VARCHAR(length=225),
                           'Video_Name': sqlalchemy.types.VARCHAR(length=225),
                           'Video_Description': sqlalchemy.types.TEXT,
                           'Published_date': sqlalchemy.types.String(length=50),
                           'View_Count': sqlalchemy.types.BigInteger,
                           'Like_Count': sqlalchemy.types.BigInteger,
                           'Dislike_Coun': sqlalchemy.types.Integer,
                           'Comment_Count': sqlalchemy.types.Integer,
                           'Duration': sqlalchemy.types.VARCHAR(length=1024),
                           'Caption_Status': sqlalchemy.types.VARCHAR(length=225)})
    video_df['durationSecs'] = video_df['Duration'].apply(lambda x: isodate.parse_duration(x).total_seconds())

    comment = []
    for key, val in channel_data["data"]["comments"].items():
        comment.append(
            [val["Video_id"], val['channel_id'], val["Comment_Id"], val["Comment_Text"], val["Comment_Author"],
             val["Comment_PublishedAt"]])
    comment_df = pd.DataFrame(comment,
                              columns=['Video_Id', 'Channel_Id', 'Comment_Id', 'Comment_Text', 'Comment_Author',
                                       'Comment_Published_date'])
    comment_df.to_sql('comment', engine, if_exists='append', index=False,
                      dtype={'Video_Id': sqlalchemy.types.VARCHAR(length=225),
                             'Channel_Id': sqlalchemy.types.VARCHAR(length=225),
                             'Comment_Id': sqlalchemy.types.VARCHAR(length=225),
                             'Comment_Text': sqlalchemy.types.TEXT,
                             'Comment_Author': sqlalchemy.types.VARCHAR(length=225),
                             'Comment_Published_date': sqlalchemy.types.String(length=50)})
    return 0


st.set_page_config(layout='wide')
st.header("YouTube Data Harvesting and Warehousing using SQL, MongoDB and Streamlit")


def streamlit_menu(example=2):
    if example == 2:
        selected = option_menu(
            menu_title="YouTube Data Harvesting and Warehousing",
            options=["DATA COLLECTION", "STORE IN MONGODB", "MIGRATION OF DATA TO SQL", "DATA ANALYSIS"],
            # required
            orientation="vertical",
        )
        return selected


# Page Contents
selected = streamlit_menu(example=2)


if selected == "DATA COLLECTION":
    st.write("Channel Name and Channel ID")
    data = {
        'CHANNEL NAME': ['Being Secure', 'NeuralNine', 'Simply Explained', 'AssemblyAI', 'Adam Tech', 'Madan Gowri ', 'Beyond The Ordinary - Tamil Audiobooks',
                         'Almost Everything ', 'HOUSE OF MAVERICK ', 'Take Okay'],
        'CHANNEL ID': ['UCAwMxjDnJbGIKa2dJpgqfbw', 'UC8wZnXYK_CGKlBcZp-GxYPA', 'UCnxrdFPXJMeHru_b4Q_vTPQ',
                       'UCtatfZMf-8EkIwASXM4ts0A', 'UCTIJerXXeEuYuYPSTPblqVg', 'UCY6KjrDBN_tIRFT_QNqQbRQ',
                       'UC_wrYdstZXGkQJKEsrRQRSQ', 'UCqdpvuKq4bShO1cJoFX6zpQ', 'UCrU83y4nqxHQOkmBIid8IBg',
                       'UClbWEQOP8jwcvAw6tYnGX0A']
    }
    df = pd.DataFrame(data)
    st.table(df)

if selected == "STORE IN MONGODB":
    Channel_id = st.text_input("**Enter a Channel ID**:", key="Channel_id", value="")
    st.write("#")
    if st.button('STORE IN MONGODB'):
        channel_info = get_channel_details(Channel_id)
        pushed_to_mongo = push_to_mongo(channel_info)
        st.text_area("Here is the MongoDB output", channel_info)
        if pushed_to_mongo.acknowledged:
            st.markdown('<p style="font-weight:italic;color:blue;">DATA INSERTED IN MONGODB</p>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-weight:italic;color:red;">Error: DATA NOT INSERTED IN MONGODB</p>',
                        unsafe_allow_html=True)


    # Function to clear the collection
    def clear_collection():
        collection.delete_many({})
        st.write("Collection cleared successfully!")


    # Streamlit app
    def main():
        st.write("BY CLICKING ON THE BELOW BUTTON YOU CAN CLEAR THE COLLECTIONS IN MONGODB")
        clear_button = st.button("CLEAR COLLECTION IN MONGODB")

        if clear_button:
            clear_collection()


    if __name__ == '__main__':
        main()

if selected == "MIGRATION OF DATA TO SQL":
    channel_name = extract_channel_names()
    channel_names = st.selectbox("**SELECT THE CHANNEL NAME**:", channel_name)
    st.write("#")
    if st.button('MIGRATE TO SQL'):
        migrate_to_sql(channel_names)
        st.text_area("Here is the SQL output", channel_name)
        collection.delete_one({'channel_name': channel_names})
        st.markdown('<p style="font-weight:Italic;color:blue;">MIGRATED TO SQL</p>', unsafe_allow_html=True)


    # Function to clear all data in multiple tables
    def clear_data():
        mycursor.execute("USE youtube_db")
        tables = ['channel', 'comment', 'playlist', 'video']

        for table in tables:
            query = f"DELETE FROM {table};"
            mycursor.execute(query)
            connect.commit()


    # STREAMLIT APP FOR CLEAR THE TABLE IN SQL
    def main():
        # st.title("Clear Data from Tables")
        clear_button = st.button("CLEAR DATA IN SQL")

        if clear_button:
            clear_data()


    if __name__ == '__main__':
        main()

if selected == "DATA ANALYSIS":
    st.title('HERE YOU CAN ANALYSE THE DATA')
    Questions = ["1. What are the names of all the videos and their corresponding channels",
                 "2. Which channels have the most number of videos, and how many videos do they have",
                 "3. What are the top 10 most viewed videos and their respective channels",
                 "4. How many comments were made on each video, and what are their corresponding video names",
                 "5. Which videos have the highest number of likes, and what are their corresponding channel names",
                 "6. what is the total number of likes and dislikes of each video, and what are their corresponding video names",
                 "7. what is the total number of views for each channel, and what are their corresponding channel names",
                 "8. what is the names of all the channels that have published videos in the year 2022",
                 "9. what is the average duration of all videos in each channel, and what are their corresponding channel names",
                 "10. which videos have the highest number of comments,and what are their corresponding channel names"
                 ]
    input_question = st.selectbox("**SELECT YOUR QUESTION TO GET DATA**:", Questions)
    retrieve_answer_from_sql = pymysql.connect(host="localhost", user="root", password="root", db='youtube_db')
    cursor = retrieve_answer_from_sql.cursor()

    if input_question == '1. What are the names of all the videos and their corresponding channels':
        cursor.execute(
            """SELECT channel.Channel_Name , video.Video_Name FROM channel JOIN video ON video.Channel_Id = channel.Channel_Id""")
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df_1 = pd.DataFrame(result, columns=columns).reset_index()
        df_1.index += 1
        st.write(df_1)

    elif input_question == '2. Which channels have the most number of videos, and how many videos do they have':
            cursor.execute("SELECT Channel_Name, Video_Count FROM channel ORDER BY Video_Count DESC;")
            result = cursor.fetchall()
            df_2 = pd.DataFrame(result, columns=['Channel_Name', 'Video_Count']).reset_index()
            df_2.index += 1
            st.write(df_2)


    elif input_question == '3. What are the top 10 most viewed videos and their respective channels':
        cursor.execute(
            "with channel_rank_data as ( SELECT channel.Channel_Name as channel_name, video.Video_Name as video_name, video.View_Count, row_number() over (partition by channel_name order by video.View_Count desc) as video_rank FROM channel JOIN video ON video.Channel_Id = channel.Channel_Id ) select * from channel_rank_data where video_rank <=10;")
        result = cursor.fetchall()
        df_3 = pd.DataFrame(result, columns=['Channel_Name', 'Video_Name', 'View_Count', 'Rank']).reset_index()
        df_3.index += 1
        st.write(df_3)


    elif input_question == '4. How many comments were made on each video, and what are their corresponding video names':
        cursor.execute(
            "SELECT channel.Channel_Name ,COUNT(*) AS Comment_Count ,video.Video_Name FROM video JOIN comment ON video.Video_Id = comment.Video_Id JOIN channel ON video.Channel_Id = channel.Channel_Id GROUP BY video.Video_Id, video.Video_Name, channel.Channel_Name;")
        result = cursor.fetchall()
        df_4 = pd.DataFrame(result, columns=['Channel_Name', 'Comment_Count', 'Video_Name']).reset_index()
        df_4.index += 1
        st.write(df_4)


    elif input_question == '5. Which videos have the highest number of likes, and what are their corresponding channel names':
            cursor.execute(
                "SELECT channel.Channel_Name, video.Like_Count, video.Video_Name FROM video JOIN channel ON video.Channel_Id = channel.Channel_Id ORDER BY video.Like_Count DESC LIMIT 10;")
            result = cursor.fetchall()
            df_5 = pd.DataFrame(result, columns=['Channel_Name', 'Like_Count', 'Video_Name']).reset_index()
            df_5.index += 1
            st.write(df_5)





    elif input_question == '6. what is the total number of likes and dislikes of each video, and what are their corresponding video names':
        st.write(' In November 2021, YouTube removed the public dislike count from all of its videos.')
        cursor.execute(
            "SELECT channel.Channel_Name, video.Like_Count, video.Video_Name, video.Dislike_Coun FROM video JOIN channel ON video.Channel_Id = channel.Channel_Id ORDER BY video.Dislike_Coun DESC;")
        result = cursor.fetchall()
        df_6 = pd.DataFrame(result, columns=['Channel_Name', 'Like_Count', 'Video_Name', 'Dislike_Coun']).reset_index()
        df_6.index += 1
        st.write(df_6)

    elif input_question == '7. what is the total number of views for each channel, and what are their corresponding channel names':
            cursor.execute("SELECT Channel_Name, Channel_Views FROM channel ORDER BY Channel_Views DESC;")
            result = cursor.fetchall()
            df_7 = pd.DataFrame(result, columns=['Channel_Name', 'Total number of views']).reset_index()
            df_7.index += 1
            st.write(df_7)


    elif input_question == '8. what is the names of all the channels that have published videos in the year 2022':
        cursor.execute(
            "SELECT channel.Channel_Name FROM channel AS channel JOIN video ON channel.Channel_Id = video.Channel_Id WHERE YEAR(video.Published_date) = 2022 GROUP BY channel.Channel_Name;")
        result = cursor.fetchall()
        df_8 = pd.DataFrame(result, columns=['Channel_Name'])
        df_8.index += 1
        st.write(df_8)


    elif input_question == '9. what is the average duration of all videos in each channel, and what are their corresponding channel names':
        cursor.execute(
            "SELECT channel.Channel_Name, AVG(video.Duration) AS average_duration FROM channel JOIN video ON channel.Channel_Id = video.Channel_Id GROUP BY channel.Channel_Name;")
        result = cursor.fetchall()
        df_9 = pd.DataFrame(result, columns=['Channel_Name', 'Duration'])
        df_9.index += 1
        st.write(df_9)


    elif input_question == '10. which videos have the highest number of comments,and what are their corresponding channel names':
        cursor.execute(
            "SELECT channel.Channel_Name, video.Video_Name, video.Comment_Count FROM video JOIN channel ON video.Channel_Id = channel.Channel_Id ORDER BY video.Comment_Count DESC LIMIT 10;")
        result = cursor.fetchall()
        df_10 = pd.DataFrame(result, columns=['Channel_Name', 'Video_Name', 'Comment_Count']).reset_index()
        df_10.index += 1
        st.write(df_10)    

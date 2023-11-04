# youtube_repo
YouTube Data Harvesting and Warehousing using SQL, MongoDB and Streamlit

**Problem Statement**
The assignment is to create Streamlit software that enables users to examine information from various YouTube channels. To access information like channel details, video details, and user engagement, users can enter their YouTube channel ID. Users should be able to gather information from up to 10 distinct channels using the app, which should ease storing the information in a MongoDB database. It should also provide the option to move specific channel data from the data lake to a SQL database for additional analysis. The app should support complex functions, including joining tables for complete channel information, as well as searching and retrieving data from the SQL database.

## **Technology Used**
1. Python
2. MySQL
3. MongoDB
4. Google Client Library
   
## **Approach**
1. Create a Streamlit application using the Python library "Streamlit" to get started. This library offers a simple interface for users to enter a YouTube channel ID, check channel details, and choose channels to migrate.

2. Create a connection to the YouTube API V3 so I may use the Google API client library for Python to receive information about channels and videos.


3. Because MongoDB is an appropriate solution for handling unstructured and semi-structured data, store the obtained data in a MongoDB data lake. To do this, a method to get the prior API request is first written, and the identical data is then stored in the database in three different collections.

4. using a SQL database like MySQL or PostgreSQL for the transfer of the data gathered from various channels, namely the channels, videos, and comments.


5. Join tables in the SQL data warehouse using SQL queries to extract certain channel data based on user input. For that, the foreign and primary keys must be appropriately provided to the previously created SQL table.

6. Utilizing the data visualization features of Streamlit, the retrieved data is presented within the Streamlit application for users to analyze.

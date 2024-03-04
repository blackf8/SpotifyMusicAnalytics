# SpotifyMusicAnalysis
Attempting to learn the basics of web scraping through Selenium by creating a web scraper that records the users currently playing songs and stores the data within a DB. 
This project has been containerized and automated using Docker + Airflow. 
For future work I aim to conduct some data analysis on the results to learn more about my music habits.
![alt text](https://github.com/blackf8/SpotifyMusicAnalytics/blob/main/images/spotify_client.png?raw=true)
Sample Image of my Spotify Client.

## Architechure
![alt text](https://github.com/blackf8/SpotifyMusicAnalytics/blob/main/images/spotify_diagram.png?raw=true)

Our general architecture utilizes docker to host selenium and airflow containers within a docker network. The airflow dags will then run based on a cron schedule, interacting with the selenium container to scrape data, and finally store the results within our local postgresql database. To avoid spotify’s captcha we store the cookies of the currently open selenium session within airflow’s xcom.


Currently, I have this entire process running within one dag. This dag would be running every minute or so and scrape the spotify website for running songs. After designing and implementing this heartbeat dag I realized having an additional dag that runs on a daily schedule would be beneficial. One of the issues I am working on fixing with the first dag is that after each run the selenium web browser cookies are stored within airflow’s xcom db without a garbage collector being implemented. This second daily dag would be used to clean up xcom pushes made throughout the day and run PySpark queries on the time series data.

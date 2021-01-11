# https://developers.google.com/youtube/v3/docs
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import sqlite3, time
from bs4 import BeautifulSoup
import argparse
import sys
import os


global api_key, youtube, props, existing_videos


def db_connector(func):
    '''decorator for db operaitons'''
    def with_connection(*args, **kwargs):
        with sqlite3.connect('youtube.db') as conn:
            try:
                cur = conn.cursor()
                rv = func(cur, *args, **kwargs)
                conn.commit()
            except Exception as ex:
                conn.rollback()
                print('error: ' + str(ex))
                raise
            return rv

    return with_connection


def read_file(file):
    lines = open(file, 'r').read().splitlines()
    return [l for l in lines if l and not l.startswith('#')]


@db_connector
def create_new(cur):
    '''
    To run any function(s), first run get_api_key, to start the Youtube API
    '''
    cur.execute("""CREATE TABLE IF NOT EXISTS tb_channels (
        Channel_ID TEXT PRIMARY KEY,
        Channel_title TEXT,
        Published_At TEXT NOT NULL,
        Country TEXT,
        View_Count INTEGER,
        Subscriber_Count INTEGER,
        Video_Count INTEGER,
        Playlist_Count INTEGER
    )

        """)

    cur.execute("""CREATE TABLE IF NOT EXISTS tb_playlists(
        Playlist_ID TEXT PRIMARY KEY,
        Playlist_title TEXT,
        Channel_ID TEXT NOT NULL,
        Channel_Title TEXT NOT NULL,
        Published_At TEXT NOT NULL,
        Item_Count INTEGER,
        Playlist_Seconds INTEGER,
        Playlist_Duration TEXT,
        Is_Seen INTEGER default 0,
        Worth INTEGER default 0,
        FOREIGN KEY (Channel_ID)
        REFERENCES tb_channels (Channel_ID)
    )
    """)

    cur.execute("""CREATE TABLE IF NOT EXISTS tb_videos (
        Video_ID TEXT PRIMARY KEY,
        Video_title TEXT,
        Is_Seen INTEGER,
        Worth INTEGER,
        Upload_playlistId TEXT,
        Playlist_ID TEXT,
        Published_At TEXT NOT NULL,
        epoch REAL NOT NULL,
        Channel_ID TEXT NOT NULL,
        Channel_Title TEXT NOT NULL,
        View_Count INTEGER,
        Like_Count INTEGER,
        Dislike_Count INTEGER,
        Upvote_Ratio REAL,
        Comment_Count INTEGER,
        Duration TEXT,
        video_seconds INTEGER,
        Is_Licensed INTEGER,
        Is_Deleted INTEGER,
        Is_Downloaded INTEGER default 0,
        FOREIGN KEY (Channel_ID)
        REFERENCES tb_channels (Channel_ID),
        FOREIGN KEY (Playlist_ID)
        REFERENCES tb_playlists (Playlist_ID)
    )
    """)

    cur.execute("""CREATE TABLE IF NOT EXISTS video_history (
        Video_ID TEXT NOT NULL,
        Watched_at TEXT ,
        epoch REAL NOT NULL,
        Is_in_Main INTEGER,
        PRIMARY KEY ( Video_ID, epoch),
        FOREIGN KEY (Video_ID)
        REFERENCES tb_videos (Video_ID)
    )

        """)

    # cur.execute("""CREATE TABLE IF NOT EXISTS tb_channel_check (
    #     Channel_ID TEXT PRIMARY KEY,
    #     Channel_title TEXT,
    #     Last_check TEXT NULL,
    #     Last_epoch REAL NULL,
    #     FOREIGN KEY (Channel_ID) REFERENCES tb_channels (Channel_ID)
    # )
    # """)


def read_properties():
    prop_file = 'app.properties'
    separator = "="
    tmp = {}
    if os.path.exists(prop_file):
        lines = read_file(prop_file)
        for line in lines:
            # Find the name and value by splitting the string
            name, value = line.split(separator, 1)
            tmp[name.strip()] = value.strip()

    global props
    props = tmp
    return tmp


@db_connector
def cache_existing_videos(cur):
    global existing_videos
    existing_videos = set()
    r = cur.execute("SELECT Video_id FROM tb_videos")
    rs = r.fetchall()
    for c in rs:
        existing_videos.add(c[0])


read_properties()
cache_existing_videos()

def get_api_key(key=None):
    token_api_key = 'api_key'
    global api_key, youtube, props
    if key:
        api_key = key
    else:
        if props and props.get(token_api_key):
            api_key = os.getenv(props.get(token_api_key))

    youtube = build('youtube', 'v3', developerKey=api_key)
    return youtube


# get_api_key('Your API Key')

def get_channel_id(ch_name):
    '''
    Increasingly, searching by channel name returns None. Prefer search by ID
    '''
    global youtube
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        forUsername=ch_name
    )
    response = request.execute()
    try:
        sub_count = int(response['items'][0]['statistics']['subscriberCount'])
        if sub_count > 1000000:
            sub_count = str(sub_count / 1000000)
            sub_count = sub_count + 'M Subscribers'
        elif sub_count > 1000:
            sub_count = str(sub_count / 1000)
            sub_count = sub_count + 'K Subscribers'
        else:
            sub_count = str(sub_count) + ' Subscribers'
        ch_id = response['items'][0]['id']

        print(" ")
        print(sub_count)
        return ch_id
    except KeyError:
        print(" ")
        print("          Error : Channel not Found ")
        print(" ")


@db_connector
def table_columns(cur, tablename):
    cur.execute("PRAGMA table_info(" + tablename + ")")
    results = cur.fetchall()
    ret = []
    for r in results:
        ret.append(r[1])
    return ret


def table_column_str(tablename):
    cols = table_columns(tablename)
    cols = [c for c in cols if c not in ['Is_Downloaded', ]]
    colStr = ""
    for c in cols:
        colStr += ',' + c if colStr else c
    colStr = "(" + colStr + ")"
    return colStr


@db_connector
def get_videos_stats(cur, video_ids, flag=1, playlistID=None):
    global youtube
    count1 = 0
    stats = []
    tot_len = 0
    colStr = table_column_str('tb_videos')

    #TODO: batch?
    for i in range(0, len(video_ids), 50):
        res = youtube.videos().list(id=','.join(video_ids[i:i + 50]),
                                    part='snippet,statistics,contentDetails').execute()
        stats += res['items']

    for video in stats:
        count1 += 1

        Video_id = video['id']
        Video_title = video['snippet']['title']
        Upload_playlistId = video['snippet']['channelId']

        if playlistID is not None:
            Playlist_Id = playlistID  # When call is from a playlist
        else:
            cur.execute("SELECT Playlist_ID FROM tb_videos WHERE Video_ID = ?", (Video_id,))
            result = cur.fetchone()
            if result is None:
                Playlist_Id = None
            else:
                if type(result) is tuple:
                    Playlist_Id = result[0]
                elif type(result) is str:
                    Playlist_Id = result
                else:
                    Playlist_Id = None
        Published_At = video['snippet']['publishedAt']
        date_format = "%Y-%m-%dT%H:%M:%SZ"
        epoch = float(time.mktime(time.strptime(Published_At, date_format)))
        Channel_Id = video['snippet']['channelId']
        Channel_Title = video['snippet']['channelTitle']
        try:
            View_Count = video['statistics']['viewCount']
        except:
            View_Count = 0
            flag = 2
        try:
            Like_Count = video['statistics']['likeCount']
        except:
            Like_Count = 0
        try:
            Dislike_Count = video['statistics']['dislikeCount']
        except:
            Dislike_Count = 0
        try:
            Upvote_Ratio = (int(Like_Count) / (int(Like_Count) + (int(Dislike_Count)))) * 100
        except:
            Upvote_Ratio = 0
        try:
            Comment_Count = video['statistics']['commentCount']
        except:
            Comment_Count = 0
        try:
            Duration = str(video['contentDetails']['duration'])
            Duration = Duration.replace('PT', '')
            hh = mm = ss = '00'
            if Duration.find('H') != -1:
                hh = Duration.split('H')[0]
                temp = hh + 'H'
                if len(hh) == 1:
                    hh = '0' + hh
                Duration = Duration.replace(temp, '')
            if Duration.find('M') != -1:
                mm = Duration.split('M')[0]
                temp = mm + 'M'
                if len(mm) == 1:
                    mm = '0' + mm
                Duration = Duration.replace(temp, '')
            if Duration.find('S') != -1:
                ss = Duration.split('S')[0]
                if len(ss) == 1:
                    ss = '0' + ss
            Duration = (hh + ':' + mm + ':' + ss)
            video_seconds = timedelta(hours=int(hh),
                                      minutes=int(mm),
                                      seconds=int(ss)).total_seconds()
            if playlistID is not None:
                tot_len += video_seconds
        except:
            Duration = '0'
            video_seconds = 0
            flag = 2

        try:
            Is_Licensed = video['contentDetails']['licensedContent']
        except:
            Is_Licensed = 0
        Is_Seen = 0  # 0 = not seen    1 = seen
        Worth = 0  # 0 = not rated , ratings = 1(not worth saving)/2(worth saving)
        # Is_Downloaded = 0
        Is_Deleted = 0
        if flag == 1:
            Is_Deleted = 0
        elif flag == 2:
            Is_Deleted = 1
        params = (
            Video_id, Video_title, Is_Seen, Worth, Upload_playlistId, Playlist_Id, Published_At,
            epoch, Channel_Id, Channel_Title, View_Count, Like_Count, Dislike_Count, Upvote_Ratio,
            Comment_Count, Duration, video_seconds,
            Is_Licensed, Is_Deleted)

        if flag == 1:
            cur.execute(
                "INSERT OR REPLACE INTO tb_videos " + colStr +
                " VALUES (?, ?, ?, ?, ?, ?, ? ,? ,? ,? ,? ,? , ?, ?, ?, ?, ?, ?, ?)", params)
        else:
            cur.execute(
                "INSERT OR IGNORE INTO tb_videos " + colStr +
                " VALUES (?, ?, ?, ?, ?, ?, ? ,? ,? ,? ,? ,? , ?, ?, ?, ?, ?, ?, ?)",
                params)

    if tot_len > 0:
        return tot_len


def get_channel_playlists(cur, channel_id, single=False, playlistID=''):
    global youtube
    playlists = []
    playlist_ids = []
    next_page_token = None

    while 1:
        res = youtube.playlists().list(part="snippet,contentDetails",
                                       channelId=channel_id,
                                       pageToken=next_page_token,
                                       maxResults=50
                                       ).execute()
        playlists += res['items']
        next_page_token = res.get('nextPageToken')

        for playlist in playlists:
            Playlist_ID = playlist['id'];
            playlist_ids.append(Playlist_ID)
            if (single == True and playlist['id'] == playlistID) or single == False:
                Playlist_title = playlist['snippet']['title']
                Channel_Id = playlist['snippet']['channelId']
                Channel_Title = playlist['snippet']['channelTitle']
                Published_At = playlist['snippet']['publishedAt']
                Item_Count = playlist['contentDetails']['itemCount']
                Playlist_Seconds = 0
                Playlist_Duration = '0'
                Is_Seen = 0  # 0 = not seen    1 = seen
                Worth = 0  # 0 = not rated , ratings = 1(not worth saving)/2(worth saving)
                params = (
                Playlist_ID, Playlist_title, Channel_Id, Channel_Title, Published_At, Item_Count, Playlist_Seconds,
                Playlist_Duration, Is_Seen, Worth)
                cur.execute("INSERT OR REPLACE INTO tb_playlists VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
        if next_page_token is None:
            break

    playlist_ids = set(playlist_ids)
    playlist_ids = list(playlist_ids)
    count = len(playlist_ids)
    cur.execute("UPDATE tb_channels SET Playlist_Count = ? WHERE Channel_ID = ? ", (count, channel_id))

    return playlist_ids


@db_connector
def get_channel_details(cur, channel_id, single=False, playlistID=''):
    ''' get_channel_details() and  entire_channel(ch_id) use  get_channel_playlists '''
    global youtube

    request = youtube.channels().list(part="snippet,statistics",
                                      id=channel_id
                                      ).execute()

    # print(request['items'][0]['snippet'])

    Channel_Id = channel_id
    Channel_title = request['items'][0]['snippet']['title']
    Published_At = request['items'][0]['snippet']['publishedAt']
    try:
        Country = request['items'][0]['snippet']['country']
    except:
        Country = None
    View_Count = request['items'][0]['statistics']['viewCount']

    Subscriber_Count = request['items'][0]['statistics']['subscriberCount']
    Video_Count = request['items'][0]['statistics']['videoCount']

    params = (Channel_Id, Channel_title, Published_At, Country, View_Count, Subscriber_Count, Video_Count)

    cur.execute("INSERT OR REPLACE INTO tb_channels VALUES (?, ?, ?, ?, ?, ?, ?, 0)", params)

    return get_channel_playlists(cur, Channel_Id, single, playlistID)


@db_connector
def get_playlist_videos(cur, playlistID):
    '''
    get_playlist_videos(playlistID)
    @:param str playlistID: Playlist ID as string
    '''
    @db_connector
    def next(cur, videoIDs, playlistID):
        Playlist_Seconds = get_videos_stats(videoIDs, 1, playlistID)
        Playlist_Duration = str(timedelta(seconds=Playlist_Seconds))
        cur.execute("UPDATE tb_playlists SET Playlist_Seconds = ? WHERE playlist_ID = ? ",
                    (Playlist_Seconds, playlistID))
        cur.execute("UPDATE tb_playlists SET Playlist_Duration = ? WHERE playlist_ID = ? ",
                    (Playlist_Duration, playlistID))

    global youtube
    ch_ID = 'skip'
    videos = []
    next_page_token = None
    video_IDS = []
    while 1:
        res = youtube.playlistItems().list(part="snippet",
                                           maxResults=50,
                                           playlistId=playlistID,
                                           pageToken=next_page_token
                                           ).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')

        if next_page_token is None:
            break

    for video in videos:

        Video_id = video['snippet']['resourceId']['videoId'];
        video_IDS.append(Video_id)
        try:
            ch_ID = video['snippet']['channelId']
        except:
            ch_ID = 'skip'
        params = (Video_id, "", 0, 0, "", "", "")
        cur.execute("INSERT OR IGNORE INTO tb_videos VALUES (?, ?, ?,? ,?, ?, ?, 0,'', '',0,0,0,0,0,'',0,0,0,0)",
                    params)

    print('Videos in this playlist =', len(video_IDS))

    if ch_ID == 'skip':
        return 0
    else:
        get_channel_details(ch_ID, True, playlistID)
        next(video_IDS, playlistID)


@db_connector
def get_channel_videos(cur, channel_id):
    global youtube
    res = youtube.channels().list(id=channel_id,
                                  part='contentDetails').execute()

    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    videos = []
    next_page_token = None
    new_video_ids = []

    while 1:
        res = youtube.playlistItems().list(playlistId=playlist_id,
                                           part='snippet',
                                           maxResults=50,
                                           pageToken=next_page_token).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')

        video_ids = list(map(lambda x: x['snippet']['resourceId']['videoId'], videos))

        if next_page_token is None:
            break

    global existing_videos
    for newVid in video_ids:
        if newVid not in existing_videos:
            new_video_ids.append(newVid)

    print('\nParsing ', len(new_video_ids), ' videos which are not in any playlist for channel ',
          channel_id)
    get_videos_stats(video_ids, flag=0)


@db_connector
def most_watched(cur, n=5):
    cur.execute("SELECT video_history.Video_ID,COUNT(video_history.Video_ID) AS cnt, Video_title FROM video_history \
                    LEFT OUTER JOIN tb_videos on tb_videos.Video_ID = video_history.Video_ID \
                    GROUP BY video_history.Video_ID ORDER BY cnt DESC;")
    results = cur.fetchmany(n)
    print("\t", "  Video Link", "\t", "\t", "\t", "   Times Watched", "\t", "\t", "      Video Name")
    print("-------------------------------------------------------------------------------------------------------")
    for result in results:
        Link = "https://www.youtube.com/watch?v=" + result[0]
        if result[2] is None:
            title = "Video is not available in local database"
        else:
            title = result[2]
        print(Link, '\t', result[1], '\t', title)


@db_connector
def latest_timestamp(cur, channel=None):
    sql = "SELECT Channel_ID, max(epoch) FROM tb_videos"
    if channel:
        sql += " WHERE Channel_ID=?"
        sql += " group by Channel_ID"
        cur.execute(sql, (channel))
    else:
        sql += " group by Channel_ID"
        cur.execute(sql)
    results = cur.fetchall()
    ret = {}
    for r in results:
        ret[r[0]] = r[1]
    return ret


@db_connector
def most_upvoted(cur, channel, upvote, n=5):
    cur.execute("SELECT Video_ID, Video_title FROM tb_videos \
                WHERE Channel_ID=? and Like_Count >= ? ORDER BY epoch DESC;",
                (channel, upvote))
    results = cur.fetchmany(n)
    ret =[]
    for result in results:
        Link = "https://www.youtube.com/watch?v=" + result[0]
        if result[2] is None:
            title = "Video is not available in local database"
        else:
            title = result[2]
        ret.append((Link, title))
    return ret


@db_connector
def early_views(cur, n=5):
    cur.execute("SELECT video_history.Video_ID, video_history.epoch -tb_videos.epoch As diff,video_history.epoch,tb_videos.epoch,tb_videos.Video_title,tb_videos.epoch, Watched_at FROM video_history \
                    LEFT OUTER JOIN tb_videos on tb_videos.Video_id = video_history.Video_ID WHERE (diff-19800) > 0 GROUP BY video_history.Video_ID ORDER BY diff ASC ;")
    results = cur.fetchmany(n)
    print("Video ID", "      Diff in Min", "\t", "Published AT(UTC)", " Watched AT (IST)", "\tVideo Title")
    print("-------------------------------------------------------------------------------------------------------")
    for result in results:
        Link = result[0]
        differ = (int(result[1]) - 19800) / 60
        differ1 = ("{:6d}".format(int(differ // 1)))
        differ2 = ("{:.2f}".format(differ % 1)).replace('0.', '.')
        differ = differ1 + differ2
        print(Link, '\t', differ, '\t', result[2], '\t', result[3], '\t', result[4])


@db_connector
def update_is_seen(cur):
    cur.execute("UPDATE tb_videos SET Is_Seen = 1 WHERE Video_ID IN (SELECT Video_ID FROM tb_videos \
                WHERE Video_ID IN (SELECT Video_ID FROM video_history))")


@db_connector
def update_worth(cur, chList=None):
    global props
    sql = props.get('updateWorth')
    if chList:
        for ch in chList:
            subquery = sql + " and Channel_ID = ?"
            stmt = "UPDATE tb_videos SET worth = 1 WHERE Video_ID IN (" + subquery + ")"
            cur.execute(stmt, (ch, ))
    else:
        cur.execute("UPDATE tb_videos SET worth = 1 WHERE Video_ID IN (" + sql + ")")


@db_connector
def update_is_in_main(cur):
    cur.execute("UPDATE video_history SET Is_in_Main = 1 WHERE Video_ID IN (SELECT Video_ID FROM video_history \
                WHERE Video_ID IN (SELECT Video_ID FROM tb_videos))")


@db_connector
def update_history(cur):
    for i in range(1000):
        cur.execute("SELECT Count(*) FROM video_history")
        tot = cur.fetchone()
        cur.execute("SELECT Video_ID FROM video_history WHERE Is_in_Main = 0 LIMIT 50;")
        temp = cur.fetchall()
        if len(temp) < 2:
            print("All Videos From Watched History are now in main table tb_videos")
            break
        result = []
        for item in temp:
            cur.execute("UPDATE video_history SET Is_in_Main = 1 WHERE Video_ID = ?", (item[0],))
            result.append(item[0])

        print('Parsing Watch History Videos :', (i * 50), ' / ', tot[0], end="\r")
        get_videos_stats(result, 1)
        update_is_in_main()


@db_connector
def load_history(cur, res='n'):
    count_loc_prog = 0
    with open("takeout/history/watch-history.html", encoding='utf-8') as fp:
        soup = BeautifulSoup(fp, 'lxml')
        soup = soup.body

        videos = soup.find_all("div", {"class": "content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1"})

        print(len(videos))

        for video in videos:
            count_loc_prog += 1
            if count_loc_prog % 500 == 0:
                print('Loading into Database : ', count_loc_prog, ' / ', len(videos), end="\r")
            tags = video.find_all('a')
            # try:

            if tags == []:
                continue

            V_link = tags[0].get('href')
            V_link = V_link.split('=')[-1]
            br_tags = video.find_all('br')
            for tag in br_tags:
                watched_at = str(tag.next_sibling)
                if watched_at[-3:-1] == 'IS':
                    final_time = (watched_at)
                    temp = final_time.replace('IST', '+0530')
                    epoch = time.mktime(time.strptime(temp, "%b %d, %Y, %I:%M:%S %p %z"))
            cur.execute("INSERT OR IGNORE INTO video_history VALUES (?,?,?,?)", (V_link, final_time, epoch, 0))

    print("\n Loaded \n")

    if res == 'y' or res == "Y":
        update_history()
    update_is_seen()
    update_is_in_main()


@db_connector
def generate_download(cur, channels, n=50):
    '''
    generate download file from db with worth=1 and Is_Downloaded = 0
    :param cur:
    :param channels:
    :param n:
    :param append: if true, delete old existing file first
    :return:
    '''
    def download_file_path():
        global props
        downloadPath = props.get('download_path')
        filepath = os.path.join(downloadPath, "download_list.txt." + str(int(time.time())))
        return filepath

    print('generating download file')
    filepath = download_file_path()

    with open(filepath, 'w', encoding='utf-8') as fp:
        for channelID in channels:
            if channelID == '':
                cur.execute("SELECT Video_ID FROM tb_videos WHERE Worth = 1 and Is_Downloaded = 0 "
                            + "order by epoch desc LIMIT ?", (n,))
            else:
                try:
                    cur.execute(
                        "SELECT Video_ID FROM tb_videos WHERE Worth = 1 and Is_Downloaded = 0 and Channel_ID = ? order by epoch desc LIMIT ?",
                        (channelID, n))
                except:
                    print("Please enter correct Channel ID")
            down_list = cur.fetchall()
            for item in down_list:
                link = "https://www.youtube.com/watch?v=" + item[0]
                cur.execute("UPDATE tb_videos SET Is_Downloaded = 1 WHERE Video_ID = ?", (item[0],))
                fp.write(link)
                fp.write('\n')

    print('generated file ', filepath)


def entire_channel(ch_id):
    playlists_list = get_channel_details(ch_id)
    count = 0
    print('\nThere are ', len(playlists_list), ' original/imported playlists\n')
    for playlist in playlists_list:
        count += 1
        print('\nParsing playlist ', count, ' \ ', len(playlists_list))
        get_playlist_videos(playlist)
    get_channel_videos(ch_id)


def sync_generate_download():
    global props
    get_api_key()

    if not os.path.exists("youtube.db"):
        create_new()

    channelFile = props.get('channels_file')
    channels = read_file(channelFile)
    chList = []
    for ch in channels:
        if '.' in ch:
            get_playlist_videos(ch.split('.')[1])
        else:
            get_channel_details(ch)
            get_channel_videos(ch)
        chList.append(ch)
    update_worth(chList)
    generate_download(chList, n=100)


if __name__ == "__main__":
    # create_new()
    # temp = input("Enter API KEY \n")
    # get_api_key(temp)
    # get_channel_details('UCJQJ4GjTiq5lmn8czf8oo0Q')
    # get_playlist_videos('PLZHQObOWTQDP5CVelJJ1bNDouqrAhVPev')
    # download_n()
    sync_generate_download()

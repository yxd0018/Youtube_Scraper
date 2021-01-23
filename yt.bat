@echo off
@rem description: batch script to download video with youtube-dl with different sizelution and type.

@rem youtube-dl doesn't support bilibili playlist, need to use annie @ https://github.com/iawia002/annie#installation
@rem -i to list all the formats

@rem pushd %~dp0
@rem cd /d %~dp0
@rem -v # Print various debugging information

set download_default=D:/temp/download
set download_list=D:/temp/download/tmp
set "source="
set "reso="
set /p source="config source: enter=single(use ^ before &), 2=config file, 3=bili: "

IF /i "%source%" == ""  (set location=%download_default%)
IF /i "%source%" == "2" (set location=%download_list%)
IF /i "%source%" == "3" (set location=%download_list%)

set /p reso="resolution: enter=480, 2=720, 3=1080, 4=audio, 5=m3u8: "

set prefix=youtube-dl ^
-i ^
--ignore-config ^
--add-metadata ^
--no-mtime ^
--no-overwrites ^
--no-check-certificate ^
--console-title ^
--yes-playlist ^
--output "%location%/%%(title)s.%%(ext)s"

set aria2=--external-downloader aria2c  ^
--external-downloader-args "-j 16 -x 16 -s 16 -k 1M --console-log-level=error --enable-rpc=false"

set audio_config=--extract-audio ^
--audio-format mp3 ^
--audio-quality 0

set list_config=-a d:/temp/download/ytdl_url.txt

@rem case insensitive
IF /i "%reso%" == ""  goto video
IF /i "%reso%" == "2" goto video
IF /i "%reso%" == "3" goto video
IF /i "%reso%" == "4" goto audio
IF /i "%reso%" == "5" goto m3u8

echo Not valid choice
pause

:video
IF /i "%reso%" == ""  (
    IF /i "%source%" == "3" (set size=32) else (set size=480)
)
IF /i "%reso%" == "2" (
    IF /i "%source%" == "3" (set size=64)  else (set size=720)
)
IF /i "%reso%" == "3" (
    IF /i "%source%" == "3" (set size=80) else (set size=1080)
)

set video_config=--prefer-ffmpeg ^
--ffmpeg-location "c:/PortableApps/ffmpeg/bin" ^
--format "bestvideo[ext=mkv][height<=%size%]+bestaudio[ext=mp3]/bestvideo[ext=mp4][height<=%size%]+bestaudio[ext=mp3]/bestvideo[ext=mp4][height<=%size%]+bestaudio[ext=mp3]/bestvideo[ext=flv][height<=%size%]+bestaudio[ext=mp3]/best[height<=%size%]/best[filesize<100M]/best "

IF /i "%source%" == ""  (set cmd=%prefix% %aria2% %video_config% "%*")
IF /i "%source%" == "2" (set cmd=%prefix% %video_config% %list_config%)
IF /i "%source%" == "3" (set cmd=annie -f %size% -p "%*")
goto commonexit

:audio
set size=480
IF /i "%source%" == "" (set cmd=%prefix% %aria2% %audio_config% "%*")
IF /i "%source%" == "2" (set cmd=%prefix% %audio_config% %list_config%)
goto commonexit

:m3u8
IF /i "%source%" == "" (set cmd=%prefix% "%*")
IF /i "%source%" == "2" (set cmd=%prefix% %list_config%)
goto commonexit

:commonexit
@echo on
%cmd%

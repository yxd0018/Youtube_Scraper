select * from tb_videos where Like_Count > 1000 --and channel_id='UCtXKDgv1AVoG88PLl8nGXmw'
                          and published_at > '2010-01-01'
order by epoch desc;

update tb_videos set Worth=0, Is_Downloaded=0 where worth=1 and Like_Count < 10000 and Channel_Title like '%TED%'
--                                    channel_id='UCtXKDgv1AVoG88PLl8nGXmw'
                                                and published_at < '2010-01-01';

update tb_videos set Is_Downloaded=0 where worth=1 and Like_Count > 10000 and  Channel_Title like '%TED%'
                                       and video_id not in ('5dVcn8NjbwY', 'jmQWOPDqxWA', 'KzIp4IzDPG0', 'z9jXW9r1xr8', 'oIZDtqWX6Fk', 'Xe8fIjxicoo', '7uRPPaYuu44');

select video_id, video_title, Like_Count, channel_id, channel_title, worth, Is_Downloaded from tb_videos
where Worth = 1 order by Channel_ID, epoch desc;

select * from tb_channels;

PRAGMA table_info(tb_videos);

delete from tb_videos where Channel_ID='UCknLrEdhRCp1aegoMqRaCZg';

select channel_id, channel_title from tb_channels where channel_id ='UCCBVCTuk6uJrN3iFV_3vurg'


import asyncio
from datetime import datetime
import math
import os
import streamlink
from typing import List
import subprocess
from ffmpeg import FFmpeg
from streamlink import Streamlink

from infobot.Listener import Listener
from infobot.twitch.TwitchEvents import TwitchEvent
from infobot.twitch.TwitchProfile import TwitchProfile
from infobot.async_util import run_in_executor
import utils.redis_key as redis_key


class TwitchListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)
        self.period = 500000
        self.profiles: List[TwitchProfile] = []
        self.last_subscribe = None
        self.streamlink_session = Streamlink()
        self.streamlink_session.set_plugin_option("twitch", "disable-ads", True)
        self.streamlink_session.set_plugin_option("twitch", "disable-reruns", True)

    async def start(self):
        await super().start()
        self.period = 3
        # self.loop.create_task(self.custom_download())

    @Listener.repeatable
    async def listen(self):
        await self.subscribe_all()

        while True:
            data = await self.manager.db.redis.get_one_from_list_parsed(redis_key.get_streams_data())
            if data is None:
                break

            self.logger.info(data)

            for prof in self.profiles:
                if prof.twitch_id == data['twitch_id']:
                    event = TwitchEvent(prof, data['data'])
                    await event.translate(self.manager.api.twitch)
                    await event.profile.store_to_cache(self.manager.db.redis)
                    # Publish event to Info bot
                    self.loop.create_task(self.manager.event(event))

                    self.logger.info('Export data: {}'.format(event.export()))
                    # Publish event to Twitch/Telegram bot
                    await self.manager.db.redis.publish_event(redis_key.get_streams_forward_data(), event.export())

                    # if event.start and not event.update or event.recovery:
                    #     self.loop.create_task(self.download_stream(event))

    async def subscribe_all(self)->None:
        for profile in self.profiles:
            if profile.need_resubscribe():
                await self.subscribe_profile(profile)
                profile.subscribed()
                await asyncio.sleep(2)

    async def subscribe_profile(self, profile: TwitchProfile)->None:
        self.logger.info('Refreshing stream webhook for {}'.format(profile.twitch_name))
        await self.manager.api.twitch.webhook_subscribe_stream(profile.twitch_id, profile.twitch_name)

    async def update_data(self, start: bool = False):
        try:
            profiles = await self.db.getTwitchProfiles()
            history = await self.db.getTwitchHistory()

            await self.update_profiles(profiles, history, start)
        except Exception as ex:
            self.logger.exception(ex)

    def get_new_profile_instance(self, *args, **kwargs)->TwitchProfile:
        return TwitchProfile(*args, **kwargs)

    async def handle_new_profile(self, profile: TwitchProfile):
        await self.subscribe_profile(profile)

    @run_in_executor
    def download(self, name, url):
        streams = self.streamlink_session.streams(url)
        if streams is None:
            self.logger.info("Failed to get streams data for {}".format(url))
            return

        stream = streams["best"]
        if stream is None:
            self.logger.info("Failed to get best stream quality for {}".format(url))
            self.logger.info(streams)
            return

        for stream_part in self.get_stream_parts(name, stream):
            self.logger.info('Got new stream part, sending for convert')
            self.loop.create_task(self.convert_and_publish(stream_part))

        self.logger.info("End of download()")

    async def custom_download(self):
        self.download("olyashaa", "https://www.twitch.tv/olyashaa")

    async def download_stream(self, event: TwitchEvent):
        if event.profile.twitch_name.lower() != "olyashaa":
            return

        self.logger.info("Starting stream download for {}".format(event.profile.twitch_name))
        self.download(event.profile.twitch_name, "https://twitch.tv/{}".format(event.profile.twitch_name))

    def get_stream_parts(self, name, stream):
        self.logger.info("Downloading stream parts for {}".format(stream.url))
        fd = stream.open()

        current_size = 0
        total_size = 0
        kb = 1024
        part = 1
        max_file_size = kb * 1024 * 1024 * 10
        file_pattern = "streams/{}_{}_{}.ts".format(datetime.now().strftime("%Y%m%d_%H%M%S"), name, "{}")
        filename = file_pattern.format(0)

        if not os.path.exists('streams'):
            os.makedirs('streams')

        while True:
            data = None
            try:
                data = fd.read(kb * 100)
            except IOError:
                # End of stream
                break

            if data is None:
                self.logger.info("Finished")
                break

            if current_size == 0:
                self.logger.info("Starting to download part {}".format(part))
                filename = file_pattern.format(part)
                try:
                    os.remove(filename)
                except:
                    pass

            current_size += len(data)
            total_size += len(data)

            f = open(filename, "ab")
            f.write(data)
            f.close()

            if current_size > max_file_size:
                yield {"part": part, "filename": filename, "size": current_size, "duration": 0, "height": 1080, "width": 1920}
                part += 1
                current_size = 0

        if current_size > 0:
            yield {"part": part, "filename": filename, "size": current_size, "duration": 0, "height": 1080, "width": 1920}

    async def convert_and_publish(self, stream):
        await self.convert_stream(stream)


    async def convert_stream(self, stream):
        input_file = stream['filename']
        output_file = input_file.replace('.ts', '.mp4')

        ffmpeg = FFmpeg() \
            .input(url=input_file) \
            .output(url=output_file, format='mp4', safe=0, vcodec='libx264', acodec='aac', movflags='faststart')

        @ffmpeg.on('start')
        def on_start(arguments):
            self.logger.info('Starting stream convert with arguments: {}'.format(arguments))

        @ffmpeg.on('completed')
        def on_completed():
            self.logger.info('Stream converted successfully {}'.format(stream))

        await ffmpeg.execute()

        # Delete original .ts file
        try:
            os.remove(input_file)
        except:
            pass

        # telegram upload limit
        max_file_size = 2000000000

        total_runtime = self.get_video_length(output_file)
        if total_runtime is None or total_runtime <= 0:
            self.logger.error("Received runtime value as {} for file {}".format(total_runtime, output_file))
            return
        stream['duration'] = total_runtime

        total_size = self.get_video_size(output_file)
        if total_size > max_file_size:
            part_count = math.ceil(total_size / max_file_size)
        else:
            part_count = 1

        # Need to split
        if part_count > 1:
            length_of_part = total_runtime / part_count
            self.logger.info("Splitting file {} of length {} into {} peaces by {} seconds".format(output_file, total_runtime, part_count, length_of_part))
            stream['duration'] = length_of_part
            convert_from = 0.0
            convert_to = length_of_part
            current_subpart = 1

            while convert_to <= total_runtime:
                partname = output_file.replace(".mp4", ".split{}.mp4".format(current_subpart))
                self.logger.info("Generating part from {} to {} into {}".format(convert_from, convert_to, partname))

                ffmpeg = FFmpeg() \
                    .input(url=input_file) \
                    .output(url=partname, format='mp4', safe=0, vcodec='copy', acodec='copy', ss=convert_from, t=convert_to)
                await ffmpeg.execute()

                stream['converted'] = partname
                self.loop.create_task(self.manager.publish_stream_video(None, stream))
                convert_from = convert_to
                convert_to += length_of_part
                current_subpart += 1

            # Big file not needed anymore
            try:
                os.remove(output_file)
            except:
                pass
        else:
            self.loop.create_task(self.manager.publish_stream_video(None, stream))

    def get_video_length(self, filename):
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of",
                                 "default=noprint_wrappers=1:nokey=1", filename],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        return float(result.stdout)

    def get_video_size(self, filename):
        result = subprocess.run(["ffprobe", "-i", filename, "-show_entries",
                                 "format=size", "-v", "quiet", "-of", 'csv="p=0"'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        return float(result.stdout)
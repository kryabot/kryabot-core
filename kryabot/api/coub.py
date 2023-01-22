from api.core import Core
from ffmpeg import FFmpeg
from mutagen.mp3 import MP3
import aiofiles
import math
import uuid
import os
import shutil

import io


class Coub(Core):
    def __init__(self):
        super().__init__()

    async def get_coub_part_by_url(self, coub_url: str):
        coub_url = coub_url.replace("https://", "http://")
        coub_url = coub_url.replace("coub.com/view/", "coub.com//api/v2/coubs/")

        api_resp = await self.make_get_request(coub_url)

        try:
            directlink_audio = api_resp["file_versions"]["html5"]["audio"]["high"]["url"]
        except:
            directlink_audio = api_resp["file_versions"]["html5"]["audio"]["med"]["url"]

        try:
            directlink_video = api_resp["file_versions"]["html5"]["video"]["high"]["url"]
        except:
            directlink_video = api_resp["file_versions"]["html5"]["video"]["med"]["url"]

        headers = {"User-agent": "Mozilla/5.0"}
        raw_video = await self.download_file_io(url=directlink_video, headers=headers)
        raw_audio = await self.download_file_io(url=directlink_audio, headers=headers)
        return raw_video, raw_audio, api_resp["duration"]

    async def get_coub_io(self, coub_url: str)->io.BytesIO:
        dir_name = str(uuid.uuid4())
        os.mkdir(dir_name)
        file = None
        try:
            self.logger.info('Getting coub {}'.format(coub_url))
            io_video, io_audio, video_duration = await self.get_coub_part_by_url(coub_url)

            video_name = '{}/video.mp4'.format(dir_name)
            audio_name = '{}/audio.mp3'.format(dir_name)
            text_name = '{}/concat.txt'.format(dir_name)
            result_name = '{}/result.mp4'.format(dir_name)

            async with aiofiles.open(video_name, mode='wb') as f:
                await f.write(io_video.getbuffer())
                await f.flush()

            async with aiofiles.open(audio_name, mode='wb') as f:
                await f.write(io_audio.getbuffer())
                await f.flush()

            audio = MP3(audio_name)
            repeats = math.ceil(audio.info.length) / video_duration
            self.logger.info("Video duration: {}, audio duration: {}, coub video repeats: {}".format(video_duration, audio.info.length, repeats))

            async with aiofiles.open(text_name, mode='w', encoding='utf-8') as f:
                for x in range(0, int(math.ceil(repeats))):
                    f.write("file 'file:{}'\n".format(video_name))

            ffmpeg = FFmpeg()\
                .option('-y')\
                .option('-f', 'concat')\
                .option('-safe', '0')\
                .input(url=text_name)\
                .input(url=audio_name)\
                .output(url=result_name)

            @ffmpeg.on('start')
            def on_start(arguments):
                self.logger.info('Starting coub merge with arguments: {}'.format(arguments))

            # @ffmpeg.on('progress')
            # def time_to_terminate(progress):
            #     # Gracefully terminate when more than 200 frames are processed
            #     if progress.frame > 200:
            #         ffmpeg.terminate()

            @ffmpeg.on('completed')
            def on_completed():
                self.logger.info('Coub {} merge completed'.format(coub_url))

            await ffmpeg.execute()

            file = io.BytesIO()
            chunk_size = 4096
            async with aiofiles.open(result_name, mode='rb') as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    file.write(chunk)

                file.name = "coub.mp4"
                file.seek(0)
        except Exception as e:
            self.logger.exception(e)

        try:
            shutil.rmtree(dir_name)
        except OSError as e:
            print("Error: %s : %s" % (dir_name, e.strerror))

        return file

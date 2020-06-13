from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto, MessageMediaGeoLive, MessageMediaPoll, \
    MessageMediaDice, MessageMediaGame
import io
from hashlib import sha256

async def get_media_info(media):
    media_id = ''
    media_type = ''
    access_hash = ''
    file_ref = ''
    mime = ''
    file_size = 0

    if media is None:
        return media_id, media_type, access_hash, file_ref, mime, file_size

    if type(media) is MessageMediaDocument:
        media_id = str(media.document.id)
        media_type = 'MessageMediaDocument'
        access_hash = str(media.document.access_hash)
        file_ref = media.document.file_reference
        mime = media.document.mime_type
        file_size = media.document.size
    elif type(media) is MessageMediaPhoto:
        media_id = str(media.photo.id)
        media_type = 'MessageMediaPhoto'
        access_hash = str(media.photo.access_hash)
        file_ref = media.photo.file_reference
        mime = 'image/jpeg'
        file_size = 0
    elif type(media) is MessageMediaGeoLive:
        media_type = 'MessageMediaGeoLive'
        access_hash = str(media.geo.access_hash)
        file_ref = media.geo.long
        media_id = media.geo.lat
    elif type(media) is MessageMediaPoll:
        media_type = 'MessageMediaPoll'
        media_id = media.poll.id
    elif type(media) is MessageMediaDice:
        media_type = 'MessageMediaDice'
        media_id = media.emoticon
    elif type(media) is MessageMediaGame:
        media_type = 'MessageMediaGame'
        media_id = media.game.short_name

    return media_id, media_type, access_hash, file_ref, mime, file_size


async def get_document_sha(client, message):
    file = io.BytesIO()
    await client.download_media(message=message, file=file)
    file.seek(0)
    return sha256(file.read()).digest()

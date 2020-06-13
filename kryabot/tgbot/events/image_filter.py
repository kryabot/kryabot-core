from tgbot.commands.common.media import get_media_info
from api.scanmedia import ScanMedia
import io
from PIL import Image
from tgs.exporters.gif import export_gif
from tgs.parsers.tgs import parse_tgs


async def get_image_data(client, message):
    if message.media is None:
        return None

    media_id, media_type, access_hash, file_ref, file_mime, file_size = await get_media_info(message.media)

    if file_mime == '':
        return

    mime_list = file_mime.split('/')
    file = io.BytesIO()
    await client.download_media(message=message, file=file)

    if mime_list[1] == 'webp':
        file = await convert_webp_to_jpeg(file)
        mime_list[1] = 'jpeg'
        file_mime = 'image/jpeg'

    if mime_list[1] == 'x-tgsticker':
        file = await convert_tgs_to_gif(file)
        mime_list[1] = 'gif'
        file_mime = 'image/gif'

    file.seek(0)
    with open('{}.{}'.format(media_id, mime_list[1]), 'wb') as out:  ## Open temporary file as bytes
        out.write(file.read())  ## Read bytes into file
    file.seek(0)

    print(message.stringify())
    try:
        #scanner = ScanMedia()
        #resp = await scanner.scan_image_by_bytes(file, file_mime)
        #return resp
        resp = await client.api.gc.scan_image_safety(file.read())
        return resp
    except Exception as e:
        print(str(e))


async def convert_webp_to_jpeg(file_bytes):
    file_bytes.seek(0)
    converted = io.BytesIO()
    im = Image.open(file_bytes).convert("RGB")
    im.save(converted, "jpeg")
    return converted


async def convert_tgs_to_gif(file_bytes):
    file_bytes.seek(0)
    converted = io.BytesIO()
    tgs_anim = parse_tgs(file_bytes)
    print(tgs_anim)
    export_gif(tgs_anim, converted)

    return converted

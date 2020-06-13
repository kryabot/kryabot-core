from api.core import Core


class ScanMedia(Core):
    def __init__(self, cfg=None):
        super().__init__(cfg=cfg)
        self.endpoint = 'https://northeurope.api.cognitive.microsoft.com/contentmoderator/moderate/v1.0/ProcessImage/Evaluate'
        self.key = 'db31d5b8aa1347079046234f79f80fd4'

    # the following MIME types are supported
    # Content-Type: image/gif
    # Content-Type: image/jpeg
    # Content-Type: image/png
    # Content-Type: image/bmp
    async def scan_image_by_bytes(self, image_bytes, image_type):
        headers = {'Content-Type': image_type,
                   'Ocp-Apim-Subscription-Key': self.key}

        return await self.make_post_request_data(url=self.endpoint, body=image_bytes, headers=headers)

    async def scan_image_by_local_path(self, path, image_type):
        headers = {'Content-Type': image_type,
                   'Ocp-Apim-Subscription-Key': self.key}

    async def test_scan(self):
        headers = {'Content-Type': 'application/json',
                   'Ocp-Apim-Subscription-Key': self.key}

        body = {
            "DataRepresentation": "URL",
            "Value": "https://moderatorsampleimages.blob.core.windows.net/samples/sample.jpg"
        }

        return await self.make_post_request(url=self.endpoint, headers=headers, body=body)
from api.core import Core
import base64


class GoogleCloud(Core):
    def __init__(self, cfg=None):
        super().__init__(cfg=cfg)

    def get_api_key(self):
        return self.cfg.getgetGoogleVisionConfig()['API_KEY']

    async def scan_image_safety(self, image):
        content = base64.b64encode(image)

        base64_string = content.decode('utf-8')
        req = {}
        req['image'] = {}
        req['image']['content'] = base64_string
        req['features'] = []
        feature = {'type': 'SAFE_SEARCH_DETECTION', 'maxResults': 1}
        req['features'].append(feature)

        return await self.vision_scan_image(request=req)

    async def scan_image_safety_url(self, image_url):
        req = {}
        req['image'] = {}
        req['image']['source'] = {}
        req['image']['source'] = {"imageUri": image_url}
        req['features'] = []
        feature = {'type': 'SAFE_SEARCH_DETECTION', 'maxResults': 1}
        req['features'].append(feature)

        return await self.vision_scan_image(request=req)

    async def vision_scan_image(self, request):
        body = {"requests": []}
        body['requests'].append(request)
        print(body)
        url = 'https://vision.googleapis.com/v1/images:annotate?key={key}'.format(key=self.get_api_key())
        return await self.make_post_request(url=url, body=body)
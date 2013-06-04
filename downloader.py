from hashlib import md5
import json
import logging
import os
import sys
import urlparse

from project_runpy.tim import env
from project_runpy.heidi import ColorizingStreamHandler
import requests


# http://zootool.com/api/docs/users
url_endpoint = 'http://zootool.com/api/users/items/'
download_base = 'download'


class Store(object):
    data = None
    filename = 'Info.json'
    meta = None

    def __init__(self):
        self.path = os.path.join(download_base, 'Info.json')
        if os.path.isfile(self.path):
            try:
                with open(self.path) as fh:
                    self.data = json.load(fh)
            except ValueError:
                logger.warn('meta json corrupted, starting over')
                self.data = {}
        else:
            self.data = {}

    def add(self, key, meta):
        self.data[key] = meta

    def save(self):
        # dump meta
        with open(self.path, 'w') as fh:
            json.dump(self.data, fh, indent=2)


def get_filename_from_url(url):
    path = urlparse.urlparse(url).path
    return os.path.split(path)[-1]


def download(url, save_path):
    """Because urlretrieve is a wimp."""
    with open(save_path, 'wb') as fh:
        response = requests.get(url, stream=True)
        for block in response.iter_content(1024):
            if not block:
                break
            fh.write(block)


def get_meta(item, path):
    """Get metadata about an item."""
    hash = md5(open(path, 'rb').read()).hexdigest()
    return dict(
        uid=item['uid'],
        title=item['title'],
        added=item['added'],
        description=item['description'],
        tags=item['tags'],
        url=item['url'],
        source=item['referer'],
        hash=hash,
    )


def main(username):
    offset = 0
    while True:
        params = dict(
            apikey=env.get('ZOOTOOL_API_KEY'),
            username=username,
            limit=100,
            offset=offset,
        )
        response = requests.get(url_endpoint, params=params)
        data = response.json()
        if len(data) == 0:
            logger.info('done!')
            break
        if not os.path.isdir(download_base):
            os.mkdir(download_base)
        for item in data:
            url = item['url']
            filename = get_filename_from_url(url)
            assert filename
            save_path = filename  # TODO sort into tags
            full_save_path = os.path.join(download_base, save_path)
            if not os.path.isfile(full_save_path):
                logger.info('Downloading {} -> {}'.format(url, save_path))
                download(url, full_save_path)
            else:
                logger.debug('File already exists: {}'.format(save_path))
            store.add(save_path, get_meta(item, full_save_path))
        offset += 100
    store.save()


logger = logging.getLogger('downloader')
# hack to keep from adding handler multiple times
if not len(logger.handlers):
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ColorizingStreamHandler())

if __name__ == "__main__":
    store = Store()
    main(sys.argv[1])

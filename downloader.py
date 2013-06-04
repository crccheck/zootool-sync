import logging
import os
import sys
import urlparse
import urllib

from project_runpy.tim import env
from project_runpy.heidi import ColorizingStreamHandler
import requests


# http://zootool.com/api/docs/users
url_endpoint = 'http://zootool.com/api/users/items/'
download_base = 'download'


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


def main(username):
    global response
    params = dict(
        apikey=env.get('ZOOTOOL_API_KEY'),
        username=username,
    )
    response = requests.get(url_endpoint, params=params)
    data = response.json()
    if not os.path.isdir(download_base):
        os.mkdir(download_base)
    # TODO de-paginate
    for item in data:
        url = item['url']
        filename = get_filename_from_url(url)
        assert filename
        save_path = os.path.join(download_base, filename)  # TODO sort into tags
        if not os.path.isfile(save_path):
            logger.info('Downloading {} -> {}'.format(url, save_path))
            download(url, save_path)
        else:
            logger.debug('File already exists: {}'.format(save_path))


logger = logging.getLogger('downloader')
# hack to keep from adding handler multiple times
if not len(logger.handlers):
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ColorizingStreamHandler())

if __name__ == "__main__":
    main(sys.argv[1])

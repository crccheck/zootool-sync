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


def get_filename_from_url(url):
    path = urlparse.urlparse(url).path
    return os.path.split(path)[-1]


def main(username):
    global response
    params = dict(
        apikey=env.get('ZOOTOOL_API_KEY'),
        username=username,
    )
    response = requests.get(url_endpoint, params=params)
    data = response.json()
    # TODO de-paginate
    for item in data:
        url = item['url']
        filename = get_filename_from_url(url)
        assert filename
        save_path = 'download/{}'.format(filename)  # TODO sort into tags
        if not os.path.isfile(save_path):
            logger.info('Downloading {} -> {}'.format(url, save_path))
            urllib.urlretrieve(url, filename)
        else:
            logger.debug('File already exists: {}'.format(save_path))


logger = logging.getLogger('downloader')
# hack to keep from adding handler multiple times
if not len(logger.handlers):
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ColorizingStreamHandler())

if __name__ == "__main__":
    main(sys.argv[1])

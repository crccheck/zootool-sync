#! /usr/bin/env python
"""
Zootool Downloader

Usage: downloader.py [options] <directory>

Options:
  -u --username=<username>  Zootool Username
  -k --key=<api key>        Zootool Api Key

You can also specify the username and key in the environment as ZOOTOOL_USERNAME
and ZOOTOOL_API_KEY.
"""
from hashlib import md5 as hashfunc
import json
import logging
import os
import urlparse

from docopt import docopt
from project_runpy import env, ColorizingStreamHandler
import requests


# http://zootool.com/api/docs/users
url_endpoint = 'http://zootool.com/api/users/items/'


class Store(object):
    filename = 'Info.json'

    def __init__(self):
        self.path = os.path.join('.', 'Info.json')
        if os.path.isfile(self.path):
            try:
                with open(self.path) as fh:
                    self.data = json.load(fh)
            except ValueError:
                logger.warn('meta json corrupted, starting over')
                self.data = {}
        else:
            self.data = {}
        self.find_local_files()
        self.setup_existing()

    def __contains__(self, item):
        return item['uid'] in self.existing_uids

    def find_local_files(self):
        """Find what files we have locally."""
        local_files = {}
        for root, dirnames, filenames in os.walk('.'):
            for filename in filenames:
                actual_path = os.path.normpath(os.path.join(root, filename))
                if os.path.isdir(actual_path):
                    continue
                key = md5(os.path.join(actual_path))
                if key in local_files:
                    logger.debug('duplicate file found on disk: {}'.format(actual_path))
                local_files[key] = actual_path
        self.local_files = local_files

    def setup_existing(self):
        """Allows us to look up store items by hash or uids."""
        existing_hashes = {}
        existing_uids = {}
        lost = []
        for key, item in self.data.items():
            if not os.path.isfile(key):
                logger.debug('lost file: {}'.format(key))
                lost.append(key)
            if item['hash'] in existing_hashes:
                # TODO delete the one that does not actually exist
                logger.warn('duplicate file found in data: {} {}'.format(key, existing_hashes[item['hash']]))
            existing_hashes[item['hash']] = key
            existing_uids[item['uid']] = key
        self.existing = existing_hashes
        self.existing_uids = existing_uids
        if lost:
            self.relink_files(lost)

    def relink_files(self, lost):
        """Fix files in datastore that got unlinked. User may have moved files around."""
        for old_file in lost:
            actual_file = self.local_files[self.data[old_file]['hash']]
            self.data[actual_file] = self.data[old_file]
            self.data.pop(old_file)
            logger.debug('relinking {} -> {}'.format(old_file, actual_file))
        self.save()

    def add(self, key, meta):
        self.data[key] = meta
        self.existing[meta['hash']] = key
        # if meta['hash'] in self.existing:
        #     self.existing.pop(meta['hash'])
        # else:
        #     print "new item found!", key

    def save(self):
        # if self.existing:
        #     print "orphaned files:", self.existing
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


def md5(path):
    return hashfunc(open(path, 'rb').read()).hexdigest()


def get_meta(item, path):
    """Get metadata about an item."""
    return dict(
        uid=item['uid'],
        title=item['title'],
        added=item['added'],
        description=item['description'],
        tags=item['tags'],
        url=item['url'],
        source=item['referer'],
        hash=md5(path),
    )


def main(username):
    offset = 0
    while True:
        params = dict(
            apikey=api_key,
            username=username,
            limit=100,
            offset=offset,
        )
        response = requests.get(url_endpoint, params=params)
        data = response.json()
        if len(data) == 0:
            logger.info('done!')
            break
        for item in data:
            if item['type'] != 'image':
                logger.debug('SKIPPING: Wrong type: {}'.format(item['type']))
                continue
            url = item['url']
            filename = get_filename_from_url(url)
            assert filename
            if item in store:
                logger.debug('SKIPPING: File already downloaded: {}'.format(filename))
                continue
            save_path = filename  # TODO sort into tags
            if os.path.isfile(save_path):
                logger.warn('SKIPPING: File already exists: {}'.format(save_path))
                continue
            else:
                logger.info('Downloading {} -> {}'.format(url, save_path))
                download(url, save_path)
            meta = get_meta(item, save_path)
            store.add(save_path, meta)
        if len(data) < 100:
            # don't need to check next page
            break
        offset += 100
    store.save()


logger = logging.getLogger('downloader')
# hack to keep from adding handler multiple times
if not len(logger.handlers):
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ColorizingStreamHandler())

if __name__ == "__main__":
    arguments = docopt(__doc__)
    download_base = arguments['<directory>']
    username = arguments['--username'] or env.get('ZOOTOOL_USERNAME')
    api_key = arguments['--key'] or env.get('ZOOTOOL_API_KEY')
    cwd = os.getcwd()
    try:
        if not os.path.isdir(download_base):
            os.mkdir(download_base)
        os.chdir(download_base)
        store = Store()
        main(username)
    except:
        raise
    finally:
        os.chdir(cwd)

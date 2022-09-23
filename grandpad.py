import requests
import yaml
import os
from urllib.parse import urljoin
from pprint import pprint


class GrandPad:
    """Class used to access GrandPad's API"""

    def __init__(self):
        """Instantiate object to access GrandPad information for an account"""

        # Load configuration file
        with open ('config.yml') as config_file:
            try:
                self.config = yaml.safe_load(config_file)
            except yaml.YAMLError as yaml_error:
                print(yaml_error)

        # Make media download folder if it doesn't exist
        if not os.path.exists(self.config['media_folder']):
            os.mkdir(self.config['media_folder'])

        # Initialize API session
        self.session = requests.Session()
        payload = {
            'email': self.config['email'],
            'password': self.config['password'],
            'client': 'puma'}
        r = self.session.post(
            f'{self.config["api_url"]}/session/from_password', data=payload)
        self.session_id = r.json()['session']

        # Get and save list of GrandPad users
        self.users = self.call('/feed/recent').json()['users']

    def call(self, resource, payload={}):
        """Make a call to the GrandPad API."""

        # Add session ID to payload
        payload['session'] = self.session_id

        # Form request URL by joining API URL with resource parameter
        url = urljoin(self.config['api_url'], resource.strip('/'))

        return self.session.post(url, data=payload)

    def posts(self, payload={}):
        """Generate list of all posts, starting with most recent."""

        # If no limit is specified, set item limit per page to maximum
        if 'limit' not in payload:
            payload['limit'] = 100

        # Get all posts from given page
        page = self.call('/feed/recent', payload).json()
        for post in page['posts']:
            yield post

        # If there are more pages, return those posts
        this_page = page['paging']['self']['before']
        next_page = page['paging']['next']['before']
        if next_page != this_page:
            for post in self.posts({'before': next_page}):
                yield post

    def media(self, media_key):
        """Fetch a piece of media given a media key."""

        payload = {
            'media_key': media_key,
            'size': 'default'}

        return self.call('/media/download_redirect', payload)

    def write_media(self, media_json, media_folder=None):
        """Save a piece of media given its JSON information."""

        # If there is nothing to write, jump ship
        if not media_json:
            return
        # If no media folder was specified, use default
        if not media_folder:
            media_folder = self.config['media_folder']

        # Parse values from JSON and create path to save file
        mid = media_json['id']
        key = media_json['media_key']
        extension = media_json['type'].split('/')[-1]
        path = os.path.join(media_folder, f'{mid}.{extension}')

        # Get media file and save it locally
        content = self.media(key).content
        with open(path, 'wb') as f:
            f.write(content)


if __name__ == '__main__':
    # Create object to access GrandPad information
    grandpad = GrandPad()

    # Get list of all posts to be able to write data to file
    posts = list(grandpad.posts())

    # Write files with user data and post data
    with open('posts.yml', 'w') as f:
        f.write(yaml.dump(posts))
    with open('users.yml', 'w') as f:
        f.write(yaml.dump(grandpad.users))

    # Go through posts looking for media files and save them
    for post in posts:
        pprint(post)
        if 'media' in post:
            grandpad.write_media(post['media'])
        for comment in post['comments']:
            if 'media' in comment:
                grandpad.write_media(comment['media'])

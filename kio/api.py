import requests


adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)


def request(url, path, access_token, params=None):
    return session.get('{}{}'.format(url, path),
                       headers={'Authorization': 'Bearer {}'.format(access_token)}, timeout=10,
                       params=params)

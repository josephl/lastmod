# This is a pattern I use often to cache web resources I scrape

from datetime import datetime, timezone
import email.utils
from http.client import HTTPResponse
import os
import typing
import urllib.request


def get_last_modified(path: os.PathLike) -> typing.Union[datetime, None]:
    """
    Get last modified timestamp of file in UTC
    :raises PermissionError: on insufficient privileges on path
    """
    if not os.path.exists(path):
        raise FileNotFoundError
    if not os.access(path, os.W_OK):
        raise PermissionError(f"Insufficient privileges to access: '{path}'")
    stat = os.stat(path)
    cache_mdt = datetime.fromtimestamp(stat.st_mtime)
    return cache_mdt.astimezone(timezone.utc)


def serialize_last_modified(timestamp: datetime) -> str:
    """
    Format timezone-aware datetime for 'If-Modified-Since' header
    """
    return email.utils.format_datetime(timestamp, usegmt=True)


def parse_last_modified(last_mod: str) -> datetime:
    """
    :param last_mod_str: Value from 'Last-Modified' response header
    """
    return email.utils.parsedate_to_datetime(last_mod)


def mark_last_modified(path: os.PathLike, mod_dt: datetime) -> None:
    """
    Mark :path: file with modified time :mod_dt: (as system local time)
    """
    stat = os.stat(path)
    # Last-Modified header doesn't utilize ms - yet
    set_mtime = int(mod_dt.astimezone().timestamp())
    os.utime(path, (stat.st_atime, set_mtime))


def urlopen(
    cache_path: os.PathLike,
    url: typing.Union[str, urllib.request.Request],
    *args,
    **kwargs,
) -> typing.Tuple[HTTPResponse, bytes]:
    """
    Wrapper for urllib.request.urlopen(...)
    :param cache_path: path to filename for cached file including basename
    :returns: {http.client.HTTPResponse,urllib.error.HTTPError}, {payload,None}
        payload - HTTPResponse.read() if 200
    """
    if isinstance(url, urllib.request.Request):
        request = url
    else:
        request = urllib.request.Request(url)
    try:
        last_mod = get_last_modified(cache_path)
        last_mod_str: str = serialize_last_modified(last_mod)
        request.add_header("If-Modified-Since", last_mod_str)
    except FileNotFoundError:
        pass
    try:
        response = urllib.request.urlopen(request, *args, **kwargs)
        if response.status == 200:
            new_last_mod = parse_last_modified(response.headers.get("Last-Modified"))
            body = response.read()
            cache_dirname = os.path.dirname(cache_path)
            if not os.path.isdir(cache_dirname):
                os.mkdir(cache_dirname)
            with open(cache_path, "wb") as f:
                f.write(body)
            mark_last_modified(cache_path, new_last_mod)
        else:
            body = None
    except urllib.error.HTTPError as err:
        response = err
        if err.status == 304:
            with open(cache_path, "rb") as f:
                body = f.read()
        else:
            raise
    return response, body

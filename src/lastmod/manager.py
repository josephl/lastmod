from configparser import ConfigParser, SectionProxy
from contextlib import contextmanager
import json
import logging
import os
import sqlite3
import typing
import urllib.request
import uuid


NAMESPACE = "lastmod"


class CacheManager:
    """
    Use as the interface for URL requests
    :param cache_path: parent directory for storing/reading cached payloads
    :param db: path to SQLite3 database for response records
    """

    @classmethod
    def from_config(
        cls,
        config_ini: typing.Union[ConfigParser, SectionProxy, os.PathLike, None] = None,
    ):
        """
        Factory function for using config file instantiation
        """
        if isinstance(config_ini, ConfigParser):
            section = config_ini[NAMESPACE]
        elif isinstance(config_ini, SectionProxy):
            section = config_ini
        elif isinstance(config_ini, str):
            config = ConfigParser()
            config.read(config_ini)
            section = config[NAMESPACE]
        return cls(cache_path=section.get("cache_path"), db=section.get("db"))

    def __init__(
        self,
        cache_path: typing.Optional[os.PathLike],
        db: typing.Optional[os.PathLike] = None,
    ):
        if not cache_path:
            raise ValueError("Must specify cache_path in argument or config")
        self.cache_path = cache_path
        self.db = db

    def get_cached_response(self, request: urllib.request.Request) -> dict:
        """
        Serialize request URL to a subpath relative to self.cache_path
        """
        url = request.get_full_url()
        cur = self._cx.cursor()
        cur.execute("SELECT * FROM response WHERE url = ?", (url,))
        return cur.fetchone()

    @contextmanager
    def database_connection(self):
        try:
            self._cx = sqlite3.connect(self.db)
            self.init_db(self._cx)
            self._cx.row_factory = self.response_dict_factory
            yield self._cx
        except Exception:
            raise
        finally:
            self._cx.close()
            self._cx = None

    @staticmethod
    def init_db(cx):
        cur = cx.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS response (
                url TEXT PRIMARY KEY,
                headers TEXT,
                location TEXT
            )
            """
        )

    @staticmethod
    def response_dict_factory(cursor, row):
        """
        Convert fetched rows to dict
        Set connection.row_factory = <this method>
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.row_factory
        """
        data = {}
        for i, col in enumerate(cursor.description):
            data[col[0]] = row[i]
        return data

    def generate_cache_location(self, url: str) -> os.PathLike:
        """
        Create a unique cache location for a URL (absolute path)
        """
        basename = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
        return os.path.abspath(os.path.join(self.cache_path, basename))

    @staticmethod
    def normalize_headers(headers: typing.Dict) -> str:
        """
        Normalization is lower-casing keys, then serialize the result to JSON
        """
        norm = {}
        for k, v in headers.items():
            norm[k.lower()] = v
        return json.dumps(norm)

    def insert_response(self, url: str, headers: typing.Dict, location: os.PathLike):
        """
        Create record for response
        """
        headers = self.normalize_headers(headers)
        self._cx.execute(
            "INSERT OR REPLACE INTO response VALUES (?, ?, ?)",
            (url, headers, location),
        )
        self._cx.commit()

    @contextmanager
    def urlopen(
        self,
        url: typing.Union[str, urllib.request.Request],
        data: typing.Any = None,
        timeout: typing.Union[int, float, None] = None,
        **kwargs,
    ):
        """
        Primary method to make URL request
        Accepts arguments matching urllib.request.urlopen(...)
        :param url: resource to fetch
        :param cache_dest: destination to cache payload
            if not specified, automatically determines location within self.cache_path
        """
        if isinstance(url, urllib.request.Request):
            request = url
        else:
            request = urllib.request.Request(url)
        with self.database_connection():
            cached_resp = self.get_cached_response(request)
            if cached_resp:
                cache_dest = cached_resp.get("location")
            if cache_dest:
                cache_dest = os.path.abspath(cache_dest)
            if cached_resp and os.path.exists(cache_dest):
                cached_headers = json.loads(cached_resp["headers"])
                last_modified = cached_headers.get("last-modified")
                if last_modified:
                    request.add_header("If-Modified-Since", last_modified)
            try:
                resp = urllib.request.urlopen(request, data, timeout, **kwargs)
                logging.info(f"Request {resp.status}: {resp.url}")
                if resp.status == 200:
                    body = resp.read()
                    try:
                        yield body
                    finally:
                        cache_dest = cache_dest or self.generate_cache_location(
                            request.full_url
                        )
                        self.insert_response(request.full_url, resp.headers, cache_dest)
                        with open(cache_dest, "wb") as f:
                            f.write(body)
            except urllib.error.HTTPError as err:
                logging.warning(f"Error {err.status}: {err.url}")
                if err.status == 304 and cache_dest:
                    with open(cache_dest, "rb") as f:
                        body = f.read()
                        yield body
                else:
                    raise


if __name__ == "__main__":
    from argparse import ArgumentParser

    logging.basicConfig(level=logging.INFO)
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to INI config")
    parser.add_argument(
        "-p", "--cache-path", help="Parent directory for caching payload files"
    )
    parser.add_argument("-d", "--db", help="SQLite3 database for response data")
    parser.add_argument("url", help="Fetch url")
    parsed_args = parser.parse_args()
    if parsed_args.cache_path and parsed_args.db:
        mgr = CacheManager(parsed_args.cache_path, parsed_args.db)
    elif parsed_args.config:
        mgr = CacheManager.from_config(parsed_args.config)
    else:
        raise ValueError(
            "Specify cache path and database path by config or command-line args"
        )
    with mgr.urlopen(parsed_args.url) as f:
        print(f.decode())

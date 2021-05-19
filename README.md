# lastmod

Simple Python (>=3.6) package for caching URI requests using HTTP headers (response) `Last-Modified` / (request) `If-Modified-Since` (default) or optionally with (response) `ETag` / (request) `If-Match`. All dependecies are in the Python 3 standard library.

## Installation

To install this package (virtualenv recommended):
```
pip install git+https://github.com/josephl/lastmod.git
```

## Configuration

* `cache_path` - directory to store requested bodies of URI requests
* `db` - Path to SQLite3 database to manage request records
* (TODO) `use_etags` - To use `ETag` instead of `Last-Modified`, supply `use_etags` option to `CacheManager`. Must use the `db` option for this
* (TODO) `size_limit` - Set this to maximum payload file size on disk (in MB)
* (TODO) `zip_format` - If set, compress file using the specified format (accepts `gzip`, `bz2`, `lzma`)

Each of these options can also be set in an INI config in section `lastmod` and pass to `CacheManager.from_config(config)`.

## Usage

`urlopen(...)` caches requests to a specified `cache_path` directory and syncs the "Last-Modified" HTTP response header to the system's file status modification timestamp (`st_mtime`).
On subsequent requests, `urlopen(...)` sets the "If-Modified-Since" request header.
* If `200`, overwrite the cache and update the file's modified system timestamp
* If `304`, load data from cached file

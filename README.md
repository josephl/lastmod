# Last Mod

Simple, Python (>=3.6) module to use the "Last-Modified" HTTP header to avoid repeatedly requesting the same unmodified remote source unnecessarily.

`urlopen(...)` caches requests to a specified `cache_path` directory and syncs the "Last-Modified" HTTP response header to the system's file status modification timestamp (`st_mtime`).
On subsequent requests, `urlopen(...)` sets the "If-Modified-Since" request header.
* If `200`, overwrite the cache and update the file's modified system timestamp
* If `304`, load data from cached file

TODO: Grant an option to use a SQLite database for caching modification metadata:
* Avoids updating cached file's system mtime which is admittedly kind of dirty
* Allows usage of etags instead of timestamps, which are likely more reliable and aren't affected by Last-Modified timestamps' limitation of whole seconds granularity

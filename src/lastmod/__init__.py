from .manager import CacheManager


if __name__ == "__main__":
    from argparse import ArgumentParser
    import logging

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

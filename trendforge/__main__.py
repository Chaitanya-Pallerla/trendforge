"""CLI: python -m trendforge [run|serve]"""

from __future__ import annotations

import argparse
import functools
import http.server
import logging
import sys

from .config import CONFIG


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trendforge", description="TrendForge AI — daily trend intelligence")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="collect data and rebuild site/data + reports")
    p_run.add_argument("--no-ai", action="store_true", help="skip the Claude analysis layer")
    p_run.add_argument("--ai-now", action="store_true", help="run the AI step even if it isn't due yet")
    p_run.add_argument("--no-reddit", action="store_true", help="skip Reddit")
    p_run.add_argument("-v", "--verbose", action="store_true")

    p_serve = sub.add_parser("serve", help="serve the dashboard locally")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.cmd == "run":
        if args.no_reddit:
            import os
            os.environ["TRENDFORGE_REDDIT"] = "0"
            object.__setattr__(CONFIG, "reddit_enabled", False)
        from .pipeline import run
        run(use_ai=not args.no_ai, force_ai=args.ai_now)
        return 0

    if args.cmd == "serve":
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(CONFIG.site_dir))
        with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
            print(f"TrendForge dashboard: http://127.0.0.1:{args.port}")
            httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())

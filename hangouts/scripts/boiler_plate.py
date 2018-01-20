"""Common framework used to run hangups examples."""

import argparse
import asyncio
import logging
import os

import hangups
import appdirs


def run_example(example_coroutine, *extra_args):
    args = _get_parser(extra_args).parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    cookies = hangups.auth.get_auth_stdin(args.token_path)
    client = hangups.Client(cookies)
    loop = asyncio.get_event_loop()
    task = asyncio.ensure_future(_async_main(example_coroutine, client, args),
                                 loop=loop)

    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        task.cancel()
        loop.run_until_complete(task)
    finally:
        loop.close()


def _get_parser(extra_args):
    """Return ArgumentParser with any extra arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    dirs = appdirs.AppDirs('hangups', 'hangups')
    default_token_path = os.path.join(dirs.user_cache_dir, 'refresh_token.txt')
    parser.add_argument(
        '--token-path', default=default_token_path,
        help='path used to store OAuth refresh token'
    )
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='log detailed debugging messages'
    )
    for extra_arg in extra_args:
        parser.add_argument(extra_arg, required=True)
    return parser


async def _async_main(example_coroutine, client, args):
    """Run the example coroutine."""
    task = asyncio.ensure_future(client.connect())

    on_connect = asyncio.Future()
    client.on_connect.add_observer(lambda: on_connect.set_result(None))
    done, _ = await asyncio.wait(
        (on_connect, task), return_when=asyncio.FIRST_COMPLETED
    )
    await asyncio.gather(*done)

    try:
        await example_coroutine(client, args)
    except asyncio.CancelledError:
        pass
    finally:
        await client.disconnect()
        await task

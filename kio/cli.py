import datetime

import click

import time
from zign.api import get_named_token
from clickclick import AliasedGroup, print_table, OutputFormat

import kio
import stups_cli.config
from kio.api import request
from kio.time import normalize_time


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

output_option = click.option('-o', '--output', type=click.Choice(['text', 'json', 'tsv']), default='text',
                             help='Use alternative output format')


def parse_time(s: str) -> float:
    '''
    >>> parse_time('2015-04-14T19:09:01.000Z') > 0
    True
    '''
    try:
        utc = datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ')
        ts = time.time()
        utc_offset = datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts)
        local = utc + utc_offset
        return local.timestamp()
    except Exception as e:
        print(e)
        return None


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Kio CLI {}'.format(kio.__version__))
    ctx.exit()


@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.option('-V', '--version', is_flag=True, callback=print_version, expose_value=False, is_eager=True,
              help='Print the current version number and exit.')
@click.pass_context
def cli(ctx):
    ctx.obj = stups_cli.config.load_config('kio')


def get_token():
    try:
        token = get_named_token(['uid'], None, 'kio', None, None)
    except:
        raise click.UsageError('No valid OAuth token named "kio" found. Please use "zign token -n kio".')
    return token


def parse_since(s):
    return normalize_time(s, past=True).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def get_url(config: dict):
    url = config.get('url')
    if not url:
        raise click.ClickException('Missing configuration URL. Please run "stups configure".')
    return url


@cli.command()
@output_option
@click.option('-s', '--since', default='1d')
@click.option('-l', '--limit', help='Limit number of results', type=int, default=20)
@click.pass_obj
def applications(config, output, since, limit, **kwargs):
    '''Show applications'''
    url = get_url(config)

    token = get_token()

    params = {}
    r = request(url, '/apps', token['access_token'], params=params)
    r.raise_for_status()
    data = r.json()

    rows = []
    for row in data:
        row['last_modified_time'] = parse_time(row['last_modified'])
        rows.append(row)

    # we get the newest violations first, but we want to print them in order
    rows.sort(key=lambda r: r['id'])

    with OutputFormat(output):
        print_table(['id', 'team_id', 'name', 'subtitle', 'last_modified_time'],
                    rows, titles={'last_modified_time': 'Modified'}, max_column_widths={'name': 32, 'subtitle': 32})


def main():
    cli()

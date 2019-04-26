import datetime

import click
import json

import time
import zign.api
from clickclick import AliasedGroup, print_table, OutputFormat, Action

import kio
import stups_cli.config
from kio.api import request, session
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


def get_token(scopes=None):
    try:
        token = zign.api.get_token('kio', scopes or ['uid'])
    except Exception as e:
        raise click.UsageError(str(e))
    return token


def parse_since(s):
    return normalize_time(s, past=True).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def get_url(config: dict):
    url = config.get('url')
    if not url:
        raise click.ClickException('Missing configuration URL. Please run "stups configure".')
    return url


@cli.group(cls=AliasedGroup)
def applications():
    '''Manage applications'''
    pass


@applications.command('list')
@output_option
@click.option('-s', '--since')
@click.option('-t', '--team', help='Filter by team')
@click.option('--incident-contact', help='Filter by 24x7 incident contact')
@click.option('-a', '--all', is_flag=True, help='List all applications (also disabled)')
@click.pass_obj
def list_apps(config, output, since, team, incident_contact, **kwargs):
    '''List applications'''
    url = get_url(config)
    token = get_token()

    since_str = parse_since(since) if since else ''

    params = {}
    r = request(url, '/apps', token, params=params)
    r.raise_for_status()
    data = r.json()

    rows = []
    for row in data:
        if not row['active'] and not kwargs['all']:
            continue

        if team and row['team_id'] != team:
            continue

        if incident_contact and row.get('incident_contact', '') != incident_contact:
            continue

        if row['last_modified'] < since_str:
            continue

        row['last_modified_time'] = parse_time(row['last_modified'])
        rows.append(row)

    # we get the newest violations first, but we want to print them in order
    rows.sort(key=lambda r: r['id'])

    with OutputFormat(output):
        print_table(['id', 'team_id', 'incident_contact', 'name', 'subtitle', 'last_modified_time'],
                    rows, titles={'last_modified_time': 'Modified'}, max_column_widths={'name': 32, 'subtitle': 32})


@applications.command('show')
@output_option
@click.pass_obj
@click.argument('application_id')
def show_app(config, application_id, output):
    '''Show application'''
    url = get_url(config)
    token = get_token()

    r = request(url, '/apps/{}'.format(application_id), token)
    r.raise_for_status()

    rows = [{'key': k, 'value': v} for k, v in sorted(r.json().items())]

    with OutputFormat(output):
        print_table(['key', 'value'], rows)


@applications.command('update')
@click.pass_obj
@click.argument('application_id')
@click.argument('key_val_pairs', nargs=-1)
def update(config, application_id, key_val_pairs):
    '''Update a single application

    kio app up APPLICATION_ID KEY1=VAL1 ..'''
    url = get_url(config)
    token = get_token()

    r = request(url, '/apps/{}'.format(application_id), token)
    r.raise_for_status()
    data = r.json()
    for key_val in key_val_pairs:
        key, sep, val = key_val.partition('=')
        if key not in data:
            raise click.UsageError('Field "{}" does not exist'.format(key))
        if not val:
            raise click.UsageError('Value missing for field "{}". You must provide KEY=VAL pairs.'.format(key))
        if isinstance(data[key], bool):
            val = val == 'true'
        data[key] = val
    # remove fields which we can't update
    for key in ('id', 'last_modified', 'last_modified_by', 'criticality_level', 'created', 'created_by'):
        del data[key]
    with Action('Updating application {}..'.format(application_id)):
        r = session.put('{}/apps/{}'.format(url, application_id),
                        headers={'Authorization': 'Bearer {}'.format(token),
                                 'Content-Type': 'application/json'},
                        timeout=10,
                        data=json.dumps(data))
        r.raise_for_status()


def main():
    cli()

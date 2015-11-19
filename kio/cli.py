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


def get_token():
    try:
        token = zign.api.get_token('kio', ['uid'])
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


@cli.group(cls=AliasedGroup, invoke_without_command=True)
@output_option
@click.option('-s', '--since')
@click.option('-t', '--team', help='Filter by team')
@click.option('-a', '--all', is_flag=True, help='List all applications (also disabled)')
@click.option('-l', '--limit', help='Limit number of results', type=int, default=20)
@click.pass_context
def applications(ctx, output, since, team, limit, **kwargs):
    '''Show applications'''
    if ctx.invoked_subcommand:
        return

    config = ctx.obj
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

        if row['last_modified'] < since_str:
            continue

        row['last_modified_time'] = parse_time(row['last_modified'])
        rows.append(row)

    # we get the newest violations first, but we want to print them in order
    rows.sort(key=lambda r: r['id'])

    with OutputFormat(output):
        print_table(['id', 'team_id', 'name', 'subtitle', 'last_modified_time'],
                    rows, titles={'last_modified_time': 'Modified'}, max_column_widths={'name': 32, 'subtitle': 32})


@applications.command('print')
@click.pass_obj
@click.argument('application_id')
def print_app(config, application_id):
    url = get_url(config)
    token = get_token()

    r = request(url, '/apps/{}'.format(application_id), token)
    r.raise_for_status()
    print(r.json())


@cli.group(cls=AliasedGroup)
def versions():
    '''Manage application versions'''
    pass


@versions.command('list')
@output_option
@click.argument('application_id')
@click.option('-s', '--since', default='60d')
@click.pass_obj
def list_versions(config, application_id, output, since):
    '''Show application versions'''
    url = get_url(config)
    token = get_token()

    since_str = parse_since(since)

    params = {}
    r = request(url, '/apps/{}/versions'.format(application_id), token, params=params)
    r.raise_for_status()
    data = r.json()

    rows = []
    for row in data:
        if row['last_modified'] < since_str:
            continue
        r = request(url, '/apps/{}/versions/{}/approvals'.format(application_id, row['id']), token)
        row['approvals'] = ', '.join(['{}: {}'.format(x['approval_type'], x['user_id']) for x in r.json()])
        row['last_modified_time'] = parse_time(row['last_modified'])
        rows.append(row)

    # we get the newest violations first, but we want to print them in order
    rows.sort(key=lambda r: r['last_modified_time'])

    with OutputFormat(output):
        print_table(['application_id', 'id', 'artifact', 'approvals', 'last_modified_time'],
                    rows, titles={'last_modified_time': 'Modified'})


@versions.command('create')
@click.argument('application_id')
@click.argument('version')
@click.argument('artifact')
@click.option('-m', '--notes', help='Notes', default='')
@click.pass_obj
def create_version(config, application_id, version, artifact, notes):
    '''Create a new application version'''
    url = get_url(config)
    token = get_token()

    data = {'artifact': artifact, 'notes': notes}
    with Action('Creating version {} {}..'.format(application_id, version)):
        r = session.put('{}/apps/{}/versions/{}'.format(url, application_id, version),
                        headers={'Authorization': 'Bearer {}'.format(token),
                                 'Content-Type': 'application/json'},
                        timeout=10,
                        data=json.dumps(data))
        r.raise_for_status()


@versions.command('approve')
@click.argument('application_id')
@click.argument('version')
@click.option('-t', '--approval-type', help='Approval type', default='DEPLOY')
@click.option('-m', '--notes', help='Notes', default='')
@click.pass_obj
def approve_version(config, application_id, version, approval_type, notes):
    '''Approve application version'''
    url = get_url(config)
    token = get_token()

    data = {'approval_type': approval_type, 'notes': notes}
    with Action('Approving version {} {}..'.format(application_id, version)):
        r = session.post('{}/apps/{}/versions/{}/approvals'.format(url, application_id, version),
                         headers={'Authorization': 'Bearer {}'.format(token),
                                  'Content-Type': 'application/json'},
                         timeout=10,
                         data=json.dumps(data))
        r.raise_for_status()


@versions.command('show')
@output_option
@click.argument('application_id')
@click.argument('version')
@click.pass_obj
def show_version(config, application_id, version, output):
    '''Show version details'''
    url = get_url(config)
    token = get_token()

    r = request(url, '/apps/{}/versions/{}'.format(application_id, version), token)
    r.raise_for_status()

    rows = [{'key': k, 'value': v} for k, v in sorted(r.json().items())]

    r = request(url, '/apps/{}/versions/{}/approvals'.format(application_id, version), token)
    r.raise_for_status()

    for approval in r.json():
        txt = '{approval_type} by {user_id} on {approved_at}'.format(**approval)
        rows.append({'key': 'approvals', 'value': txt})

    with OutputFormat(output):
        print_table(['key', 'value'], rows)


def main():
    cli()

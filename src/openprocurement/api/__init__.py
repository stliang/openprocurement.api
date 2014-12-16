# -*- coding: utf-8 -*-
"""Main entry point
"""
import gevent.monkey
gevent.monkey.patch_all()
import os
import pkg_resources
from pyramid.config import Configurator
from openprocurement.api.auth import AuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy as AuthorizationPolicy
from pyramid.renderers import JSON, JSONP
from pyramid.events import NewRequest
from couchdb import Server
from openprocurement.api.design import sync_design
from openprocurement.api.migration import migrate_data
from boto.s3.connection import S3Connection, Location
from openprocurement.api.traversal import factory


VERSION = int(pkg_resources.get_distribution(__package__).parsed_version[0])
if os.environ.get('READTHEDOCS', None) == 'True':
    os.environ['TZ'] = 'Europe/Kiev'


def set_renderer(event):
    request = event.request
    try:
        json = request.json_body
    except ValueError:
        json = {}
    pretty = isinstance(json, dict) and json.get('options', {}).get('pretty') or request.params.get('opt_pretty')
    jsonp = request.params.get('opt_jsonp')
    if jsonp and pretty:
        request.override_renderer = 'prettyjsonp'
        return True
    if jsonp:
        request.override_renderer = 'jsonp'
        return True
    if pretty:
        request.override_renderer = 'prettyjson'
        return True


def main(global_config, **settings):
    config = Configurator(
        settings=settings,
        root_factory=factory,
        authentication_policy=AuthenticationPolicy(settings['auth.file'], __name__),
        authorization_policy=AuthorizationPolicy(),
    )
    config.add_renderer('prettyjson', JSON(indent=4))
    config.add_renderer('jsonp', JSONP(param_name='opt_jsonp'))
    config.add_renderer('prettyjsonp', JSONP(indent=4, param_name='opt_jsonp'))
    config.add_subscriber(set_renderer, NewRequest)
    config.include("cornice")
    config.route_prefix = '/api/{}'.format(VERSION)
    config.scan("openprocurement.api.views")

    # CouchDB connection
    server = Server(settings.get('couchdb.url'))
    config.registry.couchdb_server = server
    db_name = os.environ.get('DB_NAME', settings['couchdb.db_name'])
    if db_name not in server:
        server.create(db_name)
    config.registry.db = server[db_name]

    # sync couchdb views
    sync_design(config.registry.db)

    # migrate data
    migrate_data(config.registry.db)

    # S3 connection
    if 'aws.access_key' in settings and 'aws.secret_key' in settings and 'aws.bucket' in settings:
        connection = S3Connection(settings['aws.access_key'], settings['aws.secret_key'])
        config.registry.s3_connection = connection
        bucket_name = settings['aws.bucket']
        if bucket_name not in [b.name for b in connection.get_all_buckets()]:
            connection.create_bucket(bucket_name, location=Location.EU)
        config.registry.bucket_name = bucket_name
    return config.make_wsgi_app()

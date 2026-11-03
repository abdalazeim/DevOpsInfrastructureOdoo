import os
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run Odoo Infrastructure Manager'

    def add_arguments(self, parser):
        parser.add_argument('--action', default='tui')
        parser.add_argument('--profile', default='profiles/example.yaml')
        parser.add_argument('--api-host', default='127.0.0.1')
        parser.add_argument('--api-port', type=int, default=8787)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        sys.path.insert(0, base_dir)
        try:
            from app.main import main
        except ImportError:
            from infrastructure_core.app.main import main
        sys.argv = ['manage.py', 'infra_run']
        if options['profile']:
            sys.argv.extend(['--profile', options['profile']])
        if options['action']:
            sys.argv.extend(['--action', options['action']])
        if options['dry_run']:
            sys.argv.append('--dry-run')
        if options['api_host']:
            sys.argv.extend(['--api-host', options['api_host']])
        if options['api_port']:
            sys.argv.extend(['--api-port', str(options['api_port'])])
        main()

"""Bounded Jenkins smoke execution, restricted to the exact bundled harmless job."""
import base64
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None  # never forward credentials to a redirected origin


def verify_smoke(config, execute=False):
    user, token = os.environ.get(config.jenkins_user_env), os.environ.get(config.jenkins_token_env)
    if not user or not token or not config.jenkins_job:
        return dict(status='NEEDS_CONFIGURATION', detail='Configure a smoke job and credential environment references')
    origin = urllib.parse.urlsplit(config.jenkins_url)
    if origin.username or origin.password or origin.query or origin.fragment:
        return dict(status='NEEDS_CONFIGURATION', detail='Jenkins URL must not contain credentials/query/fragment')
    if origin.scheme != 'https' and not (origin.scheme == 'http' and origin.hostname in ('127.0.0.1', 'localhost', '::1')):
        return dict(status='NEEDS_CONFIGURATION', detail='Jenkins credentials require HTTPS or loopback HTTP')
    base = config.jenkins_url.rstrip('/') + '/'
    job = base + 'job/' + urllib.parse.quote(config.jenkins_job, safe='') + '/'
    authorization = 'Basic ' + base64.b64encode((user + ':' + token).encode()).decode()
    opener = urllib.request.build_opener(NoRedirect())

    def request(url, data=None, extra=None):
        if not url.startswith(base):
            raise ValueError('Jenkins response points outside configured server')
        req = urllib.request.Request(url, data=data, headers={'Authorization': authorization, **(extra or {})})
        return opener.open(req, timeout=10)

    try:
        with request(job + 'config.xml') as response:
            document = ET.fromstring(response.read(1024 * 1024))
        expected = (Path(__file__).resolve().parents[2] / 'deployment/jenkins/Jenkinsfile.smoke').read_text(encoding='utf-8')
        if (document.findtext('./definition/script') or '').strip() != expected.strip():
            return dict(status='NEEDS_CONFIGURATION', detail='Job must use the exact bundled smoke script; no arbitrary job is executed')
        if not execute:
            return dict(status='NOT_VERIFIED', detail='Smoke definition verified; use --run-jenkins-smoke to execute it')
        headers = {}
        try:
            with request(base + 'crumbIssuer/api/json') as response:
                crumb = json.load(response)
            headers[crumb['crumbRequestField']] = crumb['crumb']
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        with request(job + 'build', data=b'', extra=headers) as response:
            queue = response.headers.get('Location', '')
        if not queue.startswith(base + 'queue/item/'):
            raise ValueError('Missing or untrusted build queue URL')
        deadline = time.monotonic() + 60
        build_url = None
        while time.monotonic() < deadline:
            with request((build_url or queue).rstrip('/') + '/api/json') as response:
                result = json.load(response)
            if build_url and not result.get('building', True):
                return dict(status='SUCCESS' if result.get('result') == 'SUCCESS' else 'FAILED',
                            build_url=build_url, build_number=result.get('number'), result=result.get('result'),
                            detail='Exact smoke job result; console available at build URL')
            if result.get('cancelled'):
                return dict(status='FAILED', detail='Smoke job cancelled')
            if not build_url and result.get('executable'):
                build_url = result['executable']['url']
                if not build_url.startswith(job):
                    raise ValueError('Unexpected Jenkins build URL')
            time.sleep(2)
        return dict(status='NOT_VERIFIED', detail='Smoke polling timed out; job may still be queued/running; inspect Jenkins before retry')
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        # Never include response bodies, credentials or arbitrary URL errors in logs.
        return dict(status='FAILED', detail='Jenkins smoke request failed: ' + type(exc).__name__)

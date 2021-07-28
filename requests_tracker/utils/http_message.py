"""
requests_tracker.utils.http_message
===================================
"""
from django.template.loader import get_template
from six.moves.urllib import parse


def render_request_message(prepared_request):
    try:
        tmpl = get_template('requests_tracker/request.tmpl')
        context = {
            'prep': prepared_request,
            'host': parse.urlsplit(prepared_request.url).netloc,
        }
        return tmpl.render(context)
    except Exception as e:
        return str(e)


def render_response_message(response):
    try:
        tmpl = get_template('requests_tracker/response.tmpl')
        context = {'response': response}
        return tmpl.render(context)
    except Exception:
        return response.text if response else ""

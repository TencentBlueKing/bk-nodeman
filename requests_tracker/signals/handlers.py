"""
requests_tracker.signals.handlers
=================================
"""
import logging

from six.moves.urllib import parse

from requests_tracker import states
from requests_tracker.models import Record
from requests_tracker.utils import http_message

logger = logging.getLogger(__name__)

# python3 & python2
urlsplit, urlunsplit = parse.urlsplit, parse.urlunsplit


def pre_send_handler(sender, uid, prep, api_uid, operator, **kwargs):
    """handle `requests_tracker.signals.pre_send` signal"""

    setattr(prep, "api_uid", api_uid)
    logger.info(f"[request_tracker] {prep.url}")
    # if filters.rt_filter(prep, use_cache=False):
    # 由于 rt_filter 中 cache.set 会导致 DB 死锁，这里暂时不进行过滤，待排查
    rt_kwargs = {
        "uid": uid,
        "api_uid": api_uid or "",
        "operator": operator or "",
        "method": prep.method,
        "request_message": http_message.render_request_message(prep),
    }

    _ = urlsplit(prep.url)
    rt_kwargs.update({"url": urlunsplit((_.scheme, _.netloc, _.path, "", ""))})

    record = Record(**rt_kwargs)
    try:
        record.save()
    except Exception as e:
        logger.warning("save record error: %s" % str(e))
        return
    record.transit(states.IN_PROGRESS)


def response_handler(sender, uid, resp, duration, **kwargs):
    """handle `requests_tracker.signals.response` signal"""

    try:
        record = Record.objects.get(uid=uid)
    except Record.DoesNotExist:
        logger.info("uid does not exist: %r" % uid)
    except Exception as e:
        logger.info(f"table does not exist, {e}")
    else:
        if record.api_uid in ["DOWNLOAD_FILE"]:
            response_message = ""
        else:
            response_message = http_message.render_response_message(resp)[0 : 2048 * 8]

        rt_kwargs = {
            "status_code": resp.status_code,
            "response_message": response_message,
            "remark": resp.reason,
            "duration": duration,
            "request_host": resp.raw._original_response.peer,
        }
        record.transit(states.SUCCESS, **rt_kwargs)


def request_failed_handler(sender, uid, exception, duration, **kwargs):
    """handle `requests_tracker.signals.request_failed` signal"""

    try:
        record = Record.objects.get(uid=uid)
    except Record.DoesNotExist:
        logger.info("uid does not exist: %r" % uid)
    except Exception as e:
        logger.info(f"table does not exist, {e}")
    else:
        rt_kwargs = {
            "duration": duration,
            "remark": exception.__class__.__name__,
            "response_message": exception,
        }
        record.transit(states.FAILURE, **rt_kwargs)

    raise exception

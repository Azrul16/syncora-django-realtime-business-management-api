import logging


class RequestLogDefaultsFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, 'request_id', '')
        record.user_id = getattr(record, 'user_id', '')
        record.status_code = getattr(record, 'status_code', '')
        record.duration_ms = getattr(record, 'duration_ms', '')
        return True

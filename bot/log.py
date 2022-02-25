import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
format_string = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
ch.setFormatter(format_string)
log.addHandler(ch)

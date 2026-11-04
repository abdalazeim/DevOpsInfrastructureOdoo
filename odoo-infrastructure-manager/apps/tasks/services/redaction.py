import re


_SECRET_PAIR = re.compile(
    r'''(?i)(["']?(?:password|passwd|token|secret|api[_-]?key|authorization|private[_-]?key)["']?\s*[:=]\s*["']?)([^\s,"';}]+)'''
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)


def redact_output(value, *, max_length=8192):
    text = str(value or "")[:max_length]
    text = _PRIVATE_KEY.sub("[REDACTED PRIVATE KEY]", text)
    text = _SECRET_PAIR.sub(r"\1[REDACTED]", text)
    return _BEARER.sub("Bearer [REDACTED]", text)

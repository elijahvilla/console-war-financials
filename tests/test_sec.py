import pytest

from cwf.sec import ConfigError, SecClient

UA = "Test Person tester@example.org"


class FakeResp:
    def __init__(self, status, body=b"{}"):
        self.status_code, self.content = status, body


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        return self.responses.pop(0)


class Clock:
    def __init__(self):
        self.t, self.sleeps = 100.0, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def make(tmp_path, responses, clock=None):
    clock = clock or Clock()
    s = FakeSession(responses)
    c = SecClient(user_agent=UA, cache_dir=tmp_path, session=s, clock=clock.now, sleep=clock.sleep)
    return c, s, clock


def test_missing_user_agent_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(ConfigError, match="SEC_USER_AGENT"):
        SecClient(cache_dir=tmp_path, load_env=False)


def test_user_agent_header_sent_but_not_cached(tmp_path):
    c, s, _ = make(tmp_path, [FakeResp(200, b'{"a": 1}')])
    assert c.get_json("https://data.sec.gov/x.json") == {"a": 1}
    assert s.calls[0][1]["User-Agent"] == UA
    for f in tmp_path.rglob("*"):
        if f.is_file():
            assert UA.encode() not in f.read_bytes()


def test_cache_hit_skips_network(tmp_path):
    c, s, _ = make(tmp_path, [FakeResp(200, b"body")])
    assert c.get("https://www.sec.gov/a") == b"body"
    assert c.get("https://www.sec.gov/a") == b"body"
    assert len(s.calls) == 1


def test_throttle_spaces_requests(tmp_path):
    c, s, clock = make(tmp_path, [FakeResp(200, b"1"), FakeResp(200, b"2")])
    c.get("https://www.sec.gov/1")
    c.get("https://www.sec.gov/2")
    assert any(x >= 0.2 - 1e-9 for x in clock.sleeps)


def test_retries_on_429_then_succeeds(tmp_path):
    c, s, clock = make(tmp_path, [FakeResp(429), FakeResp(503), FakeResp(200, b"ok")])
    assert c.get("https://www.sec.gov/r") == b"ok"
    assert len(s.calls) == 3


def test_gives_up_after_retries(tmp_path):
    from cwf.sec import SecError
    c, s, _ = make(tmp_path, [FakeResp(429)] * 4)
    with pytest.raises(SecError):
        c.get("https://www.sec.gov/r")
    assert len(s.calls) == 4

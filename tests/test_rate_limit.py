from server.rate_limit import RateLimiter, TokenBucket


class FakeClock:
    """A controllable clock, so a token bucket can be tested without a real
    time.sleep - each call to it returns whatever time was last set."""

    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now


def test_a_fresh_bucket_allows_up_to_its_capacity():
    clock = FakeClock()
    bucket = TokenBucket(capacity=3, refill_per_second=1, clock=clock)
    assert [bucket.allow() for _ in range(3)] == [True, True, True]
    assert bucket.allow() is False  # the 4th, with no time having passed


def test_tokens_refill_over_time():
    clock = FakeClock()
    bucket = TokenBucket(capacity=1, refill_per_second=1, clock=clock)
    assert bucket.allow() is True
    assert bucket.allow() is False   # empty
    clock.now += 1.0                 # a full second passes
    assert bucket.allow() is True    # refilled exactly one token


def test_refill_never_exceeds_capacity():
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_per_second=100, clock=clock)
    clock.now += 10  # would refill far past capacity if unbounded
    assert [bucket.allow() for _ in range(3)] == [True, True, False]


def test_different_keys_in_a_rate_limiter_do_not_share_a_bucket():
    clock = FakeClock()
    limiter = RateLimiter(capacity=1, refill_per_second=1, clock=clock)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False  # "a" is out
    assert limiter.allow("b") is True   # "b" has its own bucket


def test_the_same_key_reuses_its_bucket_across_calls():
    clock = FakeClock()
    limiter = RateLimiter(capacity=2, refill_per_second=1, clock=clock)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False

# -*- coding: utf-8 -*-

import time
import traceback
import signal
from multiprocessing.managers import SyncManager
import pickle
import datetime


class NS:

    def __init__(self):
        mgr = SyncManager()
        mgr.start(signal.signal, (signal.SIGINT, signal.SIG_IGN))
        self.ns_default = mgr.Namespace()
        self.ns_default.error = None
        self.ns_stats = mgr.Namespace()
        self.input_queue = mgr.Queue(maxsize=100)
        self.error_occurred = mgr.Event()
        self.error_processed = mgr.Event()
        self.batch_done = mgr.Event()
        self.mgr = mgr
        self.stats_lock = mgr.Lock()
        self.main_lock = mgr.Lock()

    def set_shared_value(self, name, value, no_lock=False):
        if no_lock:
            setattr(self.ns_default, name, value)
            return
        with self.main_lock:
            setattr(self.ns_default, name, value)

    def get_shared_value(self, name, no_lock=False):
        if no_lock:
            return getattr(self.ns_default, name)
        with self.main_lock:
            return getattr(self.ns_default, name)


ns_container = NS()


class Stats:

    stats = ns_container.ns_stats
    start_time = datetime.datetime.utcnow()
    _lock = ns_container.stats_lock
    _locked = False

    @classmethod
    def time_spent(cls):
        return datetime.datetime.utcnow() - cls.start_time

    @classmethod
    def lock(cls):
        cls._lock.acquire()
        cls._locked = True

    @classmethod
    def unlock(cls):
        cls._lock.release()
        cls._locked = False

    @classmethod
    def set_stats_val(cls, name, value):
        cls.lock()
        cls.add_key(name)
        setattr(cls.stats, name, value)
        cls.unlock()
        return value

    @classmethod
    def inc_stats_val(cls, name, value=1):
        cls.lock()
        cls.add_key(name)
        if not hasattr(cls.stats, name):
            setattr(cls.stats, name, 0)
        setattr(cls.stats, name, getattr(cls.stats, name) + value)
        cls.unlock()
        return getattr(cls.stats, name)

    @classmethod
    def get_stats_val(cls, name, default=None):
        cls.lock()
        value = getattr(cls.stats, name, default)
        cls.unlock()
        return value

    @classmethod
    def inc_stats_vals(cls, vals, return_stats=False, **kwargs):
        cls.lock()
        for name, value in vals.items():
            cls.add_key(name)
            if not hasattr(cls.stats, name):
                setattr(cls.stats, name, 0)
            setattr(cls.stats, name, getattr(cls.stats, name) + value)
        if return_stats:
            stats = cls.get_stats(**kwargs)
        cls.unlock()
        if return_stats:
            return stats

    @classmethod
    def get_stats(cls, ignore_keys=(), **kwargs):
        keys = (k for k in cls.stat_keys() if k not in ignore_keys)
        return {k: getattr(cls.stats, k, None) for k in keys}

    @classmethod
    def add_key(cls, name):
        stat_keys = getattr(cls.stats, 'stat_keys', set())
        stat_keys.add(name)
        cls.stats.stat_keys = stat_keys

    @classmethod
    def stat_keys(cls):
        return getattr(cls.stats, 'stat_keys', set())

    @classmethod
    def time_spent(cls):
        return str(datetime.datetime.utcnow() - cls.start_time)


class ExitStatus:
    _listeners = set()
    seconds = 0
    time_start = time.time()

    def __init__(self, message='Success', code=0, target=None, **kwargs):
        self.time_start = kwargs.get('time_start') or self.time_start
        if traceback.sys.exc_info()[0]:
            message = traceback.format_exc()
            code = code or 1

        self.code = code
        self.message = message
        self.target_error = target

    @property
    def seconds(self):
        time_now = time.time()
        return time_now - self.time_start

    def __repr__(self):
        data = 'Finished with code {c} in {s} with message: [{m}]'.format(
            c=self.code,
            s=self.seconds,
            m=self.message
        )
        if self.target_error:
            data += '\nError target: {}'.format(self.target_error)
        return data

    def __iter__(self):
        for f in ['code', 'seconds', 'message', 'target_error']:
            val = getattr(self, f, None)
            if val is not None:
                yield f, val

    def get_error(self):
        if self.target_error:
            return f'target: {self.target_error}\nmessage: {self.message}'

    @classmethod
    def get_status(cls, wait=True):
        if ns_container.error_occurred.is_set():
            wait and ns_container.error_processed.wait()
            result = ns_container.ns_default.error
            status = pickle.loads(result) if isinstance(
                result,
                bytes) else result
        else:
            status = ExitStatus()
        for l in cls._listeners:
            l(status)
        return status

    @classmethod
    def add_exit_listener(cls, listener):
        cls._listeners.add(listener)


def handle_exception_occurred(**kwargs):
    if ns_container.error_processed.is_set():
        return
    result = ExitStatus(**kwargs)
    print(result.message)
    ns_container.ns_default.error = pickle.dumps(result)
    ns_container.error_occurred.set()


def _sigint_default(_signal, frame):
    handle_exception_occurred(code=_signal, message='Keyboard interrupt')


signal.signal(signal.SIGINT, _sigint_default)

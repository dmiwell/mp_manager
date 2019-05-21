# -*- coding: utf-8 -*-

import logging
import multiprocessing
from threading import Thread
import inspect
import pickle

from mp_manager.base_handler import BaseHandler
from mp_manager.process_helpers import ExitStatus, ns_container, \
    handle_exception_occurred, Stats


class ItemWorker(multiprocessing.Process):

    def __init__(self, import_handler: BaseHandler, worker_number: int):
        self.worker_number = worker_number
        self.logger = logging.getLogger(self.worker_name)
        self.handler = import_handler(worker_number, self.logger)
        self.input_queue = ns_container.input_queue
        self.batch_done = ns_container.batch_done
        super(multiprocessing.Process, self).__init__()

    def run(self):
        try:
            while not ns_container.error_occurred.is_set():
                data = self._get_item_to_handle()
                if data == 'STOP':
                    break
                else:
                    self._handle(data)
            self.logger.info('Finishing %s', self.worker_name)
        except:
            handle_exception_occurred()
        else:
            self.batch_done.set()

    @property
    def worker_name(self):
        return 'worker-%s' % self.worker_number

    def _handle(self, item):
        try:
            # Starting point to process the item in handler
            self.handler.handle(item)
        except:
            handle_exception_occurred(target=self.handler.log_item)
        else:
            self.batch_done.set()
            self.logger.info('batch_done. item: %s time spent: %s',
                             self.handler.log_item,
                             Stats.time_spent())

    def _get_item_to_handle(self):
        try:
            return self.input_queue.get()
        except StopIteration:
            return 'STOP'


class ImportManager:

    processes = []
    import_handler = BaseHandler

    def __init__(self, import_handler: BaseHandler, *args, **kwargs):
        self.num_workers = kwargs.get('num_workers', 1)
        self.import_handler = import_handler
        self.logger = logging.getLogger(
            inspect.getmodule(self.__class__).__name__)
        self.input_queue = ns_container.input_queue
        assert self.import_handler != BaseHandler

    def run(self) -> ExitStatus:
        """
        Run import
        """
        try:
            self._run()
        except:
            if not ns_container.ns_default.error:
                handle_exception_occurred()
        return ExitStatus.get_status()

    def _run(self):
        error_listener = Thread(
            target=self._error_listener,
            name='error_listener',
            daemon=True,
            args=[]
        )
        error_listener.start()

        manager_wait = Thread(
            target=ns_container.mgr.join,
            daemon=True
        )
        manager_wait.start()

        for n in range(0, self.num_workers):
            p = ItemWorker(self.import_handler, n)
            p.start()
            self.processes.append(p)
            ns_container.batch_done.clear()

        self._feed_queue()

        for _ in self.processes:
            if not ns_container.error_occurred.is_set():
                ns_container.input_queue.put('STOP')

        ns_container.error_occurred.is_set() and \
            ns_container.error_processed.wait()

        for p in self.processes:
            p.join()

    def _error_listener(self):
        ns_container.error_occurred.wait()
        error = pickle.loads(ns_container.ns_default.error)
        self.logger.error('Got [%s] stopping all import processes...',
                          error.message)
        for _ in range(0, ns_container.input_queue.qsize()):
            try:
                ns_container.input_queue.get_nowait()
            except:
                pass
        ns_container.batch_done.set()
        ns_container.error_processed.set()

    def _feed_queue(self):
        for h in self.import_handler.build_items():
            if not ns_container.error_occurred.is_set():
                self.input_queue.put(h)
            else:
                break

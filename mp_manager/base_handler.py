# -*- coding: utf-8 -*-

from typing import Any


class BaseHandler:

    current_item = None
    stats = {}

    def __init__(self, worker_num: int, logger):
        self.worker_num = worker_num
        self.logger = logger

    @classmethod
    def build_items(cls, *args, **kwargs):
        """
        Build items to be input to handle(item)

        :param kwargs:
        :return:
        """
        pass

    @property
    def log_item(self):
        return self.current_item

    def handle(self, item: Any):
        """
        Handle the item from multiprocess manager
        :param item:
        :return:
        """
        self.current_item = item
        self._reset_stats()
        self._handle_item()

    def _handle_item(self):
        """
        Actual handling of current item
        """
        print(self.current_item)
        raise NotImplementedError

    def _reset_stats(self):
        """
        Reset stats related to processing current item
        """
        self.stats = {}

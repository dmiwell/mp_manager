# Simple multiprocessing management tool
Handles big amounts of data using python multiprocessing

## Concept
The main idea is to utilize multiprocessing, by building source queue and handle items to process in workers. 

Multiprocess managing is implemented using `mp_manager.manager.py` with help of `mp_manager.process_helpers.py` that provides events, locks, shared values and stats, exception handler helper and `ExitStatus`

Workers for multiprocessing are built based on handlers classes.

### Handlers
Handlers must inherit `mp_manager.base_handler.BaseHandler` and at least implement:
1) classmethod `build_items()` that must return iterable of items to handle by workers
2) `_handle_item()` which is used to handle current item

They also could implement:
1) `log_item()` that is used by manager as a source for logging
2) `_reset_stats()` is used internally to reset worker dict stats related to current item

### Sample usage
```python
import math
import random
import time

from mp_manager.base_handler import BaseHandler
from mp_manager.process_helpers import Stats, ns_container
from mp_manager.utils import build_batches


class SampleHandler(BaseHandler):

    batch_size = 2

    @classmethod
    def build_items(cls, *args, **kwargs):
        total = 100
        batches_total = int(math.ceil(total / cls.batch_size))

        Stats.set_stats_val('items_total', total)
        Stats.set_stats_val('batches_total', batches_total)
        ns_container.set_shared_value('shared_data', cls._data_to_share(),
                                      True)
        for i, val in enumerate(build_batches(range(total), cls.batch_size)):
            yield i, val

    @property
    def log_item(self):
        return f'{self.current_item[0]} / {Stats.stats.batches_total}'

    @classmethod
    def _data_to_share(cls):
        return dict(somekey="some value")

    def _reset_stats(self):
        self.stats = {
            'items_processed': 0,
            'items_positive': 0,
            'items_negative': 0,
        }

    def _handle_item(self):
        num, items = self.current_item
        for item in items:
            self._process_number(item)
        Stats.inc_stats_vals(self.stats)
        self.logger.info(Stats.get_stats())

    def _process_number(self, item):
        time.sleep(random.random())
        value = math.factorial(item) / math.cos(item)
        self.stats['items_processed'] += 1
        if value > 0:
            self.stats['items_positive'] += 1
        else:
            self.stats['items_negative'] += 1


if __name__ == '__main__':
    import logging
    from mp_manager.manager import ImportManager

    logging.basicConfig(level=logging.DEBUG)
    status = ImportManager(SampleHandler, num_workers=8).run()

    print(status)
    exit(status.code)
```
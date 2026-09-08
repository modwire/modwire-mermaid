from functools import cache

from wireup import ScopedSyncContainer, SyncContainer, create_sync_container

import mermaiden


def _create_container() -> SyncContainer:
    return create_sync_container(injectables=[mermaiden], config={})


@cache
def process_scope() -> ScopedSyncContainer:
    scope = _create_container().enter_scope()
    scope.__enter__()
    return scope

from wireup import SyncContainer, create_sync_container

import mermaiden


def create_container() -> SyncContainer:
    return create_sync_container(injectables=[mermaiden], config={})

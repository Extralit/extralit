from typing import Optional, List, Union
from uuid import UUID, uuid4
from unittest.mock import MagicMock

from extralit.client import Extralit
from extralit.workspaces import Workspace
from extralit.users import User
from extralit.datasets import Dataset
from extralit._models import WorkspaceModel, UserModel, DatasetModel

class MockClient(Extralit):
    def __init__(self):
        self.api = MagicMock()
        self.api.workspaces = MagicMock()
        self.api.users = MagicMock()
        self.api.datasets = MagicMock()
        self._workspaces_storage = []
        self._users_storage = []
        self._datasets_storage = []

    def add_workspace(self, workspace: Workspace):
        self._workspaces_storage.append(workspace._model)
        self.api.workspaces.list.return_value = self._workspaces_storage
        # Setup get behavior
        self.api.workspaces.get.side_effect = self._get_workspace_by_id

    def add_user(self, user: User):
        self._users_storage.append(user._model)
        self.api.users.list.return_value = self._users_storage
        self.api.users.get.side_effect = self._get_user_by_id

    def add_dataset(self, dataset: Dataset):
        self._datasets_storage.append(dataset._model)
        self.api.datasets.list.return_value = self._datasets_storage
        self.api.datasets.get.side_effect = self._get_dataset_by_id

    def _get_workspace_by_id(self, id):
        for w in self._workspaces_storage:
            if str(w.id) == str(id):
                return w
        from extralit._exceptions import NotFoundError
        raise NotFoundError()

    def _get_user_by_id(self, id):
        for u in self._users_storage:
            if str(u.id) == str(id):
                return u
        from extralit._exceptions import NotFoundError
        raise NotFoundError()

    def _get_dataset_by_id(self, id):
        for d in self._datasets_storage:
            if str(d.id) == str(id):
                return d
        from extralit._exceptions import NotFoundError
        raise NotFoundError()

from extralit import Dataset, Extralit, Settings, TaskDistribution, TextField, TextQuestion, Workspace


class TestDatasetsList:
    def test_list_datasets(self, client: Extralit):
        workspace = Workspace(name="test-workspace", client=client)
        workspace.create()

        dataset = Dataset(
            name="test_dataset",
            workspace=workspace.name,
            settings=Settings(fields=[TextField(name="text")], questions=[TextQuestion(name="text_question")]),
            client=client,
        )
        dataset.create()
        datasets = client.datasets
        assert len(datasets) > 0, "No datasets were found"

        for ds in datasets:
            if ds.name == "test_dataset":
                assert ds == dataset, "The dataset was not loaded properly"

    def test_list_dataset_with_custom_task_distribution(self, client: Extralit, workspace: Workspace):
        dataset = Dataset(
            name="test_dataset",
            workspace=workspace.name,
            settings=Settings(
                fields=[TextField(name="text")],
                questions=[TextQuestion(name="text_question")],
                distribution=TaskDistribution(min_submitted=4),
            ),
            client=client,
        )
        dataset.create()
        datasets = client.datasets
        assert len(datasets) > 0, "No datasets were found"

        dataset_idx = 0
        for idx, ds in enumerate(datasets):
            if ds.id == dataset.id:
                dataset_idx = idx
                assert ds.settings.distribution.min_submitted == 4, "The dataset was not loaded properly"
                break

        ds = client.datasets[dataset_idx]
        assert ds.settings.distribution.min_submitted == 4, "The dataset was not loaded properly"

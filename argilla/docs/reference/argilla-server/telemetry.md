# Server Telemetry

Argilla uses telemetry to report anonymous usage and error information. As an open-source software, this type of information is important to improve and understand how the product is used. This is done through the [Hugging Face Hub library](https://github.com/huggingface/huggingface_hub) telemetry implementations.

## How to opt-out

You can opt out of telemetry reporting using the `ENV` variable `HF_HUB_DISABLE_TELEMETRY` before launching the server. Setting this variable to `1` will completely disable telemetry reporting.

If you are a Linux/MacOs user, you should run:

```bash
export HF_HUB_DISABLE_TELEMETRY=1
```

If you are a Windows user, you should run:

```bash
set HF_HUB_DISABLE_TELEMETRY=1
```

To opt in again, you can set the variable to `0`.

## Why reporting telemetry

Anonymous telemetry information enables us to continuously improve the product and detect recurring problems to better serve all users. We collect aggregated information about general usage and errors. We do NOT collect any information on users' data records, datasets, or metadata information.

## Sensitive data

We do not collect any piece of information related to the source data you store in Argilla. We don't identify individual users. Your data does not leave your server at any time:

* No dataset record is collected.
* No dataset names or metadata are collected.

## Information reported

The following usage and error information is reported:

* The code of the raised error
* The `user-agent` and `accept-language` http headers
* Task name and number of records for bulk operations
* An anonymous generated user uuid
* An anonymous generated server uuid
* The Argilla version running the server
* The Python version, e.g. `3.8.13`
* The system/OS name, such as `Linux`, `Darwin`, `Windows`
* The system’s release version, e.g. `Darwin Kernel Version 21.5.0: Tue Apr 26 21:08:22 PDT 2022; root:xnu-8020`
* The machine type, e.g. `AMD64`
* The underlying platform spec with as much useful information as possible. (eg. `macOS-10.16-x86_64-i386-64bit`)
* The type of deployment: `huggingface_space` or `server`
* The dockerized deployment flag: `True` or `False`

For transparency, you can inspect the source code where this is performed [here](https://github.com/extralit/extralit/argilla-server/src/argilla_server/telemetry.py).



# INGV pygeoapi process plugins

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18892819.svg)](https://doi.org/10.5281/zenodo.18892819)

Plugins for extending **pygeoapi** with processing services developed at **INGV**.

This repository contains a collection of plugins that allow exposing processing services through **pygeoapi**, compliant with the **OGC API - Processes** standard.

---
## Overview

[pygeoapi](https://pygeoapi.io/) is a Python server framework that implements several **OGC API** standards.
In particular, it supports the [OGC API - Processes](https://ogcapi.ogc.org/processes/) standard to expose processing services through standard APIs.

Through the plugins contained in this repository it is possible to integrate new processing workflows within a pygeoapi instance.

These plugins allow exposing processing services developed at INGV through standard API interfaces, making the processes accessible via HTTP requests.

## Solution architecture

The complete solution is composed of three distinct software layers.

### 1. pygeoapi

The **pygeoapi** framework exposes processes through APIs compliant with the
**OGC API - Processes** standard.

### 2. pygeoapi plugins

The repository https://github.com/francescoingv/ingv-pygeoapi-process-plugins
contains the plugins that implement pygeoapi processes.
The plugins receive execution requests and forward them to an
external processing service responsible for executing the code.

### 3. Execution service

The repository

https://github.com/francescoingv/generic-processor-provider

implements the execution service for the application codes.
The service receives HTTP requests from the plugins and invokes
the configured scientific codes through command-line execution.

### 4. Processing codes

The scientific processing codes used for computation are not part
of the repositories listed above.

They are invoked by the execution service through the `command_line`
parameter defined in the `application.ini` configuration file.

Current deployments of the platform expose processes associated
with the following codes:

- **solwcad**
- **conduit**
- **pybox**

These codes are executed through the external execution service.

---

### Logical solution schema

```text
Client
  │
  ▼
pygeoapi
  │
  ▼
pygeoapi plugins
  │
  ▼
generic-processor-provider
  │
  ▼
scientific processing code
```

---
## Requirements

To use the plugins the following software must be installed:

- Python >= 3.12
- pygeoapi

Using a Python virtual environment is recommended.

Installing pygeoapi includes all runtime dependencies
(see the `requirements*.txt` files of the framework).

---
## Installation

Clone the repository:

git clone https://github.com/francescoingv/ingv-pygeoapi-process-plugins.git

Enter the project directory:

cd ingv-pygeoapi-process-plugins

Install the package:

pip install .

Alternatively, for development:

pip install -e .

---
## Usage

To use the plugins they must be registered in the **pygeoapi** configuration.

An example configuration is available in the file:

example-config.yml

Within the pygeoapi configuration file a process can be added by defining the corresponding Python plugin.

Simplified example:

```yaml
processes:
  example-process:
    type: process
    processor:
      name: ingv_plugin_pygeoapi.process.example_process
```

After configuring the process the OpenAPI configuration file must be generated, for example:

```
pygeoapi openapi generate example-config.yml --output-file example-openapi.yml
```

pygeoapi will automatically expose the corresponding API endpoint.

---
## Plugin architecture

### Base plugin: BaseRemoteExecutionProcessor

The base plugin:

- receives and manages the execution request
- forwards the execution request to an **external processing service** used by pygeoapi

### Specific plugins

Each plugin derived from `BaseRemoteExecutionProcessor` is specific for a given code:

- contains metadata describing how the service should be used
- validates input parameters
- returns the result in the format expected by pygeoapi

## External processing service

A design choice was made **not to execute processing code on the same server** running pygeoapi, allowing full independence between the execution environments of different plugins, particularly regarding the libraries required by each code.

Each plugin calls a processing service hosted at a specific URL; therefore, a dedicated server is assumed for each processing code.

### Directory and job management

Each processing request is managed as a job identified by a UUID.

Each plugin is associated with a directory (defined in the plugin configuration via `private_processor_dir`), under which a specific directory is created for each job, identified by the unique job identifier (UUID - Universally Unique Identifier).

The plugin can read and write files within the job directory while processing.

If the **external processing service** uses input files or returns output files:

- if the service has access to the plugin directory (shared directory), plugin and service can exchange files through it;
- otherwise, file contents must be transferred through the request/response body.

The exchange of information between the plugin and the service is implemented specifically within each plugin.

---
## External processing service interface

The external processing service must respond to the following request:

```text
POST /execute
```

The request `Content-Type` can be:

- `text/plain`
- `application/json`

The request body must contain a **JSON object** with the following fields:

```json
{
  "code_input_params": {
    "parameter_key": "parameter_value"
  },
  "application_params": {
    "job_id": "UUID",
    "synch_execution": true
  }
}
```

### Parameters

#### `code_input_params`

Dictionary containing `<parameter_key : parameter_value>` pairs.

Values can be:

- strings
- numbers
- booleans
- lists

#### `application_params`

Dictionary with the following keys:

- `job_id`
  Job identifier (UUID)

- `synch_execution`
  Optional, boolean, default `true`; indicates whether the request must
  be executed synchronously

---

```text
GET /job_info/<string:job_id>
```

Returns a JSON object containing job execution information.

---
## Docker usage

The plugin can be used inside a Docker container running pygeoapi.

In that case the following structure must be created:

```text
./
├── Dockerfile
├── my.pygeoapi.config.yml
└── ingv_plugin/
    ├── pyproject.toml
    ├── setup.py
    └── ingv_plugin_pygeoapi/
        ├── __init__.py
        └── process/
            ├── base_remote_execution.py
            ├── conduit.py
            ├── solwcad.py
            ├── pybox.py
            └── ...
```

The repository includes a Docker configuration that allows running the processing service in a container environment.

---
## Environment variables

Environment variables are referenced in the configuration file using placeholders of the form `$VARIABLE$`.

During deployment these placeholders must be replaced with the actual environment variable values.

---
## Related software

This repository is part of the **INGV pygeoapi processing platform**:

https://github.com/francescoingv/ingv-pygeoapi-processing-platform  
Platform DOI: https://doi.org/10.5281/zenodo.18892848

The execution service for application codes is implemented in the repository:

https://github.com/francescoingv/generic-processor-provider  
DOI: https://doi.org/10.5281/zenodo.18892842

This service receives HTTP requests from the pygeoapi plugins and executes
the configured application codes.

---
## Citation

If you use this software in scientific work, please cite it as:

Martinelli, F. (2026).  
*INGV pygeoapi process plugins*.  
DOI: https://doi.org/10.5281/zenodo.18892819

## License

This project is distributed under the **MIT License**.

See the `LICENSE` file for details.

## Authors

Francesco Martinelli  
Istituto Nazionale di Geofisica e Vulcanologia (INGV)  
Pisa, Italy

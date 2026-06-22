# EXPOSE plugins

Plugin per estendere **pygeoapi** con processi di elaborazione sviluppati all'interno del progetto **EXPOSE**.

Questo repository contiene una collezione di plugin che permettono di esporre tramite **pygeoapi** servizi di elaborazione compatibili con lo standard **OGC API - Processes**.

---
## Overview

[pygeoapi](https://pygeoapi.io/) è un server framework Python che implementa diversi standard **OGC API**.
In particolare supporta lo standard [OGC API - Processes](https://ogcapi.ogc.org/processes/) per offrire servizi di elaborazione tramite API standard.

Attraverso i plugin presenti in questo repository è possibile integrare nuovi processi di elaborazione all'interno di un'istanza pygeoapi.

I plugin permettono di esporre servizi di processing tramite interfacce API standard, rendendo i processi accessibili tramite richieste HTTP.

## Architettura della soluzione

La soluzione completa è composta da tre livelli software distinti.

### 1. pygeoapi

Il framework **pygeoapi** espone i processi tramite API conformi allo
standard **OGC API - Processes**.

### 2. Plugin pygeoapi

Il repository https://github.com/francescoingv/expose-pygeoapi-plugins
contiene i plugin che implementano i processi pygeoapi.
I plugin ricevono le richieste di esecuzione e le inoltrano a un
servizio di elaborazione esterno responsabile dell'esecuzione del codice.

### 3. Servizio di esecuzione

Il repository

https://github.com/francescoingv/generic-processor-provider

implementa il servizio di esecuzione dei codici applicativi.
Il servizio riceve richieste HTTP dai plugin e invoca i codici
applicativi configurati tramite riga di comando.

### 4. Codici di elaborazione

I codici scientifici utilizzati per l'elaborazione non fanno parte
dei repository sopra indicati.

Essi vengono invocati dal servizio di esecuzione tramite il parametro
`command_line` definito nel file di configurazione `application.ini`.

---

### Schema logico della soluzione

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
codice scientifico
```

---
## Requirements

Per utilizzare i plugin è necessario avere installato:

- Python >= 3.12
- pygeoapi

È consigliato utilizzare un ambiente virtuale Python.

L’installazione di pygeoapi include tutte le librerie necessarie al runtime
(con riferimento ai file `requirements*.txt` del framework).

---
## Installation

Clonare il repository:

git clone https://github.com/francescoingv/expose-pygeoapi-plugins.git

Entrare nella directory del progetto:

cd expose-pygeoapi-plugins

Installare il pacchetto:

pip install .

In alternativa, per sviluppo:

pip install -e .

---
## Usage

Per utilizzare i plugin è necessario registrarli nella configurazione di **pygeoapi**.

Un esempio di configurazione è disponibile nel file:

example-config.yml

Nel file di configurazione di pygeoapi è possibile aggiungere un processo definendo il plugin Python corrispondente.

Esempio semplificato:
```yaml
processes:
  example-process:
    type: process
    processor:
      name: expose-plugins.process.example_process
```

Dopo aver configurato il processo deve essere generato il file di configurazione OpenAPI, ad esempio:

```
pygeoapi openapi generate example-config.yml --output-file example-openapi.yml
```

pygeoapi esporrà automaticamente l'endpoint API relativo.

---
## Plugin architecture

### Plugin base: BaseRemoteExecutionProcessor

Il plugin base:
- riceve e gestisce la richiesta di esecuzione
- inoltra la richiesta di esecuzione ad un **servizio di elaborazione esterno** a pygeoapi

### Plugin specifici
Ciascun plugin derivato da BaseRemoteExecutionProcessor è specifico per un codice:
- contiene la definizione dei metadati per l’utilizzo del servizio
- valida i parametri di input
- restituisce il risultato nel formato previsto da pygeoapi

## Servizio di elaborazione esterno

È stata fatta la scelta di **non eseguire l’elaborazione del codice sullo stesso server** su cui è in esecuzione pygeoapi, per permettere la completa indipendenza tra l’ambiente di esecuzione di plugin differenti, in particolare per quanto riguarda le librerie utilizzate da ciascun codice.

Ciascun plugin richiede un servizio di elaborazione su un URL specifico; si ipotizza quindi un server dedicato per ciascun codice.

### Gestione delle directory e dei job

Ogni richiesta di elaborazione viene gestita come un job identificato da un UUID.

A ciascun plugin è associata una directory (riferita nella configurazione del plugin tramite `private_processor_dir`), al di sotto della quale viene creata una directory specifica per ciascun job, identificata dal nome univoco del job (UUID - Universally Unique Identifier).

Il plugin può leggere e scrivere file nella directory specifica del job che sta elaborando.

Nel caso in cui il **servizio di elaborazione esterno** richiesto dal plugin utilizzi file di input o restituisca file di output:
- se il servizio ha accesso alla directory del plugin (ovvero la cartella è condivisa tra il servizio ed il plugin), plugin e servizio possono utilizzare tale directory per lo scambio di file;
- se il servizio non ha accesso a tale directory, il contenuto dei file deve essere trasferito nel body/response.

La modalità di scambio di informazioni tra plugin e servizio specifico è gestita in maniera dedicata all’interno del plugin.


---
## Interfaccia del servizio di elaborazione esterno

Il servizio di elaborazione esterno deve rispondere alla seguente richiesta:

```text
POST /execute
```

Il `Content-Type` della richiesta può essere:

- `text/plain`
- `application/json`

Il body della richiesta deve contenere un **oggetto JSON** con i seguenti campi:

```json
{
  "code_input_params": {
    "chiave_parametro": "valore_parametro"
  },
  "application_params": {
    "job_id": "UUID",
    "synch_execution": true
  }
}
```

### Parametri

#### `code_input_params`

Dizionario contenente coppie `<chiave_parametro : valore_parametro>`.

I valori possono essere:
- stringhe
- numeri
- booleani
- liste

#### `application_params`

Dizionario con le seguenti chiavi:

- `job_id`  
  Identificativo del job (UUID)

- `synch_execution`  
  Opzionale, booleano, default `true`; indica se la richiesta deve essere
  eseguita in modalità sincrona

---

```text
GET /job_info/<string:job_id>
```

Restituisce un oggetto JSON con le seguenti informazioni di esempio:

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_info": {
    "received": "2026-01-20T10:00:00Z",
    "start_processing": "2026-01-20T10:01:00Z",
    "end_processing": "2026-01-20T10:02:00Z",
    "exit_code": 0,
    "std_out": "Output standard del processo",
    "std_err": ""
  },
  "params": {
    "param1": "valore1",
    "param2": 123
  }
}
```

### Parametri

#### `exit_code`

Codice di uscita dell'esecuzione (0 se è terminata senza errori)

#### `std_out`

Quello che l'esecuzione del codice ha prodotto sullo standard output

#### `std_err`

Quello che l'esecuzione del codice ha prodotto sullo standard error

#### `params`

Dizionario con i parametri che vengono passati al codice.
Ricavati principalmente da code_input_params nella richiesta POST, possono talvolta essere differenti: parametri aggiunti o modificati dal servizio.

---
## Uso con Docker

Il plugin può essere utilizzato all'interno di un container Docker
che esegue pygeoapi.

In tal caso è necessario creare la seguente struttura:

```text
./
├── Dockerfile
├── my.pygeoapi.config.yml
└── expose/
    ├── pyproject.toml
    ├── setup.py
    └── expose-plugins/
        ├── __init__.py
        └── process/
            ├── base_remote_execution.py
            ├── conduit.py
            ├── solwcad.py
            ├── pybox.py
            └── ...
```

Il repository include una configurazione Docker che permette di eseguire il servizio di elaborazione in un ambiente containerizzato.

---
## Variabili d’ambiente

Le variabili d’ambiente sono indicate nel file di configurazione tramite
placeholder della forma `$VARIABILE$`.  
Durante il deployment tali placeholder devono essere sostituiti con i valori
delle corrispondenti variabili d’ambiente.


### Server pygeoapi

- `$SERVER_NAME_geoinquire$`  
  Nome del server su cui è fornito il framework pygeoapi  
  (es. `localhost:5000`, `epos_geoinquire.pi.ingv.it`)

- `$LOCATION_epos_pygeoapi$`  
  Nome della location a cui è fornito il framework pygeoapi  
  (es. stringa vuota oppure `epos_pygeoapi`)

---

### Job Manager di pygeoapi
Si fa riferimento a PostgreSQLManager

- `$PYGEOAPI_OUTPUT_DIR$`
  directory utilizzata per scrivere i file dei risultati delle elaborazioni
  
- `$IP_ADDRESS_POSTGRES_SERVER$`
  host che fornisce PostgreSQL
  (es. 127.0.0.1)
  
- `$PORT_POSTGRES_SERVER$`
  porta utilizzata da PostgreSQL
  (es. 5433, 5432)
  
Nota: attualmente il file di configurazione non prevede variabili per user e password per l'accesso al DB, ma in un progetto non isolato è opportuno aggiungerle.
```yaml
user: ogc_api_user
password: user
```

---

### Variabili specifiche dei plugin

Nella configurazione proposta si ipotizza che ciascun plugin abbia una directory
dedicata al di sotto di una directory comune che contiene le directory di tutti
i plugin.

- `$PYGEOAPI_BASE_PRIVATE_DIRECTORY$`  
  Directory padre di tutte le directory private dei plugin  
  (es. `/custom_process_dir`)

- `$<SERVICE_ID>_SERVICE_ID$`  
  Directory specifica del servizio offerto dal plugin  
  (es. `solwcad`)

- `$<SERVICE_ID>_URL_BASE$`  
  URL del servizio specifico  
  (es. `http://127.0.0.1:5001`)

Le singole richieste di elaborazione possono richiedere ai plugin,
se i metadati del plugin lo prevedono (attributo `outputTransmission`
che può avere uno o entrambi i valori `value`, `reference`),
che ciascuno dei risultati richiesti come **output** venga restituito come:
- valore ("transmissionMode": "value")
- reference ("transmissionMode": "reference")
Nel caso di "reference", l'output contiene l'URL a cui
accedere per avere il valore.

I plugin derivati dalla classe `BaseRemoteExecutionProcessorLocalReference`
implementano la logica che i file da restituire alla richiesta di URL
vengono scritti dal plugin in una directory a cui si può accedere tramite URL.
Il server che fornisce l'accesso all'URL è esterno all'infrastruttura pygeoapi,
ma deve avere accesso alla directory in cui viene scritto il file.
Tali plugin, se abilitati a fornire risultati come `reference`
richiedono le seguenti variabili d'ambiente:

- `$LOCAL_DIR_HREF_RESULTS$`  
  Viene sostituita nel file di configurazione (`local.config.yml`,
  copiato da `my.pygeoapi.config.yml`) a `$<SERVICE_ID>_DIR_HREF_RESULTS$`.
  Directory in cui il plugin scrive i file che vengono acceduti tramite URL
  (es. `/custom_process_url/`)
  Può essere la stessa per tutti i plugin, purchè non ci siano duplicati nei nomi.
  I plugin sviluppati contengono il **job_id** come prefisso del nome, dove il
  job_id è un UUID, quindi si assume non ci possano essere duplicati.
  Attualmente si pensa di utilizzare una sola directory per tutti i plugin,
  ma è possibile differenziarle.

- `$LOCAL_URL_HREF_RESULTS$`  
  Viene sostituita nel file di configurazione (`local.config.yml`,
  copiato da `my.pygeoapi.config.yml`) a `$<SERVICE_ID>_URL_HREF_RESULTS$`.
  URL di base che rende disponibili i contenuti in `$<SERVICE_ID>_DIR_HREF_RESULTS$`
  (es. `http://process_results/myresults/`)
  Un servizio esterno a pygeoapi deve essere presente per rendere
  disponibili i file.
  Attualmente si pensa di utilizzare un solo server web per tutti i plugin,
  ma è possibile differenziarli.
  

## Related software

Questo repository fa parte di una soluzione composta da più componenti.

Il servizio di esecuzione dei codici applicativi è implementato nel repository:

https://github.com/francescoingv/generic-processor-provider

Questo servizio riceve richieste HTTP dai plugin pygeoapi ed esegue
i codici applicativi configurati tramite riga di comando.

---
## Citation

Se utilizzi questo software in un lavoro scientifico, ti preghiamo di citarlo come segue:

Martinelli, F. (2026). EXPOSE plugins.

Il DOI verrà aggiunto dopo la pubblicazione su Zenodo.

## License

Questo progetto è distribuito sotto licenza **MIT**.

Vedere il file `LICENSE` per maggiori dettagli.

## Authors

Francesco Martinelli  
Istituto Nazionale di Geofisica e Vulcanologia (INGV)  
Pisa, Italy



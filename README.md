# File upload architecture
A scalable architecture for handling file uploads from the browser using HTTP.

## High level idea
Single orchestration webserver with many worker webservers.
Programmer goes to master webserver using some known URL.
Master then dictates a worker URL and parameters for the programmer to target for HTTP Post requests.
Programmer uploads file to worker URL using specified parameters.
Worker webserver informs master that it has finished.


## Master Webserver
Programmer performs a GET to "/start_upload"; success returns a 200.
Master responds with JSON of the following shape:
```
{
    target_url: <string>,
    uuid: <string>,
    parameters: {
        chunk_size: <number in bytes>,
        ...
    }
}
```
The master webserver responds by:
* Selecting a worker using some information about current loads
* Provides UUID that must be supplied it each POST to the worker
* Specifying some parameters that must be followed by the programmer when uploading to the worker

The master webserver informs the selected worker to expect uploads to "/upload/<uuid>".
Forcing the programmer to make this request allows the master server to act as a load balancer and deal with problems if servers go down.


## Worker webserver
The programmer must make POST requests to the worker webserver adhering to the parameters dictated by the master webserver. The programmer shall upload chunks, using chunk_size from parameters, of the desired file to "/upload/<uuid>" in order; successful requests will be responded with 202. 

Once the last chunk has been successfully uploaded, the programmer will perform a GET to "/finish_upload/<uuid>"; to which the worker shall respond with 201, if successful. The worker server will notify the master that it has finished the upload associated with the specified UUID.
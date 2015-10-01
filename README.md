CIFpy3
===================

CIFpy3 is a python rewrite and adaptation of the [Collective Intelligence Framework](http://csirtgadgets.org/collective-intelligence-framework/). The python version has a number of significant performance and feature advantages over the long standing Perl version.

There are two main components: the server, and the client. The server is responsible for almost everything. The client is simply used to interact and format data using the fully RESTful API exposed by the server.

----------

Features
----------
* Powered by Python 3.4+
* Performance
  * Ingest ~70-80 Observables per second per CPU core
    * This equates to ingesting about 1M Observables in ~30 minutes using 8vCPUs
  * Less than 250MB RAM per worker process
  * Configurable workers/threads count
    * Default: (1 Worker per CPU + 30 threads per /worker)
  * Faster Installation (only a few dependencies)
* Features
  * Full REST API
  * Simple Architecture
  * Easy to read logs
  * Comprehensive documentation and code commenting
  * Cross platform compatible
* Bug Fixes
  * No longer bails out if a single feed fails
  * Handles errors better
  * Doesn't consume memory unchecked for large feeds
  * Logic bug fixes
  * Reduction in number of memory leaks (zero or near zero leaks)
  * Proper proxy usage when fetching feeds

Architecture
---------------

#### Definitions
* **observable**: A piece of unique information used to identify an item of interest (ip, domain name, hash)
* **feed**: A source containing observables to be imported
* **parser**: Parsers are responsible for parsing types of feeds (csv, rss, etc) and converting them to objects.
* **feeder**: Process that is in charge of retrieving feeds and parsing them.
* **worker**: Process used to ingest an observable, augment it with meta, and context.
* **worker plugin**: Plugins will create *new* observables related to the ingested one for purpose of context
* **worker meta**: Worker Meta adds information about an ingested observable (GeoIP, rDNS, etc)
* **rest api**: The CIF Rest API is available on HTTP port 8080.  
* **storage engine**: The final resting place for any observables created. (Elasticsearch)
* **cif-server**: The controlling daemon that runs and manages the workers, feeder, and REST API.

#### Logic
The lifecycle of an observable

1. Feed is downloaded from source using the 'feeder'.
2. Feed is then parsed using a 'parser'.
3. Parser sends the observable to a queue to be worked. 
4. Worker picks up the observable from the queue.
5. Worker first adds meta to the observable by running worker meta scripts against it
6. Worker then runs plugins against the now augmented observable. 
7. Worker then adds meta to any new observables created from the plugins
8. Worker sends observables to storage engine
9. Observable can now be searched using the rest api
10. Observable will be removed once it has not been seen for X number of days (default: 14)

Prerequisites
-------------
* A powerful and fast upstream DNS server (use a local caching instance is preferred).
  * This software can generate over 3000 DNS requests/second second when using 8 vCPUs and is processing lots of observables
* One of the following supported operating systems
  * Debian 8 (jessie) or later
  * Ubuntu 14.04 (trusty) or later


Installation
-------------
By default CIFpy3 gets installed to /opt/CIFpy3/.

> **note**: be sure to save the admin token generated during installation. You need it if you want to add any additional users or use CIFpy3 with authentication enabled or even use the API. It does get saved to ~/.cif.

```
#!/bin/bash
wget --no-check-certificate -O install.sh https://raw.githubusercontent.com/jmdevince/cifpy3/master/bin/install.sh
chmod +x install.sh
./install.sh
```

CIFpy3 will automatically install and configure a token for the cli & user that installs CIFpy3. This is the admin token. Any token flagged as an 'admin' is capable of deleting other admins.


Updating
--------
Very simple process to update cifpy3

```
#!/bin/bash
cd /opt/cifpy3
git pull
```

Then reboot your server or just restart the cif-server service.

Usage
-------
#### Configuring & Running
* Directory Layout
  * bin: Runtime files (cif, cif-server, cif-utility, install.sh)
  * cache: Cache folder for feed journals
  * etc: Contains configuration files for CIFpy3
    * feeds: This is where all feeds go. Standard YAML format is used. Feeds outside of this directory (or in subdirectories) are not loaded
  * lib: Contains the CIF runtime and GeoIP database if downloaded
  * log: Contains log files for CIFpy3 runs

#### CLI Usage
CIFpy3 comes with a CLI client called 'cif'. This client can be used to manage an entire CIF instance easily.


* Features
  * Select only fields desired. Almost any field is searchable
  * Customize output formats (csv,pipe,xml,json,delimiter)
  * Shows HTTP requests sent and received for debugging and advanced API usage

More details are available via the --help argument(> cif --help)

#### API Usage

The REST API by default is available on port 8080. It is very simple to use and returns JSON payloads for requests that return objects.

Objects are created or modified using POST parameters. For a full list of parameters and their meanings please see the object reference guide below.

> **note**: The CLI utility can generate and show the HTTP request sent if additional examples are needed


#### Example Observable Search Request
To search for an observable named 'google.com' and tagged with whitelist use the following example
```
GET /observables?observable=google.com&tags=whitelist&provider=alexa.com
Authorization: <insert token here>
```

#### Example Observable Submission
Creates an observable of 'google.com' with a provider of alexa.com and a tag of whitelist
```
PUT /observables
Authorization: <insert token here>
Content-Type: application/x-www-form-urlencoded

observable=google.com&provider=alexa.com&tags=whitelist
```



Object Reference
----------------
Bold items are required. Italicised are only required when modifying objects.

Most of these are automatically filled in using Worker meta and plugins after the observable is submitted.

#### Observable
* *id*: Unique 64 byte hex ID (optional for new objects)
* lang: Two character language type (optional)
* group: One or more groups the observable can belong to, default: everyone (optional)
* tlp: Traffic Light Protocol attribute. Can be one of 'white', 'green', 'yellow', 'red'.
* confidence: An integer or float of the observables confidence level. Higher is more confident.
* tags: List of tags to group like observables together. (Example: whitelist)
* description: A description of this observable or why it is listed
* data: Original Purpose Unknown
* otype: Observable type, valid values are ipv4,ipv6,url,fdqn,email,hash,binary.
* **observable**: The observable string or path to binary. If set before otype, otype will be automatically detected
* application: The application that utilizes this obserable
* provider: The domain name or name of the list providing the observalbe
* reporttime: The time the observable was reported. Most standard formats are acceptable.
* firsttime: The time the observable was first seen. Most standard formats are acceptable.
* lasttime: The time the observable was last seen. Most standard formats are acceptable.
* adata: ??
* related: A 'parent' or related observable ID
* altid: Alternate ID or link to more details about the observable.
* altid_tlp: Traffic Light Protocol of the TLP. May be different from the observable TLP
* additional_data: Original Purpose Unknown. Likely a place for any additional data that doesn't fit anywhere else.
* Other non-standard object attributes can be created and stored by simply creating the observable with them (e.g. rank)

#### Observable Type Specific attributes
* ipv4, ipv6
  * portlist: One or more ports applicable to the observable
  * protocol: The IP protocol used for communication (.e.g. ip, tcp, udp)
  * cc: Two letter country code
  * rdata: Reverse data record (.e.g. result of a reverse DNS lookup)
  * rtype: Reverse data type (reverse dns)
  * orientation: Orientation of the object, inbound or outbound
  * asn: Autonomous System Number
  * asn_desc: Name of the ASN ID
  * rir: RIR Organization
  * peers: List of BGP peers found for the ASN the ip address is announced from
  * mask: Subnet mask from the observable
  * prefix: Subnet prefix this IP belongs to
  * citycode: GeoIP Citycode
  * longitude: GPS Longitude
  * latitude: GPS latitude
  * geolocation: GPS coordinate concatenation of longitude and latitude
  * timezone: GeoIP guessed timezone of IP address
  * subdivision: Possible housing subdivision for this IP address
* url, fdqn
  * portlist: One or more ports applicable to the observable
  * protocol: The IP protocol used for communication (.e.g. ip, tcp, udp)
  * cc: Two letter country code
  * rdata: Reverse data record (.e.g. result of a reverse DNS lookup)
  * rtype: Reverse data type (rdns)
* email, binary
  * hash: possible hash of the email observable
  * htype: hash type (default: sha256)

#### Token
* *token*: Unique 64 byte hex ID (Default: will be automatically generated)
* acl: Arbitrary ACL setting for external synchronization or usage (Default: None)
* description: Description for the token (such as a user or hostname of a system). (Default: None)
* username: Arbitrary username. This does not have to be given when the token is used. (Default: None)
* write: Write Permission, 1 = User can submit new observables and (if admin) create/edit/delete tokens. (Default: 0)
* groups: Groups the user can search observables for. (default: everyone)
* expires: Expiration timestamp. After this expiration period the token cannot be used any longer. (Default: none)
* read: Read permission. 1 = User can read from allowed groups, 0 = user cannot read (Default: 1)
* admin: Admin flag. 1 = Grants this user all privileges across all groups, 0 = Not an admin (Default: 0)
* revoked: Revokation status. 1 = Revoked and cannot be used anymore, 0 = Active

Performance Notes
------------------
This is running with 8x workers and 30x threads. ~ 850-900 observables per second being augmented / correlated.

This is while processing the largest feed in the CIF feed list. DGA list by Bambenek Consulting

Only 1.25GB of memory in use by applications (half of that being used by elasticsearch).

```
top - 13:51:16 up 5 days, 10:58,  2 users,  load average: 27.30, 24.60, 19.77
Tasks: 114 total,   3 running, 111 sleeping,   0 stopped,   0 zombie
%Cpu0  : 55.0 us,  0.0 sy,  0.0 ni, 35.0 id,  0.0 wa,  0.0 hi,  5.0 si,  5.0 st
%Cpu1  : 50.0 us,  0.0 sy,  0.0 ni, 50.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
%Cpu2  : 66.7 us,  5.6 sy,  0.0 ni, 27.8 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
%Cpu3  : 55.6 us,  0.0 sy,  0.0 ni, 44.4 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
%Cpu4  : 41.2 us,  0.0 sy,  0.0 ni, 58.8 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
%Cpu5  : 38.9 us,  5.6 sy,  0.0 ni, 55.6 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
%Cpu6  : 55.6 us,  0.0 sy,  0.0 ni, 44.4 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
%Cpu7  : 50.0 us,  0.0 sy,  0.0 ni, 50.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
KiB Mem:   8230192 total,  2582412 used,  5647780 free,   167884 buffers
KiB Swap:  4290556 total,      412 used,  4290144 free.  1143036 cached Mem

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
 4524 cif       20   0  657464 519600   7544 R  88.4  6.3   6:17.10 /usr/bin/python3 bin/cif-server --noauth
 2623 elastic+  20   0 5855960 447004  33360 S  24.6  5.4 377:24.83 /usr/lib/jvm/java-7-openjdk-amd64//bin/java -Xms256m -Xmx1g -Xss256k -D+
 4375 cif       20   0 2368256  24852   5572 S  44.2  0.3   7:41.93 /usr/bin/python3 bin/cif-server --noauth
 4440 cif       20   0 2368256  24472   5444 S  34.4  0.3   7:43.51 /usr/bin/python3 bin/cif-server --noauth
 4265 cif       20   0   81796  24396   8116 S   0.0  0.3   0:00.29 /usr/bin/python3 bin/cif-server --noauth
 4398 cif       20   0 2368256  24308   5572 S  44.2  0.3   7:41.27 /usr/bin/python3 bin/cif-server --noauth
 4268 cif       20   0 2368256  24188   5484 S  34.4  0.3   7:43.99 /usr/bin/python3 bin/cif-server --noauth
 4466 cif       20   0 2368512  24092   5388 S  34.4  0.3   7:38.03 /usr/bin/python3 bin/cif-server --noauth
 4267 cif       20   0 2368256  23612   5548 S  44.2  0.3   7:37.76 /usr/bin/python3 bin/cif-server --noauth
 4335 cif       20   0 2368256  23304   5508 S  49.1  0.3   7:38.15 /usr/bin/python3 bin/cif-server --noauth
 4301 cif       20   0 2368256  23004   5508 S  54.0  0.3   7:38.84 /usr/bin/python3 bin/cif-server --noauth
 4494 cif       20   0   83892  21656   5336 S   0.0  0.3   0:00.08 /usr/bin/python3 bin/cif-server --noauth
```

```
             total       used       free     shared    buffers     cached
Mem:          8037       2565       5471          0        163       1084
-/+ buffers/cache:       1317       6719
Swap:         4189          0       4189
```

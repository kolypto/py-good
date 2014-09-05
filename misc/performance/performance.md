Performance
===========

In this test, we compare the performance of:

* [voluptuous](https://github.com/alecthomas/voluptuous)
* [good](https://github.com/kolypto/py-good)

The [test script](performance.py) generates random dictionary schemas,
increasing its size, and compares how performant both libraries are
on those schemas. These schemas are validated with both libraries and 
a report is generated ([performance.dat](performance.dat)).

Hardware:
* CPU: Intel(R) Core(TM) i5 CPU, 2.4 GHz
* RAM: 8 GiB
* Ubuntu Linux 14.04
* Python 2.7.6 (which is supported by both libraries)

Results
-------

Solid line shows the performance of successful validations.
Dashed line shows the performance of invalid values (raising errors).

### Validations Per Second

In this test, we compare how many validations per second each of the libraries can do.
A "validation" is an attempt to validate a value against the schema only.

<img src="performance-vps.png" />

### Total Execution Time

In this test, we compare how much time a library needs to validate 5000 dictionaries
with a schema.

<img src="performance-time.png" />

Results for Py3k
----------------

### Validations Per Second

<img src="performance-vps-py3.png" />

### Total Execution Time

<img src="performance-time-py3.png" />

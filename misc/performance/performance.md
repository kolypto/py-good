Performance
===========

In this test, we compare the performance of:

* [voluptuous](https://github.com/alecthomas/voluptuous)
* [good](https://github.com/kolypto/py-good)

The [test script](performance.py) generates random dictionary schemas,
increasing its size, and compares how performant both libraries are
on those schemas.

Validations Per Second
----------------------

In this test, we compare how many validations per second each of the libraries can do.
A "validation" is an attempt to validate a value against the schema only.

<img src="performance-vps.png" />

Keys Per Second
---------------

In this test, we compare how much time a library needs to validate 5000 dictionaries
with a schema.

<img src="performance-time.png" />

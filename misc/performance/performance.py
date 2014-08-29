#! /usr/bin/env python

from __future__ import print_function, division

import voluptuous
import good

import itertools
from datetime import datetime
from random import choice, randrange


def generate_random_type(valid):
    """ Generate a random type and samples for it.

    :param valid: Generate valid samples?
    :type valid: bool
    :return: type, sample-generator
    :rtype: type, generator
    """
    type = choice(['int', 'str'])

    r = lambda: randrange(-1000000000, 1000000000)

    if type == 'int':
        return int,  (r() if valid else str(r()) for i in itertools.count())
    elif type == 'str':
        return str, (str(r()) if valid else r() for i in itertools.count())
    else:
        raise AssertionError('!')


def generate_random_schema(valid):
    """ Generate a random plain schema, and a sample generation function.

    :param valid: Generate valid samples?
    :type valid: bool
    :returns: schema, sample-generator
    :rtype: *, generator
    """
    schema_type = choice(['literal', 'type'])

    if schema_type == 'literal':
        type, gen = generate_random_type(valid)
        value = next(gen)
        return value, (value if valid else None for i in itertools.count())
    elif schema_type == 'type':
        return generate_random_type(valid)
    else:
        raise AssertionError('!')


def generate_dict_schema(size, valid):
    """ Generate a schema dict of size `size` using library `lib`.

    In addition, it returns samples generator

    :param size: Schema size
    :type size: int
    :param samples: The number of samples to generate
    :type samples: int
    :param valid: Generate valid samples?
    :type valid: bool
    :returns
    """

    schema = {}
    generator_items = []

    # Generate schema
    for i in range(0, size):
        while True:
            key_schema,   key_generator   = generate_random_schema(valid)
            if key_schema not in schema:
                break
        value_schema, value_generator = generate_random_schema(valid)

        schema[key_schema] = value_schema
        generator_items.append((key_generator, value_generator))

    # Samples
    generator = ({next(k_gen): next(v_gen) for k_gen, v_gen in generator_items} for i in itertools.count())

    # Finish
    return schema, generator



if __name__ == '__main__':
    import sys
    import argparse
    from collections import defaultdict

    parser = argparse.ArgumentParser(prog='Performance')
    parser.add_argument('samples', type=int, help='The number of samples to test with')
    parser.add_argument('size_min', type=int, help='Min dictionary size')
    parser.add_argument('size_max', type=int, help='Max dictionary size')
    args = parser.parse_args()

    # Test on both valid and invalid schemas
    results = defaultdict(list)
    best_for_size = defaultdict(float)
    for valid in (True, False):

        # Generate schemas of different size
        dictionaries = []
        for size in range(args.size_min, args.size_max + 1):
            # Generate samples
            schema, gen = generate_dict_schema(size, valid)
            samples = list(sample for i, sample in zip(range(0, args.samples), gen))

            dictionaries.append((
                size,
                schema,
                samples
            ))

        # Iterate over libraries
        for lib in (good, voluptuous):
            lib_name = lib.__name__

            # Generate schemas of different size
            for size, schema, samples in dictionaries:
                compiled_schema = lib.Schema(schema.copy())

                # Now do validation
                start = datetime.utcnow()
                for sample in samples:
                    try:
                        compiled_schema(sample)
                    except lib.Invalid as e:
                        # Ignore errors
                        pass
                stop = datetime.utcnow()

                # Results
                spent_time = (stop - start).total_seconds()
                validations_per_second = len(samples) / spent_time

                # Save
                results[valid, lib_name].append(dict(
                    size=size,
                    sec=spent_time,
                    vps=validations_per_second
                ))

                # Best
                best_for_size[valid, size] = max(
                    best_for_size[valid, size],
                    validations_per_second)

    # Print dataset
    for (valid, lib_name), stats_list in sorted(results.items()):
        # Dataset header
        print('"{lib} ({valid})"'.format(
            lib=lib_name,
            valid='Valid' if valid else 'Invalid',
        ))

        # Values
        print("#size  time  vps")
        for stat in stats_list:
            print('{size: 5d} {sec: 4.2f} {vps: 10.2f}'.format(**stat))
        print('\n')  # split datasets

        # Calculate averages
    for (valid, lib_name), stats_list in sorted(results.items()):
        vps = sum(x['vps'] for x in stats_list) / len(stats_list)
        print('AVG:{lib:<12} {valid:<8} {vps: 10.2f}'.format(
            lib=lib_name,
            valid='Valid' if valid else 'Invalid',
            vps=vps
        ), file=sys.stderr)

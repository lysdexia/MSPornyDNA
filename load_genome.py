#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Doug Shawhan
# kphretiq aht geemail dawt calm

# insert ManuSporny dna dump into couchdb, and create example view
# dump is supplied as csv file. Delete all comments down to header line:
# "#rsid	chromosome	position	genotype"
# then remove hash symbol

# REQUIRES couchdb module

# Host credentials and database url are set in load_genome.ini

import sys, csv, ConfigParser
from optparse import OptionParser
import couchdb, couchdb.design
try:
    couchdb.json.use("cjson")
except:
    pass

class Injector(object):
    def __init__(self, genome_name, genome_file):
        self.genome_name = genome_name
        self.genome_file = genome_file

    def connect(self):
        db_address = config.get("db", "url")
        username = config.get("db", "username")
        password = config.get("db", "password")
        couch = couchdb.Server(db_address)
        # if you haven't supplied host creds and you need them, you'll
        # fail right here.

        if all([username, password]):
            couch.resource.credentials = (username, password)
        try:
            db = couch[self.genome_name]
        except:
            db = couch.create(self.genome_name)
            print("created %s"%db._name)
        return db

    def gen_genome(self):
        # declare tab delimited.
        _raw = csv.reader(open(self.genome_file), delimiter = "	")
        header = _raw.next()
        for row in _raw:
            yield dict([(k, v) for k, v in zip(header, row)])

    def to_database(self):
        genome = self.gen_genome()
        db = self.connect()
        while genome:
            # use the rsid for our row key
            row = genome.next()
            key = "%s_%s"%(self.genome_name, row["position"])
            try:
                db[key] = row
            except couchdb.http.ResourceConflict, error:
                print("%s for %s. Skipping."%(error, key))
            except:
                pass

    def add_view(self):
        map_doc = "function (doc) {\n  emit([doc.genotype, doc.position, doc.chromosome], 1);\n}"
        reduce_doc = "function (keys, values, rereduce) {\n    return sum(values);\n}"
        _design = "discover"
        _view = "genotype"
        db = self.connect()
        view = couchdb.design.ViewDefinition(_design, _view, map_doc, reduce_fun = reduce_doc, language = "javascript") 
        view.sync(db)
        design_doc = view.get_doc(db)
        print(design_doc)

if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage = usage)
    parser.add_option("-f", "--genome_file", dest = "genome_file", help = "Tab-seperated text file containing genome information.")
    parser.add_option("-n", "--genome_name", dest = "genome_name", help = "Name of genome")

    options, args = parser.parse_args()

    config = ConfigParser.ConfigParser()
    config.read(["load_genome.ini"])

    if not all([options.genome_file, options.genome_name]):
        parser.print_help()
        sys.exit("See README, load_genome.ini and/or script headers for more information.")

    # couchdb likes lowercase names
    options.genome_name = "".join([i for i in options.genome_name.lower()])

    injector = Injector(options.genome_name, options.genome_file)
    injector.to_database()
    injector.add_view()

# -*- coding: utf-8 -*-
#
# Poio Tools for Linguists
#
# Copyright (C) 2009-2013 Poio Project
# Author: António Lopes <alopes@cidles.eu>
# URL: <http://media.cidles.eu/poio/>
# For license information, see LICENSE.TXT

import os
import re

import xml.etree.ElementTree as ET

import poioapi.io.typecraft
import poioapi.io.graf

class TestTypecraft:
    """
    This class contain the test methods to the
    class io.typecraft.py.

    """

    def setup(self):
        self.filename = os.path.join(os.path.dirname(__file__), "sample_files",
            "typecraft_graf", "typecraft_example.xml")

        self.basedirname = os.path.dirname(self.filename)

        typecraft = poioapi.io.typecraft.Parser(self.filename)

        typecraft_graf = poioapi.io.graf.GrAFConverter(typecraft)

        self.graph = typecraft_graf.as_graf()

        tree = ET.parse(self.filename)
        self.root = tree.getroot()

        self.xml_namespace = re.search('\{(.*)\}', self.root.tag).group()

    def test_phrase_nodes(self):
        nodes_number = len(self.root.findall(self.xml_namespace+"phrase"))

        expected_nodes_number = 0

        for nodes in self.graph.nodes:
            if "phrase" in nodes.id:
                expected_nodes_number+=1

        assert(nodes_number == expected_nodes_number)

    def test_phrase_annotation_features(self):
        """ The annotations of a phrase are the
        attributes and the rest elements
        excluding the WORD and globaltags elements.

        """

        node_phrase = self.root.find(self.xml_namespace+"phrase")

        expected_features_number = len(node_phrase.attrib)

        for elements in node_phrase:
            key = str(elements.tag).split(self.xml_namespace)
            if key[1] != "word":
                expected_features_number+=1

        node = self.graph.nodes["phrase/n1818"]

        node_annotations = node.annotations._elements

        features_number = len(node_annotations[0].features)

        assert(features_number == expected_features_number)
